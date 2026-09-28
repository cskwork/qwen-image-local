@echo off
cd /d "%~dp0"
python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if %errorlevel% equ 0 goto run_python
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if %errorlevel% equ 0 goto run_py
echo Python 3.11 or newer was not found. Install Python and enable Add to PATH.
pause
exit /b 1
:run_python
python skills\qwen-image-local\scripts\qwen_local.py serve --open %*
goto finished
:run_py
py -3 skills\qwen-image-local\scripts\qwen_local.py serve --open %*
:finished
set result=%errorlevel%
if not %result% equ 0 pause
exit /b %result%
