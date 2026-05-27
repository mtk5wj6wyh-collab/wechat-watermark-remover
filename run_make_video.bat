@echo off
chcp 65001 >nul
echo ============================================
echo   Images to Video Generator
echo ============================================
echo.

cd /d "%~dp0"

REM Default: process all articles, 3s per image, fade transition
REM Customize: -t 5 --title "My Title" --music bgm.mp3

C:\Users\admin\.workbuddy\binaries\python\versions\3.14.3\python.exe images_to_video.py -d wechat_articles --all -t 3 --transition fade

echo.
echo Done!
echo.
pause
