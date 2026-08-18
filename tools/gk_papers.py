# -*- coding: utf-8 -*-
"""试卷映射表：用户讲义 subsection 标题 <-> 项目 content/YYYY/paper.tex。"""
import os
import re

PROJ_ROOT = os.environ.get('GK_PROJ_ROOT',
                           os.path.join(os.environ['TEMP'],
                                        'Gaokao-Math-Problems-Compilation'))
PROJ_CONTENT = os.path.join(PROJ_ROOT, 'content')


def project_chapter_title(year, paper):
    txt = open(os.path.join(PROJ_CONTENT, str(year), paper + '.tex'),
               encoding='utf-8').read()
    m = re.search(r'\\chapter\{([^}]*)\}', txt)
    return m.group(1) if m else ''


def normalize_project_title(title):
    """项目 \\chapter 标题 -> 规范化（去掉年份、春秋文理后缀）。"""
    t = re.sub(r'^\d{4}年', '', title)
    t = t.replace('（秋文）', '（文）')
    t = t.replace('（秋理）', '（理）')
    t = t.replace('（秋）', '')
    return t


def normalize_user_title(title):
    return re.sub(r'^\d{4}年', '', title)


# 2010-2014 用户把项目“新课标卷”命名为“全国卷”
XKB_AS_QUANGUO = {2010, 2011, 2012, 2013, 2014}

# 2017/2018 上海文理不分科：用户有两个空 subsection（理/文），项目只有一份试卷
SHANGHAI_SINGLE = {2017, 2018}


def build_old_mapping(year):
    """返回 {用户 subsection 标题: 项目 paper 文件名}（2010-2019 转换用）。"""
    proj_dir = os.path.join(PROJ_CONTENT, str(year))
    if not os.path.isdir(proj_dir):
        return {}
    by_title = {}
    for f in sorted(os.listdir(proj_dir)):
        if not f.endswith('.tex'):
            continue
        paper = f[:-4]
        t = normalize_project_title(project_chapter_title(year, paper))
        if t.endswith('（春）'):
            continue
        by_title.setdefault(t, paper)
    mapping = {}
    for title, paper in by_title.items():
        ut = title
        if year in XKB_AS_QUANGUO:
            if ut.startswith('新课标I卷'):
                ut = '全国I卷' + ut[len('新课标I卷'):]
            elif ut.startswith('新课标II卷'):
                ut = '全国II卷' + ut[len('新课标II卷'):]
            elif ut.startswith('新课标卷'):
                ut = '全国卷' + ut[len('新课标卷'):]
        if year in SHANGHAI_SINGLE and ut.startswith('上海卷'):
            ut = '上海卷'
        mapping.setdefault(ut, paper)
    return mapping


# 2020-2026 图片补全映射：用户 subsection 名（不含年份） -> 项目 paper 文件名
FILL_MAPPING = {
    2020: {
        '全国I卷（理）': 'national_paper_1_science',
        '全国I卷（文）': 'national_paper_1_liberal',
        '全国II卷（理）': 'national_paper_2_science',
        '全国II卷（文）': 'national_paper_2_liberal',
        '全国III卷（理）': 'national_paper_3_science',
        '全国III卷（文）': 'national_paper_3_liberal',
        '新高考I卷': 'new_gaokao_paper_1',
        '新高考II卷': 'new_gaokao_paper_2',
        '北京卷': 'beijing',
        '江苏卷': 'jiangsu',
        '上海卷': 'shanghai',
        '天津卷': 'tianjin',
        '浙江卷': 'zhejiang',
    },
    2021: {
        '全国I卷（理）': 'national_paper_a_science',
        '全国I卷（文）': 'national_paper_a_liberal',
        '全国II卷（理）': 'national_paper_b_science',
        '全国II卷（文）': 'national_paper_b_liberal',
        '新高考I卷': 'new_gaokao_paper_1',
        '新高考II卷': 'new_gaokao_paper_2',
        '北京卷': 'beijing',
        '上海卷': 'shanghai',
        '天津卷': 'tianjin',
        '浙江卷': 'zhejiang',
    },
    2022: {
        '全国甲卷（理）': 'national_paper_a_science',
        '全国甲卷（文）': 'national_paper_a_liberal',
        '全国乙卷（理）': 'national_paper_b_science',
        '全国乙卷（文）': 'national_paper_b_liberal',
        '新高考I卷': 'new_gaokao_paper_1',
        '新高考II卷': 'new_gaokao_paper_2',
        '北京卷': 'beijing',
        '上海卷': 'shanghai',
        '天津卷': 'tianjin',
        '浙江卷': 'zhejiang',
    },
    2023: {
        '全国甲卷（理）': 'national_paper_a_science',
        '全国甲卷（文）': 'national_paper_a_liberal',
        '全国乙卷（理）': 'national_paper_b_science',
        '全国乙卷（文）': 'national_paper_b_liberal',
        '新高考I卷': 'new_gaokao_paper_1',
        '新高考II卷': 'new_gaokao_paper_2',
        '北京卷': 'beijing',
        '上海卷': 'shanghai',
        '天津卷': 'tianjin',
    },
    2024: {
        '全国甲卷（理）': 'national_paper_a_science',
        '全国甲卷（文）': 'national_paper_a_liberal',
        '新高考I卷': 'new_gaokao_paper_1',
        '新高考II卷': 'new_gaokao_paper_2',
        '北京卷': 'beijing',
        '上海卷': 'shanghai',
        '天津卷': 'tianjin',
    },
    2025: {
        '全国I卷': 'national_paper_1',
        '全国II卷': 'national_paper_2',
        '北京卷': 'beijing',
        '上海卷': 'shanghai',
        '天津卷': 'tianjin',
    },
    2026: {
        '全国I卷': 'national_paper_1',
        '全国II卷': 'national_paper_2',
        '北京卷': 'beijing',
        '上海卷': 'shanghai',
        '天津卷': 'tianjin',
    },
}
