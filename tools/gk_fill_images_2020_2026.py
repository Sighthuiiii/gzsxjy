# -*- coding: utf-8 -*-
"""2020-2026 补图工具：把用户 GaoKao/YYYY.tex 中的占位符
\\textsf{[插入图片：...]} 替换为项目图片 / 选项图 / 数据表格。

策略：
- 按小节(\\subsection)解析题号（\\addtocounter 递推）
- 对每个含占位符的题目，用“汉字串相似度”在当年项目试卷中定位真正的题
  （先查映射试卷，再查同年其他试卷，处理用户文件中混入他卷题目的情况）
- 图序按项目题 figures 列表顺序填充
"""
import os
import re
import sys
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gk_common import ProjectPaper, parse_user_subsections, find_env
import gk_papers

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAOKAO = os.path.join(REPO, 'GaoKao')
IMG_PREFIX = 'GaoKao/images'
PROJ_ROOT = os.environ.get('GK_PROJ_ROOT',
                           os.path.join(os.environ['TEMP'],
                                        'Gaokao-Math-Problems-Compilation'))

PH_RE = re.compile(r'\\textsf\{\s*\[插入图片：(.*?)\]\}')
BEGIN_RE = re.compile(r'\\begin\{(\w+)\}')
SKIP_ENVS = {'enumerate', 'itemize', 'cases', 'aligned', 'gathered', 'matrix',
             'pmatrix', 'bmatrix', 'vmatrix', 'smallmatrix', 'array', 'tabular',
             'tabular*', 'minipage', 'center', 'description', 'tikzpicture'}

MATCH_THRESHOLD = 0.72

# 人工核验过的内容匹配覆盖（用户表述与项目差异大，但确为同一题）
OVERRIDES = {
    (2021, '2021年北京卷', 8): ('beijing', 8),        # 圆锥形雨量器/降雨量等级
    (2022, '2022年天津卷', 8): ('tianjin', 8),        # 十字歇山顶
    (2023, '2023年全国乙卷（理）', 17): ('national_paper_b_science', 17),   # 橡胶伸缩率试验数据表
    (2023, '2023年全国乙卷（文）', 17): ('national_paper_b_liberal', 17),   # 橡胶伸缩率试验数据表
    (2023, '2023年全国甲卷（文）', 19): ('national_paper_a_liberal', 19),   # 臭氧效应试验数据表格（用户为浓缩版，同题）
    (2023, '2023年上海卷', 17): ('shanghai', 18),     # 直四棱柱示意图（项目内题号偏移）
}


# 项目 tex 正文未引用但 img 目录确有对应图片的孤儿图（人工核对后补用）
FIG_OVERRIDES = {
    (2022, '2022年全国甲卷（文）', 19): ['img/2022/national_paper_a_liberal/q19_fig1.png'],
}


# ---------------------------------------------------------------------------
# 文本工具
# ---------------------------------------------------------------------------

def cjk(s):
    """只保留汉字，用于题目内容比对（同一题的汉字串几乎完全一致）。"""
    s = re.sub(r'\\textsf\{\s*\[插入图片：.*?\]\s*\}', '', s)
    return re.sub(r'[^\u4e00-\u9fff]', '', s)


def strip_answer_solution(body):
    for env in ('answer', 'solution'):
        while True:
            m = re.search(r'\\begin\{' + env + r'\}', body)
            if not m:
                break
            _, end = find_env(body, m.start(), env)
            body = body[:m.start()] + body[end + len('\\end{' + env + '}'):]
    return body


# ---------------------------------------------------------------------------
# 用户文件扫描：小节 -> 部分 -> 题目（带占位符位置）
# ---------------------------------------------------------------------------

def scan_enum(ebody):
    """扫描一个 enumerate 顶层。返回 [(prob, items)]，item 含
    text_start/text_end（ebody 内）与 phs=[(文本, (start,end) in ebody)]。"""
    counter = 0
    items = []
    cur = None
    j = 0
    n = len(ebody)
    while j < n:
        if ebody.startswith('\\begin{', j):
            m = BEGIN_RE.match(ebody[j:])
            if m and m.group(1) in SKIP_ENVS:
                _, end = find_env(ebody, j, m.group(1))
                j = end
                continue
            j += len(m.group(0)) if m else 1
            continue
        if ebody.startswith('\\item', j) and not ebody.startswith('\\itemize', j):
            counter += 1
            cur = {'prob': counter, 'start': j, 'end': None, 'phs': []}
            items.append(cur)
            j += 5
            continue
        m2 = re.match(r'\\addtocounter\{enumi\}\{\+(\d+)\}', ebody[j:])
        if m2:
            counter += int(m2.group(1))
            j += m2.end()
            continue
        m3 = PH_RE.match(ebody[j:])
        if m3:
            if cur is not None:
                cur['phs'].append((m3.group(1), (j, j + m3.end())))
            j += m3.end()
            continue
        j += 1
    for k in range(len(items)):
        if k + 1 < len(items):
            items[k]['end'] = items[k + 1]['start']
        else:
            items[k]['end'] = n
    return items


def scan_subsection(body):
    """返回 [(part名, items)]，位置均为 body 坐标。"""
    out = []
    i = 0
    n = len(body)
    while i < n:
        m = re.search(r'\\item\[([^\]]*)\]', body[i:])
        if not m:
            break
        part = m.group(1)
        rel = body[i + m.end():]
        em = re.search(r'\\begin{enumerate}', rel)
        if not em:
            i += m.end()
            continue
        enum_start = i + m.end() + em.start()
        inner, end = find_env(body, enum_start, 'enumerate')
        out.append((part, scan_enum(body[inner:end])))
        # 修正为 body 坐标
        items = out[-1][1]
        for it in items:
            it['start'] += inner
            it['end'] += inner
            it['phs'] = [(t, (s + inner, e + inner)) for t, (s, e) in it['phs']]
        i = end
    return out


# ---------------------------------------------------------------------------
# 项目试卷匹配
# ---------------------------------------------------------------------------

_paper_cache = {}


def get_paper(year, paper):
    key = (year, paper)
    if key not in _paper_cache:
        path = os.path.join(PROJ_ROOT, 'content', str(year), paper + '.tex')
        _paper_cache[key] = ProjectPaper(path)
    return _paper_cache[key]


def _prob_cjk(prob):
    return cjk(strip_answer_solution(prob['body']))


def best_match(year, mapped_paper, user_cjk, user_prob):
    """返回 (ratio, paper, prob_num, mode)。匹配优先级：
    1) 映射试卷同题号且内容相近（>=0.6，处理同一题的不同表述）
    2) 映射试卷内最佳匹配（>= 阈值）
    3) 同年其它试卷明显更优（+0.05 且 >= 阈值，处理用户文件中混入他卷题目）
    4) 位置兜底：映射试卷同题号有图/表（内容比对失败但题号对齐）
    """
    def scan(paper):
        proj = get_paper(year, paper)
        best = (0.0, paper, None)
        for prob in proj.problems:
            pc = _prob_cjk(prob)
            if len(pc) < 6:
                continue
            r = SequenceMatcher(None, user_cjk, pc).ratio()
            if r > best[0]:
                best = (r, paper, prob['num'])
        return best

    mapped = scan(mapped_paper)
    proj = get_paper(year, mapped_paper)
    num_prob = proj.problem(user_prob) if user_prob else None
    num_ratio = 0.0
    if num_prob is not None:
        pc = _prob_cjk(num_prob)
        if len(pc) >= 6:
            num_ratio = SequenceMatcher(None, user_cjk, pc).ratio()
    if num_ratio >= 0.6:
        return (num_ratio, mapped_paper, user_prob, 'same-num')
    if mapped[0] >= MATCH_THRESHOLD:
        return (mapped[0], mapped_paper, mapped[2], 'mapped')
    best = mapped
    proj_dir = os.path.join(PROJ_ROOT, 'content', str(year))
    for fn in sorted(os.listdir(proj_dir)):
        if not fn.endswith('.tex') or 'spring' in fn:
            continue
        paper = fn[:-4]
        if paper == mapped_paper:
            continue
        cand = scan(paper)
        if cand[0] > best[0] + 0.05 and cand[0] >= MATCH_THRESHOLD:
            best = cand
    if best[2] is not None and best[0] >= MATCH_THRESHOLD:
        return (best[0], best[1], best[2], 'cross')
    return (0.0, None, None, 'none')


# ---------------------------------------------------------------------------
# 图片引用与宽度
# ---------------------------------------------------------------------------

def img_ref(proj_path):
    rel = proj_path
    for prefix in ('img_repaint/', 'img/'):
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
            break
    if rel.endswith('.tex'):
        rel = rel[:-4] + '.png'
    return IMG_PREFIX + '/' + rel.replace('\\', '/')


def figure_width(proj_path, opt, paper):
    key = proj_path
    alt = key.replace('img_repaint/', 'img/')
    for k in (key, alt):
        if k in paper.layouts:
            return paper.layouts[k][0]
        if k in paper.global_layouts:
            return paper.global_layouts[k][0]
    if opt:
        m = re.search(r'(?:max width|width)=([^\s,]+)', opt)
        if m:
            return m.group(1)
    return '0.65\\linewidth'


def choice_width(prob, idx):
    m = re.search(r'\\choicebitmap(?![a-zA-Z])\s*\[([^\]]*)\]', prob['body'])
    if m and 'width=' in m.group(1):
        return m.group(1).split('width=', 1)[1].strip()
    return '0.15\\paperwidth'


# ---------------------------------------------------------------------------
# 替换文本生成
# ---------------------------------------------------------------------------

def fig_block(proj_path, width):
    return ('{\\centering\n'
            '\\includegraphics[width=%s]{%s}\n'
            '\\par}' % (width, img_ref(proj_path)))


def image_choices_tabular(prob, paper):
    """四选项图片 -> tabular*（4 列 c），不带外层 {\\centering...\\par}。"""
    imgs = prob['choice_images']
    w = choice_width(prob, 0)
    cells = []
    for i, (_name, path, _opt) in enumerate(imgs):
        cells.append('\\(\\text{%s. }\\includegraphics[width=%s]{%s}\\)'
                     % ('ABCDE'[i], w, img_ref(path)))
    return ('\\begin{tabular*}{\\linewidth}{@{}@{\\extracolsep{\\fill}}cccc@{}}\n'
            '            %s\n'
            '        \\end{tabular*}' % '  &  '.join(cells))


def image_choices_table(prob, paper):
    """四选项图片 -> 用户样式（外层带 {\\centering...\\par}，用于替换占位符）。"""
    return ('{\\centering\n'
            '            ' + image_choices_tabular(prob, paper) + '\n'
            '        \\par}')


def find_option_tabular(item_text):
    """在题目文本中找选项 tabular*（含 \\text{A. } 等单元格），返回 (start,end)。"""
    for m in re.finditer(r'\\begin\{tabular\*\}', item_text):
        inner, end = find_env(item_text, m.start(), 'tabular*')
        body = item_text[inner:end]
        if re.search(r'\\text\{[A-E]\.\s?', body):
            return (m.start(), end + len('\\end{tabular*}'))
    return None


def find_alpha_enumerate(item_text):
    """找 label=\\Alph*. 的嵌套 enumerate（多选图题用）。返回 (start,end)。"""
    for m in re.finditer(r'\\begin\{enumerate\}\s*\[label=\\Alph\*\.\]', item_text):
        _, end = find_env(item_text, m.start(), 'enumerate')
        return (m.start(), end + len('\\end{enumerate}'))
    return None


def build_edit_plan(year, sub_title, ut, body):
    """对一个小节生成编辑计划 [(start, end, replacement)]。返回 (edits, report)。"""
    edits = []
    report = []
    mapping = gk_papers.FILL_MAPPING.get(year, {})
    mapped_paper = mapping.get(ut)
    if mapped_paper is None:
        return edits, [('%s: 无试卷映射' % sub_title)]
    for part, items in scan_subsection(body):
        for it in items:
            if not it['phs']:
                continue
            item_text = body[it['start']:it['end']]
            user_cjk = cjk(item_text)
            if len(user_cjk) < 6:
                report.append('%s %s Q%d: 题目文本过短，无法匹配' % (sub_title, part, it['prob']))
                continue
            ov = OVERRIDES.get((year, sub_title, it['prob']))
            if ov is not None:
                ratio, paper, pnum, mode = 1.0, ov[0], ov[1], 'override'
                report.append('%s %s Q%d: 人工覆盖 -> %s Q%d' % (sub_title, part, it['prob'], paper, pnum))
            else:
                ratio, paper, pnum, mode = best_match(year, mapped_paper, user_cjk, it['prob'])
            if paper is None:
                report.append('%s %s Q%d: 未找到对应项目题（ratio=%.2f）phs=%s'
                              % (sub_title, part, it['prob'], ratio, [p[0] for p in it['phs']]))
                continue
            if mode not in ('mapped', 'same-num', 'override'):
                report.append('%s %s Q%d: 内容匹配到 %s Q%d（%s，ratio=%.2f，映射=%s）'
                              % (sub_title, part, it['prob'], paper, pnum, mode, ratio, mapped_paper))
            proj = get_paper(year, paper)
            prob = proj.problem(pnum)
            figs = prob['figures']
            cif = prob['choice_images']
            if not figs:
                fo = FIG_OVERRIDES.get((year, sub_title, it['prob']))
                if fo:
                    figs = [(None, p, '') for p in fo]
                    report.append('%s %s Q%d: 孤儿图覆盖 %s' % (sub_title, part, it['prob'], fo))
            phs = it['phs']
            # ---- 选项图片 ----
            if cif:
                tab = find_option_tabular(item_text)
                alpha = find_alpha_enumerate(item_text)
                # 主图（若有）放到占位符处
                main_fig = ''
                if figs:
                    main_fig = fig_block(figs[0][1], figure_width(figs[0][1], figs[0][2], proj)) + '\n'
                if tab:
                    # 有选项表格：去掉占位符，只重写表格本体（保留外层 {\\centering...\\par}）
                    # 不插主图：占位符（如“三视图选项”）只对应选项图，避免主图错位
                    tstart, tend = tab
                    new_tab = image_choices_tabular(prob, proj)
                    edits.append((it['start'] + tstart, it['start'] + tend, new_tab))
                    for t, (s, e) in phs:
                        edits.append((s, e, ''))
                    report.append('%s %s Q%d: 选项图填入表格 %s' % (sub_title, part, it['prob'], paper))
                elif alpha:
                    astart, aend = alpha
                    alpha_body = body[it['start'] + astart: it['start'] + aend]
                    new_alpha = convert_alpha_enum(alpha_body, prob, proj)
                    edits.append((it['start'] + astart, it['start'] + aend, new_alpha))
                    for t, (s, e) in phs:
                        edits.append((s, e, main_fig))
                    report.append('%s %s Q%d: 嵌套A/B/C/D选项填入图片 %s' % (sub_title, part, it['prob'], paper))
                else:
                    # 无表格：占位符 -> 选项图表格（用户占位符只对应选项图，
                    # 不附带主图，避免“三视图选项”这类占位符多插错位主图）
                    for t, (s, e) in phs:
                        edits.append((s, e, image_choices_table(prob, proj)))
                    report.append('%s %s Q%d: 占位符 -> 选项图 %s' % (sub_title, part, it['prob'], paper))
                continue
            # ---- 普通图 ----
            if figs:
                for k, (t, (s, e)) in enumerate(phs):
                    if k < len(figs):
                        f = figs[k]
                        repl = fig_block(f[1], figure_width(f[1], f[2], proj))
                    else:
                        repl = ''
                        report.append('%s %s Q%d: 占位符多于图片数 %s' % (sub_title, part, it['prob'], t))
                    edits.append((s, e, repl))
                if len(phs) == 1 and len(figs) > 1:
                    # 一个占位符对应多图：合并为连续图块
                    pass
                report.append('%s %s Q%d: 图 x%d -> %s Q%d' % (sub_title, part, it['prob'], len(figs), paper, pnum))
                continue
            # ---- 表格 ----
            tables = extract_tables(prob['body'])
            if tables:
                repl = '\n\n'.join(convert_table(t) for t in tables)
                for t, (s, e) in phs:
                    edits.append((s, e, repl))
                report.append('%s %s Q%d: 插入数据表格 %s Q%d' % (sub_title, part, it['prob'], paper, pnum))
                continue
            report.append('%s %s Q%d: 项目无图无表 phs=%s' % (sub_title, part, it['prob'], [p[0] for p in phs]))
    return edits, report


def convert_alpha_enum(alpha_body, prob, proj):
    """把 label=\\Alph*. 嵌套列表中的 \\item 图X 换成图片。"""
    imgs = prob['choice_images']
    lines = []
    idx = 0
    for ln in alpha_body.splitlines():
        if re.match(r'\s*\\item', ln) and idx < len(imgs):
            w = choice_width(prob, idx)
            repl = '\\item \\includegraphics[width=%s]{%s}' % (w, img_ref(imgs[idx][1]))
            lines.append(re.sub(r'\\item.*', lambda m: repl, ln))
            idx += 1
        else:
            lines.append(ln)
    return '\n'.join(lines)


def extract_tables(prob_body):
    out = []
    pos = 0
    while True:
        m = re.search(r'\\begin\{center\}', prob_body[pos:])
        if not m:
            break
        start = pos + m.start()
        _, end_start = find_env(prob_body, start, 'center')
        end = end_start + len('\\end{center}')
        block = prob_body[start:end]
        if 'tabular' in block:
            out.append(block)
        pos = end
    return out


def convert_table(block):
    """项目表格 -> 用户文件可用格式（$...$ 数学、去 \\allowbreak）。"""
    s = block
    s = re.sub(r'\\allowbreak', '', s)
    s = s.replace('\\(', '$').replace('\\)', '$')
    return s


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def apply_edits(text, edits):
    for start, end, repl in sorted(edits, key=lambda x: -x[0]):
        text = text[:start] + repl + text[end:]
    return text


def fill_year(year, dry_run=False):
    path = os.path.join(GAOKAO, '%d.tex' % year)
    txt = open(path, encoding='utf-8').read()
    subs = parse_user_subsections(txt)
    new_parts = []
    all_edits = 0
    report = []
    for sub in subs:
        body = sub['body']
        edits, rp = build_edit_plan(year, sub['title'], sub['title'][5:], body)
        all_edits += len(edits)
        report.extend(rp)
        if edits:
            body = apply_edits(body, edits)
        new_parts.append(sub['header'] + body)
    out = '\n'.join(new_parts)
    # 项目宏 \\e（自然指数）-> \\mathrm{e}（讲义未定义 \\e）
    out = re.sub(r'\\e(?![a-zA-Z])', '{\\\\mathrm{e}}', out)
    if not dry_run:
        open(path, 'w', encoding='utf-8').write(out)
    return out, all_edits, report


def main():
    years = [int(a) for a in sys.argv[1:] if a.isdigit()] or list(range(2020, 2027))
    dry = '--dry' in sys.argv
    for year in years:
        out, nedit, report = fill_year(year, dry_run=dry)
        print('==== %d : edits=%d' % (year, nedit))
        for r in report:
            print('   ', r)


if __name__ == '__main__':
    main()
