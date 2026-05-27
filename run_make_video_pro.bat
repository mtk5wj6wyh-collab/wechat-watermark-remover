@echo off
echo ========================================
echo  Generate Video with Script + TTS + Subtitles
echo ========================================
set SCRIPT_DIR=%~dp0
set PYTHON=C:\Users\admin\.workbuddy\binaries\python\versions\3.14.3\python.exe

echo.
echo [1/2] Running images_to_video_pro.py ...
"%PYTHON%" "%SCRIPT_DIR%images_to_video_pro.py" -d "%SCRIPT_DIR%wechat_articles\天 沐 琴 台" -s "%SCRIPT_DIR%script.txt"

echo.
if %ERRORLEVEL% EQU 0 (
    echo Done!
) else (
    echo Error occurred. Check output above.
)
pause
