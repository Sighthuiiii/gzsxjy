# -*- coding: utf-8 -*-
"""驱动：把 2010-2019 年项目试卷转换为讲义 GaoKao/YYYY.tex。"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gk_common
import gk_papers
from gk_convert_2010_2019 import convert_paper
from gk_common import ProjectPaper

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAOKAO = os.path.join(REPO, 'GaoKao')
IMG_PREFIX = 'GaoKao/images'

# 特殊小节说明（项目无对应试卷）
NOTES = {
    (2015, '2015年江西卷（理）'): '（2015年起江西省改用全国I卷，本年度题目见“2015年全国I卷（理）”。）',
    (2015, '2015年江西卷（文）'): '（2015年起江西省改用全国I卷，本年度题目见“2015年全国I卷（文）”。）',
    (2015, '2015年辽宁卷（理）'): '（2015年起辽宁省改用全国II卷，本年度题目见“2015年全国II卷（理）”。）',
    (2015, '2015年辽宁卷（文）'): '（2015年起辽宁省改用全国II卷，本年度题目见“2015年全国II卷（文）”。）',
    (2017, '2017年上海卷（文）'): '（上海自2017年起文理不分科，本卷与“2017年上海卷（理）”同卷。）',
    (2018, '2018年上海卷（文）'): '（上海自2018年起文理不分科，本卷与“2018年上海卷（理）”同卷。）',
}


def main():
    report = []
    for year in range(2010, 2020):
        user_path = os.path.join(GAOKAO, '%d.tex' % year)
        with open(user_path, encoding='utf-8') as f:
            old = f.read()
        # 保留原 \\section 行
        sec_m = re.search(r'\\section\{[^}]*\}', old)
        sec_line = sec_m.group(0) if sec_m else '\\section{%d年高考题}' % year
        titles = re.findall(r'\\subsection\{([^}]*)\}(?:\s*\\label\{([^}]*)\})?', old)
        mapping = gk_papers.build_old_mapping(year)
        lines = [sec_line]
        stats = {'papers': 0, 'problems': 0, 'imgs': 0}
        for title, label in titles:
            ut = title[5:]
            paper_name = mapping.get(ut)
            lines.append('')
            lab = label if label else 'gk:%s' % title
            lines.append('\\subsection{%s}\\label{%s}' % (title, lab))
            lines.append('')
            if (year, title) in NOTES:
                lines.append(NOTES[(year, title)])
                lines.append('')
                continue
            # 2017/2018 上海文理同卷：文卷用备注
            if paper_name is None and year in (2017, 2018) and ut.startswith('上海卷'):
                if ut == '上海卷（文）':
                    lines.append('（上海自%d年起文理不分科，本卷与“%d年上海卷（理）”同卷。）' % (year, year))
                else:
                    paper_name = mapping.get('上海卷')
            if paper_name is None:
                report.append('%d %s: 未找到项目试卷，保留空小节' % (year, title))
                lines.append('%% [gk-convert] 未找到对应项目试卷')
                lines.append('')
                continue
            paper_path = os.path.join(gk_common.PROJ_CONTENT, str(year), paper_name + '.tex')
            if not os.path.exists(paper_path):
                report.append('%d %s: 缺文件 %s' % (year, title, paper_path))
                lines.append('%% [gk-convert] 缺少试卷文件')
                lines.append('')
                continue
            paper = ProjectPaper(paper_path)
            text = convert_paper(paper, year, title, IMG_PREFIX)
            lines.append(text)
            lines.append('')
            stats['papers'] += 1
            stats['problems'] += len(paper.problems)
            stats['imgs'] += sum(len(p['figures']) + len(p['choice_images']) for p in paper.problems)
        with open(user_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        report.append('%d: papers=%d problems=%d imgrefs=%d' % (year, stats['papers'], stats['problems'], stats['imgs']))
    print('\n'.join(report))


if __name__ == '__main__':
    main()
