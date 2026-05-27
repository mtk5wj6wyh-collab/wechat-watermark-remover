@echo off
chcp 65001 >nul
echo ============================================
echo   WeChat Image Watermark Removal Tool (Force Re-process)
echo ============================================
echo.
echo   WARNING: This will re-process ALL images, overwriting existing results!
echo.
pause

cd /d "%~dp0"

REM Force re-process all images
REM -f: force mode
REM -p medium: medium strength

C:\Users\admin\.workbuddy\binaries\python\versions\3.14.3\python.exe batch_remove_watermark.py -p medium -f

echo.
echo Done! Output: wechat_articles\<article_name>\images_new\
echo.
pause
