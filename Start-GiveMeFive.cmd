@echo off
chcp 65001 >nul
setlocal
set PYTHONUTF8=1
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 (
    echo 请先安装 Python 3.11 或更新版本，并勾选加入 PATH。
    pause
    exit /b 1
  )
)
.venv\Scripts\python.exe -c "import fastapi,uvicorn,pdfplumber,pypdf,sympy,httpx,multipart" >nul 2>&1
if errorlevel 1 (
  echo 首次运行正在安装题库服务依赖，请保持联网。
  .venv\Scripts\python.exe -m pip install -r as-v3-reference\requirements.txt
  if errorlevel 1 (
    echo 依赖安装未完成。请保留窗口中的错误信息，检查网络后重新运行。
    pause
    exit /b 1
  )
)
.venv\Scripts\python.exe scripts\run-v4.py --open %*
if errorlevel 1 pause
