# -*- coding: utf-8 -*-
"""公共解析库：解析项目试卷 tex 与用户讲义 GaoKao 章节文件。"""
import re
import os

# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------

def find_env(text, pos, env):
    """从 pos 处（位于 \\begin{env}）返回 (inner_start, end_after_end)。"""
    begin = '\\begin{' + env + '}'
    end = '\\end{' + env + '}'
    i = pos + len(begin)
    depth = 1
    n = len(text)
    while i < n:
        if text.startswith(begin, i):
            depth += 1
            i += len(begin)
        elif text.startswith(end, i):
            depth -= 1
            i += len(end)
            if depth == 0:
                return pos + len(begin), i - len(end)
        else:
            i += 1
    raise ValueError('unbalanced environment: ' + env)


def split_args(s):
    """把形如 {a}{b}{c} 的选项参数串按花括号配对切分（支持嵌套）。"""
    args = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] == '{':
            depth = 1
            j = i + 1
            while j < n and depth:
                if s[j] == '{':
                    depth += 1
                elif s[j] == '}':
                    depth -= 1
                j += 1
            args.append(s[i + 1:j - 1])
            i = j
        else:
            i += 1
    return args


PROJ_ROOT = os.environ.get('GK_PROJ_ROOT',
                           os.path.join(os.environ['TEMP'],
                                        'Gaokao-Math-Problems-Compilation'))
PROJ_CONTENT = os.path.join(PROJ_ROOT, 'content')

# 全局图片布局表（生成于项目 layout/generated_image_layout.tex），作为试卷内声明的后备
_GLOBAL_LAYOUTS = None
_GLOBAL_TRIMS = None


def global_layouts():
    global _GLOBAL_LAYOUTS, _GLOBAL_TRIMS
    if _GLOBAL_LAYOUTS is None:
        _GLOBAL_LAYOUTS = {}
        _GLOBAL_TRIMS = {}
        fp = os.path.join(PROJ_ROOT, 'layout', 'generated_image_layout.tex')
        if os.path.exists(fp):
            txt = open(fp, encoding='utf-8').read()
            for m in re.finditer(r'\\FigureLayoutDeclare\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}', txt):
                _GLOBAL_LAYOUTS[m.group(1)] = (m.group(2).strip(), m.group(3).strip())
            for m in re.finditer(r'\\FigureTrimDeclare\{([^}]*)\}\{([^}]*)\}', txt):
                _GLOBAL_TRIMS[m.group(1)] = m.group(2).strip()
    return _GLOBAL_LAYOUTS, _GLOBAL_TRIMS


PROB_RE = re.compile(r'\\begin\{problem\}')
SEC_RE = re.compile(r'\\section\s*\{([^}]*)\}')
LAYOUT_RE = re.compile(r'\\FigureLayoutDeclare\{([^}]*)\}\{([^}]*)\}\{([^}]*)\}')
TRIM_RE = re.compile(r'\\FigureTrimDeclare\{([^}]*)\}\{([^}]*)\}')

FIGURE_MACROS = [
    ('bitmapfigure', False),
    ('bitmapinlinefigure', False),
    ('bitmapinclude', False),
    ('bitmapinline', False),
    ('choicebitmap', True),
    ('choicetexfigure', True),
]


class ProjectPaper:
    """项目 content/YYYY/paper.tex 的解析结果。"""

    def __init__(self, path):
        self.path = path
        self.text = open(path, encoding='utf-8').read()
        self.layouts = {}   # 图路径 -> (width, insets)
        self.trims = {}     # 图路径 -> insets
        self.problems = []
        self.sec_counts = {}
        self.parse()
        gl, gt = global_layouts()
        self.global_layouts = gl
        self.global_trims = gt

    def parse(self):
        txt = self.text
        for m in LAYOUT_RE.finditer(txt):
            self.layouts[m.group(1)] = (m.group(2).strip(), m.group(3).strip())
        for m in TRIM_RE.finditer(txt):
            self.trims[m.group(1)] = m.group(2).strip()

        cur_sec = '?'
        next_sec = SEC_RE.search(txt, 0)
        prob_counter = 0
        pos = 0
        while True:
            prob_m = PROB_RE.search(txt, pos)
            if prob_m is None:
                break
            while next_sec and next_sec.start() < prob_m.start():
                cur_sec = next_sec.group(1)
                next_sec = SEC_RE.search(txt, next_sec.end())
            inner, end = find_env(txt, prob_m.start(), 'problem')
            body = txt[inner:end]
            if not re.search(r'\\reuseproblemnumber', body):
                prob_counter += 1
            prob = {
                'num': prob_counter,
                'section': cur_sec,
                'body': body,
                'figures': [],
                'choice_images': [],
                'choices': None,
            }
            cm = re.search(r'\\choicesfive\b', body)
            cm4 = re.search(r'\\choices\b', body)
            if cm:
                m = re.search(r'\\choicesfive(?![a-zA-Z])', body)
                span = _macro_arg_span(body, m.end())
                if span:
                    prob['choices'] = ('five', split_args(body[span[0]:span[1]]))
                else:
                    prob['choices'] = ('five', None)
            elif cm4:
                m = re.search(r'\\choices(?![a-zA-Z])', body)
                span = _macro_arg_span(body, m.end())
                if span:
                    prob['choices'] = ('four', split_args(body[span[0]:span[1]]))
                else:
                    prob['choices'] = ('four', None)
            for name, is_choice in FIGURE_MACROS:
                # 支持 0~2 个可选参数（如 bitmapinlinefigure[5cm][width=5cm]）
                for fm in re.finditer(r'\\' + name + r'(?![a-zA-Z])\s*((?:\[[^\]]*\]){0,2})\s*\{([^}]*)\}', body):
                    target = prob['choice_images'] if is_choice else prob['figures']
                    target.append((name, fm.group(2), ''))
            for fm in re.finditer(r'\\texfigure(?![a-zA-Z])\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}', body):
                prob['figures'].append(('texfigure', fm.group(1), ''))
            self.problems.append(prob)
            pos = end

        self.sec_counts = {}
        for p in self.problems:
            self.sec_counts[p['section']] = self.sec_counts.get(p['section'], 0) + 1

    def problem(self, num):
        for p in self.problems:
            if p['num'] == num:
                return p
        return None


def _macro_arg_span(text, pos):
    """从 pos 起解析连续的 {..} 参数组，返回 (start, end)；无则 None。"""
    n = len(text)
    i = pos
    start = None
    groups = 0
    while i < n:
        while i < n and text[i] in ' \t\n':
            i += 1
        if i < n and text[i] == '{':
            if start is None:
                start = i
            depth = 1
            j = i + 1
            while j < n and depth:
                if text[j] == '{':
                    depth += 1
                elif text[j] == '}':
                    depth -= 1
                j += 1
            groups += 1
            i = j
        else:
            break
    if groups >= 1:
        return (start, i)
    return None


def parse_user_subsections(text):
    """把用户 GaoKao/YYYY.tex 拆成 subsection 列表。"""
    parts = re.split(r'(\\subsection\s*\{[^}]*\}(?:\s*\\label\{[^}]*\})?)', text)
    out = []
    for i in range(1, len(parts), 2):
        header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ''
        m = re.search(r'\\subsection\s*\{([^}]*)\}', header)
        out.append({'title': m.group(1), 'header': header, 'body': body})
    return out


_BEGIN_RE = re.compile(r'\\begin\{(\w+)\}')
_SKIP_ENVS = {'enumerate', 'itemize', 'cases', 'aligned', 'gathered', 'matrix',
              'pmatrix', 'bmatrix', 'vmatrix', 'smallmatrix', 'array', 'tabular',
              'tabular*', 'minipage', 'center', 'description', 'tikzpicture'}


def top_level_items(enum_body):
    """统计 enumerate 顶层 \\item 数（跳过嵌套环境）。"""
    count = 0
    i = 0
    n = len(enum_body)
    while i < n:
        if enum_body.startswith('\\begin{', i):
            m = _BEGIN_RE.match(enum_body[i:])
            if m and m.group(1) in _SKIP_ENVS:
                i = find_env(enum_body, i, m.group(1))[1]
                continue
            i += len(m.group(0)) if m else 1
            continue
        if enum_body.startswith('\\item', i) and not enum_body.startswith('\\itemize', i):
            count += 1
            i += 5
            continue
        i += 1
    return count


def user_paper_parts(body):
    """解析用户一个 subsection 的内容，返回 [(part 名, 顶层题数, 占位符列表, addtocounter 列表)]。"""
    out = []
    i = 0
    n = len(body)
    while i < n:
        if body.startswith('\\begin{description}', i):
            d, end = find_env(body, i, 'description')
            blk = body[d:end]
            m = re.search(r'\\item\[([^\]]*)\]', blk)
            header = m.group(1) if m else ''
            em = re.search(r'\\begin{enumerate}', blk)
            items = 0
            adds = []
            phs = []
            if em:
                e_inner, e_end = find_env(blk, em.start(), 'enumerate')
                ebody = blk[e_inner:e_end]
                items = top_level_items(ebody)
                adds = [int(x) for x in re.findall(r'\\addtocounter\{enumi\}\{\+(\d+)\}', ebody)]
                phs = re.findall(r'\[插入图片：([^\]]*)\]', ebody)
            out.append({'part': header, 'items': items, 'adds': adds, 'placeholders': phs})
            i = end
        else:
            i += 1
    return out
