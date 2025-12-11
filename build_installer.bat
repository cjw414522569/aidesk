@echo off
chcp 65001 >nul
echo ====================================
echo AIDesk 安装包构建脚本
echo ====================================
echo.

REM 检查 Inno Setup 是否安装
if not exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    echo [错误] 未找到 Inno Setup 6
    echo 请从 https://jrsoftware.org/isdl.php 下载并安装 Inno Setup
    pause
    exit /b 1
)

echo [1/2] 检查构建文件...
if not exist "dist\AIDesk\AIDesk.exe" (
    echo [错误] 未找到 dist\AIDesk\AIDesk.exe，请先运行 build.bat
    pause
    exit /b 1
)

echo [2/2] 生成安装包...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss

if %errorlevel% equ 0 (
    echo.
    echo ====================================
    echo 安装包构建成功！
    echo 输出位置: build\installer\
    echo ====================================
    explorer build\installer
) else (
    echo.
    echo [错误] 安装包构建失败
)

pause