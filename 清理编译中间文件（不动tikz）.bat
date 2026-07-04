@echo off
chcp 65001 >nul
echo ============================================
echo   清理 LaTeX 编译中间文件
echo   （保留 tikz 外部化缓存，免去重绘等待）
echo ============================================

echo.
echo 正在清理根目录中间文件...
del /q *.aux *.log *.out *.toc *.lof *.lot *.bbl *.blg *.ilg *.ind *.idx *.synctex.gz *.thm 2>nul

echo.
echo 正在清理各章节子目录中间文件...
for /r %%f in (*.aux) do del /q "%%f" 2>nul

echo.
echo ============================================
echo   完成！以下文件已保留，不会被清理：
echo   - tikz111\*.pdf （tikz 图片缓存）
echo   - tikz111\*.md5 （tikz 增量检测）
echo   - *.pdf （编译产物）
echo   - *.tex, *.bib, *.cls （源文件）
echo ============================================
