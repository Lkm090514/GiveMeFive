@echo off
chcp 65001 >nul
rem Compatibility entry: always start Fusion and its real Assessment API.
if not exist "%~dp0..\Start-GiveMeFive.cmd" (
  echo 请使用完整项目根目录的 Start-GiveMeFive.cmd；仅有静态前端无法使用题库。
  exit /b 1
)
call "%~dp0..\Start-GiveMeFive.cmd" %*
