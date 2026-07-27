@echo off
chcp 65001 >nul
cd /d "%~dp0"
title face_bot — 打包

echo ============================================
echo   打包 face_bot 成单 exe
echo ============================================
echo.

where python >nul 2>&1 || (
    echo [X] 没 Python。先装:https://python.org/download
    pause & exit /b
)

echo [1/2] 安装依赖...
python -m pip install --quiet --disable-pip-version-check pyautogui Pillow pyinstaller

echo [2/2] 打包(PyInstaller,大概 30-60 秒)...
python -m PyInstaller --noconfirm --onefile ^
    --name face_bot ^
    --add-data "templates;templates" ^
    --add-data "faces;faces" ^
    face_bot.py

if exist "dist\face_bot.exe" (
    echo.
    echo ================================
    echo   打包成功! 输出: dist\face_bot.exe
    echo ================================
) else (
    echo [X] 打包失败,看上面 PyInstaller 输出
)

pause
