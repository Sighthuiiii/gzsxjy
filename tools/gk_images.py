# -*- coding: utf-8 -*-
r"""高考题图片管理工具。

约定：
- 图片统一存放在 GaoKao/images/<年份>/<试卷>/ 下，文件名沿用项目命名
  （q<题号>_fig<n>.png / q<题号>_opt<字母>.png）。
- 项目 img/ 下的位图直接复制；img_repaint/ 下的 TikZ 源图用 ctexbook+styles.tex
  渲染为 PNG（xelatex -> pdftoppm -> PIL 白边裁剪），与讲义白底风格一致。
- 本工具幂等：已存在的图片跳过；扫描 GaoKao/*.tex 里所有 \includegraphics 引用。
"""
import os
import re
import shutil
import subprocess
import sys
import glob

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAOKAO = os.path.join(REPO, 'GaoKao')
IMG_DIR = os.path.join(GAOKAO, 'images')
PROJ_ROOT = os.environ.get('GK_PROJ_ROOT',
                           os.path.join(os.environ['TEMP'],
                                        'Gaokao-Math-Problems-Compilation'))
PROJ_IMG = os.path.join(PROJ_ROOT, 'img')
PROJ_REPAINT = os.path.join(PROJ_ROOT, 'img_repaint')
STYLES = os.path.join(PROJ_ROOT, 'styles.tex')

WORK = os.path.join(os.environ.get('TEMP', '/tmp'), 'gk_imgwork')


def collect_refs():
    refs = set()
    for f in glob.glob(os.path.join(GAOKAO, '*.tex')):
        txt = open(f, encoding='utf-8').read()
        for m in re.finditer(r'\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]*)\}', txt):
            p = m.group(1).replace('\\', '/')
            if p.startswith('GaoKao/images/'):
                refs.add(p)
    return refs


def to_project_path(ref):
    rel = ref[len('GaoKao/images/'):]
    return rel.replace('/', os.sep)


def ensure_image(ref, report):
    rel = to_project_path(ref)
    dest = os.path.join(REPO, ref.replace('/', os.sep))
    if os.path.exists(dest):
        return 'ok'
    src = os.path.join(PROJ_IMG, rel)
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        return 'copied'
    tex_src = os.path.join(PROJ_REPAINT, rel[:-4] + '.tex')
    if os.path.exists(tex_src):
        ok = render_texfig(tex_src, dest)
        return 'rendered' if ok else 'render-failed'
    return 'missing'


def render_texfig(tex_src, dest):
    """渲染 TikZ 源图为 PNG：xelatex 整页编译 -> pdftoppm 转 PNG -> PIL 裁剪白边。"""
    os.makedirs(WORK, exist_ok=True)
    base = 'fig_%08x' % abs(hash(tex_src + '|' + dest))
    wrapper = os.path.join(WORK, base + '.tex')
    with open(wrapper, 'w', encoding='utf-8') as f:
        f.write('\\documentclass{ctexbook}\n'
                '\\input{styles.tex}\n'
                '\\begin{document}\n'
                '\\input{%s}\n'
                '\\end{document}\n' % tex_src.replace('\\', '/'))
    env = dict(os.environ)
    env['TEXINPUTS'] = PROJ_ROOT + os.pathsep
    env['TEXMFOUTPUT'] = WORK
    pdf = os.path.join(WORK, base + '.pdf')
    png = os.path.join(WORK, base + '-1.png')
    try:
        r = subprocess.run(['xelatex', '-interaction=nonstopmode', '-halt-on-error',
                            base + '.tex'],
                           cwd=WORK, env=env, capture_output=True, text=True, timeout=300)
        if not os.path.exists(pdf):
            return False
        r2 = subprocess.run(['pdftoppm', '-png', '-r', '300', pdf, os.path.join(WORK, base)],
                            capture_output=True, text=True, timeout=180)
        if not os.path.exists(png):
            return False
        from PIL import Image, ImageChops
        img = Image.open(png)
        bg = Image.new('RGB', img.size, (255, 255, 255))
        diff = ImageChops.difference(img.convert('RGB'), bg)
        bbox = diff.getbbox()
        if bbox:
            img = img.crop(bbox)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        img.save(dest)
        return True
    except Exception as e:
        print('render error:', e, file=sys.stderr)
        return False


def main():
    refs = sorted(collect_refs())
    stats = {'ok': 0, 'copied': 0, 'rendered': 0, 'render-failed': 0, 'missing': 0}
    report = []
    missing = []
    for ref in refs:
        st = ensure_image(ref, report)
        stats[st] = stats.get(st, 0) + 1
        if st == 'missing':
            missing.append(ref)
        elif st == 'render-failed':
            missing.append(ref + ' (render-failed)')
    print('total refs: %d' % len(refs))
    for k, v in stats.items():
        print('%s: %d' % (k, v))
    if missing:
        print('--- MISSING ---')
        for m in missing:
            print(m)
    # 统计体积
    total = 0
    n = 0
    for root, dirs, files in os.walk(IMG_DIR):
        for fn in files:
            if fn.endswith('.png'):
                total += os.path.getsize(os.path.join(root, fn))
                n += 1
    print('images on disk: %d, total %.1f MB' % (n, total / 1048576))


if __name__ == '__main__':
    main()
