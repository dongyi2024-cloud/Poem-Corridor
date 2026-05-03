@echo off
echo ========================================
echo   启动诗廊 Web 服务器
echo ========================================
echo.

cd /d "%~dp0"

echo 正在启动 HTTP 服务器...
echo 浏览器访问: http://localhost:8080
echo 按 Ctrl+C 停止服务器
echo.

python -m http.server 8080