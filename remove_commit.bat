@echo off
echo 警告：此操作将删除所有Git历史记录！
echo 按任意键继续，或关闭窗口取消...
pause

echo.
echo 正在删除历史记录...

git checkout --orphan latest_branch
git add -A
git commit -m "Initial commit"
git branch -D main
git branch -m main
git push -f origin main

echo.
echo 完成！所有历史记录已删除。
pause