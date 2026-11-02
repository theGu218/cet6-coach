@echo off
cd /d %~dp0
python -m PyInstaller --noconfirm --clean CET6Coach_portable.spec
echo Build complete: dist\CET6Coach-portable\CET6Coach.exe
pause
