#!/usr/bin/env python3
"""
Reorder \subsection{} blocks in Gaokao .tex files and add \label{gk:...} after each.
Rules:
1. National exams (全国卷) first: 大纲卷 → 老高考卷 → 新高考卷
2. Then local exams (地方卷), sorted by city/province pinyin first letter
3. Within same exam type: 理 before 文
"""
import re
import os
import sys

# Pinyin first letter mapping for city/province names
PINYIN_FIRST = {
    '安徽': 'A',
    '北京': 'B',
    '重庆': 'C',
    '福建': 'F',
    '广东': 'G',
    '湖北': 'H',
    '湖南': 'H',
    '江苏': 'J',
    '江西': 'J',
    '辽宁': 'L',
    '山东': 'S',
    '陕西': 'S',
    '上海': 'S',
    '四川': 'S',
    '天津': 'T',
    '浙江': 'Z',
}

def parse_subsection_name(name):
    """
    Parse a subsection name like '2024年全国甲卷（理）' or '2024年新高考I卷'
    Returns dict with: full_name, year, exam_type, exam_num, arts_sci
    exam_type: 'dagang' | 'laogaokao' | 'xingaokao' | 'local'
    """
    # Remove the year prefix for analysis
    # Pattern: YYYY年XXX
    m = re.match(r'(\d{4})年(.+)', name)
    if not m:
        return None

    year = int(m.group(1))
    rest = m.group(2)

    # Check for 理/文 suffix
    arts_sci = None
    if '（理）' in rest or '(理)' in rest:
        arts_sci = '理'
        rest_clean = rest.replace('（理）', '').replace('(理)', '')
    elif '（文）' in rest or '(文)' in rest:
        arts_sci = '文'
        rest_clean = rest.replace('（文）', '').replace('(文)', '')
    else:
        arts_sci = None
        rest_clean = rest

    # Classify exam type
    if '大纲' in rest_clean:
        exam_type = 'dagang'
    elif '新高考' in rest_clean:
        exam_type = 'xingaokao'
    elif '全国' in rest_clean:
        # For 2025+, 全国卷 are effectively 新高考 (the "新" was dropped)
        if year >= 2025:
            exam_type = 'xingaokao'
        else:
            exam_type = 'laogaokao'
    else:
        exam_type = 'local'

    # Extract exam number/letter (I, II, III, 甲, 乙, etc.)
    exam_num = None
    num_match = re.search(r'([IV]+|甲|乙|丙)', rest_clean)
    if num_match:
        exam_num = num_match.group(1)

    # Extract city/province name for local exams
    city = None
    if exam_type == 'local':
        city_match = re.match(r'([一-鿿]+)卷', rest_clean)
        if city_match:
            city = city_match.group(1)

    return {
        'full_name': name,
        'year': year,
        'exam_type': exam_type,
        'exam_num': exam_num,
        'arts_sci': arts_sci,
        'city': city,
    }


def sort_key(info):
    """
    Generate a sort key tuple for a subsection.
    """
    exam_type_order = {'dagang': 0, 'laogaokao': 1, 'xingaokao': 2, 'local': 3}

    # Exam number ordering
    num_order = {
        'I': 0, 'II': 1, 'III': 2, 'IV': 3,
        '甲': 0, '乙': 1, '丙': 2,
    }

    # Arts/Science ordering: 理 before 文, None in the middle
    arts_sci_order = {'理': 0, None: 1, '文': 2}

    if info['exam_type'] == 'local':
        # Sort by: (1) exam_type, (2) pinyin first letter, (3) city name, (4) exam_num, (5) 理/文
        pinyin = PINYIN_FIRST.get(info['city'], 'Z') if info['city'] else 'Z'
        return (
            exam_type_order[info['exam_type']],
            pinyin,
            info['city'] or '',
            num_order.get(info['exam_num'], 99),
            arts_sci_order.get(info['arts_sci'], 1),
        )
    else:
        # National exams: sort by (1) exam_type, (2) exam_num, (3) 理/文
        return (
            exam_type_order[info['exam_type']],
            num_order.get(info['exam_num'], 99),
            arts_sci_order.get(info['arts_sci'], 1),
        )


def process_file(filepath):
    """Process a single .tex file: reorder subsections and add labels."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split content into: preamble (before first \subsection), subsections, and postamble
    # Find the \section line
    section_match = re.search(r'(\\section\{[^}]+\}.*?\n)', content)
    if not section_match:
        print(f"  WARNING: No \\section found in {filepath}")
        return False

    section_start = section_match.start()
    section_header = section_match.group(1)

    # Everything after the section header until first \subsection is preamble text
    after_section = content[section_match.end():]

    # Find all \subsection blocks
    # Pattern: \subsection{...} followed by content until next \subsection or end
    subsec_pattern = re.compile(r'\\subsection\{([^}]+)\}', re.MULTILINE)

    # Find all subsection positions
    positions = []
    for m in subsec_pattern.finditer(after_section):
        positions.append((m.start(), m.end(), m.group(1)))

    if not positions:
        print(f"  No subsections found in {filepath}")
        return False

    # Extract subsection blocks
    blocks = []
    for i, (start, end, name) in enumerate(positions):
        content_start = end
        if i + 1 < len(positions):
            content_end = positions[i + 1][0]
        else:
            content_end = len(after_section)

        block_content = after_section[content_start:content_end]
        blocks.append({
            'name': name,
            'content': block_content,
        })

    # Parse and sort
    parsed_blocks = []
    for block in blocks:
        info = parse_subsection_name(block['name'])
        if info:
            parsed_blocks.append((info, block))
        else:
            print(f"  WARNING: Could not parse subsection name: {block['name']}")
            parsed_blocks.append((None, block))

    # Sort
    def sort_key_wrapper(item):
        info, block = item
        if info is None:
            return (999,)  # Put unparseable at the end
        return sort_key(info)

    sorted_blocks = sorted(parsed_blocks, key=sort_key_wrapper)

    # Check if reordering is needed
    original_names = [b['name'] for _, b in parsed_blocks]
    sorted_names = [b['name'] for _, b in sorted_blocks]

    if original_names == sorted_names:
        # No reordering needed, but still need to add labels
        pass

    # Build new content
    result = content[:section_match.end()]

    for info, block in sorted_blocks:
        name = block['name']
        subsec_line = f'\\subsection{{{name}}}'
        label = f'\\label{{gk:{name}}}'

        # Check if label already exists in the block content
        if '\\label{gk:' in block['content']:
            # Label already exists, don't add another
            result += subsec_line + block['content']
        else:
            # Add label after the subsection line
            # The block_content starts right after the \subsection{...}
            # We need to insert the label
            result += subsec_line + label + '\n' + block['content']

    # Add any text after the last subsection
    if positions:
        last_end = positions[-1][1]
        # Find what comes after the last subsection's content
        # The blocks already include content up to the next subsection or end
        pass  # Already handled by including content in blocks

    # Write result
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(result)

    # Report changes
    changes = []
    for i, ((info_orig, b_orig), (info_sorted, b_sorted)) in enumerate(zip(parsed_blocks, sorted_blocks)):
        if b_orig['name'] != b_sorted['name']:
            changes.append(f"    Moved '{b_orig['name']}' (was #{i+1}, now at new position)")

    if changes:
        print(f"  Reordered {filepath}:")
        for c in changes:
            print(c)
    else:
        print(f"  No reordering needed for {filepath}")

    print(f"  Added labels to {len(sorted_blocks)} subsections")
    return True


def main():
    target_dir = r'd:\Ark_sighthui\latex\gzsxjy\GaoKao'

    tex_files = sorted([f for f in os.listdir(target_dir) if f.endswith('.tex') and f != 'reorder_sections.py'])

    print(f"Processing {len(tex_files)} .tex files...")
    print()

    for tex_file in tex_files:
        filepath = os.path.join(target_dir, tex_file)
        process_file(filepath)
        print()

    print("Done!")


if __name__ == '__main__':
    main()
