@echo off
chcp 65001 >nul
echo ============================================
echo   WeChat Image Watermark Removal Tool
echo ============================================
echo.
echo   Based on watermark detection + LaMa inpainting
echo.

cd /d "%~dp0"

REM -p medium: medium strength (recommended)
REM -p heavy:  stronger effect
REM -p light:  lighter effect

C:\Users\admin\.workbuddy\binaries\python\versions\3.14.3\python.exe batch_remove_watermark.py -p medium

echo.
echo Done! Output: wechat_articles\<article_name>\images_new\
echo.
pause
