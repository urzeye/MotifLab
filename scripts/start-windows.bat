@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

:: MotifLab AI图文生成器 - Windows 启动脚本

title MotifLab AI图文生成器

cd /d "%~dp0\.."

cls
echo.
echo ╔═══════════════════════════════════════════════╗
echo ║     🪟 MotifLab AI图文生成器 - Windows 版     ║
echo ╚═══════════════════════════════════════════════╝
echo.

:: ========== 环境检查 ==========
echo [INFO] 检查环境依赖...
echo.

:: Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python 未安装！
    echo         请从 https://www.python.org/downloads/ 下载安装
    echo         安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo   [OK] %PYTHON_VER%

:: uv
where uv >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%i in ('uv --version 2^>^&1') do set UV_VER=%%i
    echo   [OK] uv !UV_VER!
    set USE_UV=1
) else (
    echo   [!] uv 未安装 ^(推荐: pip install uv^)
    set USE_UV=0
)

:: pnpm / npm
where pnpm >nul 2>&1
if %ERRORLEVEL% equ 0 (
    for /f "tokens=*" %%i in ('pnpm --version') do set PNPM_VER=%%i
    echo   [OK] pnpm !PNPM_VER!
    set PKG_MANAGER=pnpm
) else (
    where npm >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        for /f "tokens=*" %%i in ('npm --version') do set NPM_VER=%%i
        echo   [!] npm !NPM_VER! ^(建议: npm i -g pnpm^)
        set PKG_MANAGER=npm
    ) else (
        echo   [ERROR] Node.js 未安装！
        echo           请从 https://nodejs.org/ 下载安装
        pause
        exit /b 1
    )
)

echo.

:: ========== 安装依赖 ==========
echo [INFO] 检查项目依赖...

:: 后端依赖
if %USE_UV% equ 1 (
    echo   → 后端依赖 ^(uv^)
    uv sync
) else (
    echo   → 后端依赖 ^(pip^)
    pip install -e . -q
)
echo   [OK] 后端依赖完成

:: 前端依赖
echo   → 前端依赖
cd frontend
if not exist "node_modules\" (
    echo     正在安装前端依赖，请稍候...
    %PKG_MANAGER% install
)
echo   [OK] 前端依赖完成
cd ..

echo.

:: ========== 启动服务 ==========
echo [INFO] 启动服务...
echo.

:: 启动后端 (新窗口，蓝色背景)
if %USE_UV% equ 1 (
    start "MotifLab-后端-12398" cmd /k "color 1F && title MotifLab 后端服务 [12398] && uv run python backend/app.py"
) else (
    start "MotifLab-后端-12398" cmd /k "color 1F && title MotifLab 后端服务 [12398] && python backend/app.py"
)

:: 等待后端启动
echo   等待后端启动...
timeout /t 3 /nobreak >nul

:: 启动前端 (新窗口，绿色背景)
cd frontend
start "MotifLab-前端-5173" cmd /k "color 2F && title MotifLab 前端服务 [5173] && %PKG_MANAGER% run dev"
cd ..

:: 等待前端启动
timeout /t 3 /nobreak >nul

echo.
echo ╔═══════════════════════════════════════════════╗
echo ║         🎉 服务启动成功！                     ║
echo ╠═══════════════════════════════════════════════╣
echo ║  🌐 前端: http://localhost:5173              ║
echo ║  🔧 后端: http://localhost:12398             ║
echo ╠═══════════════════════════════════════════════╣
echo ║  已打开两个服务窗口，关闭它们即可停止服务    ║
echo ╚═══════════════════════════════════════════════╝
echo.

:: 自动打开浏览器
start http://localhost:5173

echo 按任意键关闭此窗口（服务会继续运行）...
pause >nul
