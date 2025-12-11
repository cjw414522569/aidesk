@echo off
echo 开始打包 AIDesk...
echo.

REM 安装所有依赖
echo 正在安装依赖包...
#pip install -r requirements.txt
#pip install pyinstaller

REM 清理旧的打包文件
echo 清理旧文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM 使用 spec 文件打包
echo 开始打包...
pyinstaller build.spec

echo.
if exist dist\AIDesk\AIDesk.exe (
    echo 打包成功！
    echo 可执行文件位于: dist\AIDesk\AIDesk.exe
) else (
    echo 打包失败，请检查错误信息
)
pause