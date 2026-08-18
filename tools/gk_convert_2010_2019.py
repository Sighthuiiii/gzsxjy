# -*- coding: utf-8 -*-
"""把项目 content/YYYY/paper.tex 转换为讲义 GaoKao 附录的用户格式（2010-2019）。

宏约定：
- \texfigure/texinclude 等 TikZ 源图：渲染为 GaoKao/images/.../qN_figM.png 后 \includegraphics
- 位图：直接复制项目 img/ 目录到 GaoKao/images/
- 项目专用宏（\examdisplaycases 等）转换为标准 LaTeX 或讲义已加载的宏
"""
import re
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gk_common import ProjectPaper, split_args, find_env, _macro_arg_span

CN_ORD = ['一', '二', '三', '四', '五', '六', '七', '八', '九']

BLANK = '\\rule[-0.3ex]{3em}{0.4pt}'


def part_name(sec, has_multi):
    if sec == '单选题':
        return '单选题' if has_multi else '选择题'
    if sec == '选择题':
        return '选择题'
    if sec == '多选题':
        return '多选题'
    if sec == '填空题':
        return '填空题'
    if sec == '解答题':
        return '解答题'
    if sec.startswith('选考'):
        return '选考题'
    if sec.startswith('选做') or sec == '选作题':
        return '选做题'
    if sec.startswith('附加'):
        return '附加题'
    if sec == '参考题':
        return '参考题'
    if sec == '补充题':
        return '补充题'
    return sec


def xuanxiu_marker(text):
    if '参数方程' in text or '极坐标' in text:
        return '【选修4-4：坐标系与参数方程】'
    if '不等式' in text or ('正数' in text and '证明' in text):
        return '【选修4-5：不等式选讲】'
    if '圆' in text or '切线' in text or '四点共圆' in text:
        return '【选修4-1：几何证明选讲】'
    return None


def is_mathy(s):
    return ('$' in s) or ('\\(' in s) or ('\\[' in s) or ('\\frac' in s) or ('\\sqrt' in s) or ('\\bm' in s)


# ---------------------------------------------------------------------------
# 文本级宏清理（不依赖 paper / img_prefix）
# ---------------------------------------------------------------------------

def _strip_macro(text, name, n_args):
    """删除 \\name 及其 n_args 个 {..} 参数。"""
    out = []
    pos = 0
    for m in re.finditer(r'\\' + name + r'(?![a-zA-Z])', text):
        span = _macro_arg_span(text, m.end())
        out.append(text[pos:m.start()])
        if span:
            pos = span[1]
        else:
            pos = m.end()
    out.append(text[pos:])
    return ''.join(out)


def _replace_macro(text, name, n_args, repl):
    """把 \\name 的 n_args 个参数交给 repl(list_of_args) 替换。"""
    out = []
    pos = 0
    for m in re.finditer(r'\\' + name + r'(?![a-zA-Z])', text):
        span = _macro_arg_span(text, m.end())
        if span and _arg_count(text[span[0]:span[1]]) >= n_args:
            args = split_args(text[span[0]:span[1]])
            out.append(text[pos:m.start()])
            out.append(repl(args[:n_args]))
            pos = span[1]
    out.append(text[pos:])
    return ''.join(out)


def _arg_count(s):
    n = 0
    i = 0
    while i < len(s):
        if s[i] == '{':
            n += 1
            i += 1
            depth = 1
            while i < len(s) and depth:
                if s[i] == '{':
                    depth += 1
                elif s[i] == '}':
                    depth -= 1
                i += 1
        else:
            i += 1
    return n


def replace_circled(s):
    def repl(m):
        n = int(m.group(1))
        if 1 <= n <= 20:
            return '\\ding{%d}' % (171 + n)
        return '\\textcircled{%s}' % m.group(1)
    return re.sub(r'\\circled(?![a-zA-Z])\s*\{(\d+)\}', repl, s)


def clean_text(s):
    """与图片无关的项目宏 -> 讲义可用宏。"""
    s = _strip_macro(s, 'answer', 1)
    s = _strip_macro(s, 'problemresetlayout', 0)
    s = _strip_macro(s, 'FigureLayoutDeclare', 3)
    s = _strip_macro(s, 'FigureTrimDeclare', 2)
    s = re.sub(r'\\tallpagetrue(?![a-zA-Z])', '', s)
    s = s.replace('\\FloatBarrier', '')
    s = re.sub(r'\\e(?![a-zA-Z])', '{\\\\mathrm{e}}', s)
    s = re.sub(r'\\bs(?![a-zA-Z])\s*(?:\{([^}]*)\}|(\\[a-zA-Z]+|[a-zA-Z0-9]))',
               lambda m: '\\bm{%s}' % (m.group(1) or m.group(2)), s)
    s = re.sub(r'\\R(?![a-zA-Z])', '\\\\mathbb{R}', s)
    s = re.sub(r'\\Z(?![a-zA-Z])', '\\\\mathbb{Z}', s)
    s = re.sub(r'\\N(?![a-zA-Z])', '\\\\mathbb{N}', s)
    s = re.sub(r'\\Q(?![a-zA-Z])', '\\\\mathbb{Q}', s)
    s = re.sub(r'\\myarc(?![a-zA-Z])\s*\{([^}]*)\}', r'\\overset{\\frown}{\1}', s)
    s = re.sub(r'\\degree(?![a-zA-Z])', '^\\\\circ', s)
    s = re.sub(r'\\examdisplaymath(?![a-zA-Z])\s*\{([^}]*)\}', r'\\[\1\\]', s)
    s = _replace_macro(s, 'examdisplaycases', 2,
                       lambda a: '\\[\n%s\\begin{cases}\n%s\n\\end{cases}\n\\]' % (a[0], a[1]))
    s = _replace_macro(s, 'examdisplayarray', 4,
                       lambda a: '\\[\n%s\\begin{array}{%s}\n%s\n\\end{array}%s\n\\]' % (a[0], a[1], a[2], a[3]))
    s = replace_circled(s)
    s = re.sub(r'\\fillinblank(?![a-zA-Z])\s*(\{\})?', lambda m: BLANK, s)
    s = s.replace('\\symbfup{', '\\mathbf{').replace('\\symbfit{', '\\bm{')
    s = re.sub(r'\\begin\{circlelist\}', lambda m: '\\begin{enumerate}', s)
    s = re.sub(r'\\end\{circlelist\}', lambda m: '\\end{enumerate}', s)
    # 题目正文中残留的选项图宏（选项已单独渲染）去掉
    s = re.sub(r'\\choicebitmap(?![a-zA-Z])\s*(?:\[[^\]]*\])?\s*\{[^}]*\}', '', s)
    return s


# ---------------------------------------------------------------------------
# 图片路径与宽度
# ---------------------------------------------------------------------------

def img_path(proj_path, img_prefix):
    rel = proj_path
    for prefix in ('img_repaint/', 'img/'):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
            break
    if rel.endswith('.tex'):
        rel = rel[:-4] + '.png'
    return os.path.join(img_prefix, rel).replace('\\', '/')


def figure_width(path, opt, paper):
    for key in (path, path.replace('img_repaint/', 'img/')):
        if key in paper.layouts:
            return paper.layouts[key][0]
        if key in paper.global_layouts:
            return paper.global_layouts[key][0]
    if opt:
        m = re.search(r'(?:max width|width)=([^\s,]+)', opt)
        if m:
            return m.group(1)
        m = re.search(r'\[([0-9.]+cm)\]', opt)
        if m:
            return m.group(1)
    return '0.65\\linewidth'


def inline_width(a1, a2):
    for opt in (a1, a2):
        if opt:
            m = re.search(r'([0-9.]+cm|0?\.[0-9]+\\linewidth)', opt)
            if m:
                return m.group(1)
    return '0.65\\linewidth'


def render_figure_block(path, opt, paper, img_prefix):
    return ('\\begin{center}\n'
            '\\includegraphics[width=%s]{%s}\n'
            '\\end{center}' % (figure_width(path, opt, paper), img_path(path, img_prefix)))



_GROUP_INNER_PAT = re.compile(
    r'\\(?:bitmapinclude|bitmapinline|bitmapfigure|bitmapinlinefigure|texfigure|texinclude)'
    r'(?![a-zA-Z])\s*(?:\[[^]]*\])?\s*\{([^}]*)\}')


def sub_examfiguregroup(body, paper, img_prefix):
    """把 \\examfiguregroup[opt]{img}{...} 整组替换为逐图居中块。

    组体可以跨行、含 % 注释与嵌套花括号，因此用括号配平而不是正则截取。
    """
    out = []
    pos = 0
    pat = re.compile(r'\\examfiguregroup(?![a-zA-Z])')
    for m in pat.finditer(body):
        out.append(body[pos:m.start()])
        p = m.end()
        opt = ''
        if p < len(body) and body[p] == '[':
            q = body.find(']', p)
            if q < 0:
                out.append(body[m.start():])
                pos = len(body)
                break
            opt = body[p + 1:q]
            p = q + 1
        img = None
        if p < len(body) and body[p] == '{':
            q = body.find('}', p)
            if q < 0:
                out.append(body[m.start():])
                pos = len(body)
                break
            img = body[p + 1:q]
            p = q + 1
        if img is None or p >= len(body) or body[p] != '{':
            out.append(body[m.start():])
            pos = len(body)
            break
        depth = 0
        i = p
        while i < len(body):
            if body[i] == '{':
                depth += 1
            elif body[i] == '}':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth != 0:
            out.append(body[m.start():])
            pos = len(body)
            break
        grp = body[p + 1:i]
        paths = [fm.group(1) for fm in _GROUP_INNER_PAT.finditer(grp)]
        if not paths:
            paths = [img]
        out.append('\n\n'.join(render_figure_block(x, opt, paper, img_prefix) for x in paths))
        pos = i + 1
    out.append(body[pos:])
    return ''.join(out)

# ---------------------------------------------------------------------------
# 选项渲染
# ---------------------------------------------------------------------------

def dollars_to_math(s):
    """把成对 $..$ 转换为 \\(..\\)（用于选项统一数学包裹）。"""
    out = []
    in_math = False
    for ch in s:
        if ch == '$':
            out.append('\\)' if in_math else '\\(')
            in_math = not in_math
        else:
            out.append(ch)
    return ''.join(out)


def choice_cell(label, content):
    content = clean_text(content)
    content = dollars_to_math(content)
    content = content.strip()
    # 文本模式单元格：数学部分保留 \(...\)，中文留在文本模式
    # （\e 在文本模式下展开为 {\mathrm{e}}，需包回行内数学）
    segs = re.split(r'(\\\(.*?\\\))', content, flags=re.S)
    fixed = []
    for seg in segs:
        if seg.startswith('\\(') and seg.endswith('\\)'):
            fixed.append(seg)
        else:
            fixed.append(re.sub(r'\{?\\mathrm\{e\}\}?', r'\\({\\mathrm{e}}\\)', seg))
    return '\\text{%s. }%s' % (label, ''.join(fixed))


def render_choices(kind, args, imgs, imgwidth, img_prefix):
    n = 5 if kind == 'five' else 4
    labels = ['A', 'B', 'C', 'D', 'E'][:n]
    cols = 'l' * n if not imgs else 'c' * n
    cells = []
    for i in range(n):
        if imgs and i < len(imgs):
            w = imgwidth or '0.15\\paperwidth'
            cells.append('\\text{%s. }\\includegraphics[width=%s]{%s}'
                         % (labels[i], w, img_path(imgs[i][1], img_prefix)))
        elif args and i < len(args):
            cells.append(choice_cell(labels[i], args[i]))
        else:
            cells.append('')
    row = '  &  '.join(cells)
    return ('        {\\centering\\begin{tabular*}{\\linewidth}{@{}@{\\extracolsep{\\fill}}%s@{}}\n'
            '          %s\n'
            '        \\end{tabular*}\\par}' % (cols, row))


# ---------------------------------------------------------------------------
# 题目转换
# ---------------------------------------------------------------------------

def strip_envs(body, names):
    for name in names:
        while True:
            m = re.search(r'\\begin\{' + name + r'\}', body)
            if not m:
                break
            _, end = find_env(body, m.start(), name)
            body = body[:m.start()] + body[end + len('\\end{' + name + '}'):]
    return body


def convert_problem(prob, paper, img_prefix):
    body = prob['body']
    body = strip_envs(body, ['answer', 'solution'])
    choices = prob['choices']
    args = choices[1] if choices else None
    kind = choices[0] if choices else None
    imgs = prob['choice_images']
    imgwidth = None
    if imgs:
        m = re.search(r'\\choicebitmap(?![a-zA-Z])\s*\[([^\]]*)\]', prob['body'])
        if m and 'width=' in m.group(1):
            imgwidth = m.group(1).split('width=', 1)[1].strip()
    # 去掉 choices 宏文本（含参数组）
    if choices:
        for cmd in (r'\\choicesfive', r'\\choices'):
            mm = re.search(cmd + r'(?![a-zA-Z])', body)
            if mm:
                span = _macro_arg_span(body, mm.end())
                if span:
                    body = body[:mm.start()] + body[span[1]:]
                else:
                    body = re.sub(cmd + r'(?![a-zA-Z])', '', body)
                break
    # 图宏 -> includegraphics
    def bitmap_repl(m):
        path = m.group(2)
        return render_figure_block(path, m.group(1) or '', paper, img_prefix)
    # examfiguregroup：优先整组解析（组体可跨行、含 % 注释与嵌套花括号）
    body = sub_examfiguregroup(body, paper, img_prefix)
    body = re.sub(r'\\bitmapfigure(?![a-zA-Z])\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}', bitmap_repl, body)
    body = re.sub(r'\\bitmapinlinefigure(?![a-zA-Z])\s*(?:\[([^\]]*)\])?\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}',
                  lambda m: render_figure_block(m.group(3), m.group(2) or '', paper, img_prefix), body)
    body = re.sub(r'\\bitmapinclude(?![a-zA-Z])\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}', bitmap_repl, body)
    body = re.sub(r'\\bitmapinline(?![a-zA-Z])\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}',
                  lambda m: render_figure_block(m.group(1), '0.5\\linewidth', paper, img_prefix), body)
    body = re.sub(r'\\texfigure(?![a-zA-Z])\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}',
                  lambda m: render_figure_block(m.group(2), m.group(1) or '', paper, img_prefix), body)
    body = re.sub(r'\\texinclude(?![a-zA-Z])\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}',
                  lambda m: render_figure_block(m.group(2), m.group(1) or '', paper, img_prefix), body)
    # 文本级清理
    body = clean_text(body)
    if prob['section'] in ('填空题',) and BLANK not in body:
        body = body.rstrip() + ' ' + BLANK + '．'
    marker = None
    if prob['section'].startswith('选考') or prob['section'].startswith('选做'):
        marker = xuanxiu_marker(body)
    lines = []
    if marker:
        lines.append('\\textbf{%s}' % marker)
    body = body.strip()
    lines.append(body)
    item = '\n\n'.join(lines)
    if choices:
        item += '\n\n' + render_choices(kind, args, imgs, imgwidth, img_prefix)
    item = item.replace('▲', r'$\blacktriangle$')
    return item


def convert_paper(paper, year, title, img_prefix):
    has_multi = '多选题' in paper.sec_counts
    parts = []
    cur = None
    for p in paper.problems:
        if not cur or cur['sec'] != p['section']:
            cur = {'sec': p['section'], 'probs': []}
            parts.append(cur)
        cur['probs'].append(p)
    out = []
    total_before = 0
    for idx, part in enumerate(parts):
        name = part_name(part['sec'], has_multi)
        ordp = CN_ORD[idx] if idx < len(CN_ORD) else str(idx + 1)
        out.append('\\begin{description}')
        out.append('    \\item[%s、%s]' % (ordp, name))
        out.append('    \\begin{enumerate}[leftmargin=5pt]')
        if total_before:
            out.append('      \\addtocounter{enumi}{+%d}' % total_before)
        for p in part['probs']:
            item = convert_problem(p, paper, img_prefix)
            out.append('        \\item ' + item)
        out.append('    \\end{enumerate}')
        out.append('\\end{description}')
        total_before += len(part['probs'])
    return '\n\n'.join(out)