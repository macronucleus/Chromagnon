@echo off

:: Miniforge install path - change this if not found automatically
set CONDA_BASE=%USERPROFILE%\miniforge3
if not exist "%CONDA_BASE%\Scripts\activate.bat" set CONDA_BASE=%USERPROFILE%\Miniforge3
if not exist "%CONDA_BASE%\Scripts\activate.bat" set CONDA_BASE=C:\miniforge3
if not exist "%CONDA_BASE%\Scripts\activate.bat" set CONDA_BASE=C:\Miniforge3
if not exist "%CONDA_BASE%\Scripts\activate.bat" set CONDA_BASE=C:\ProgramData\miniforge3
if not exist "%CONDA_BASE%\Scripts\activate.bat" set CONDA_BASE=C:\ProgramData\Miniforge3

if not exist "%CONDA_BASE%\Scripts\activate.bat" (
    echo ERROR: Miniforge not found.
    echo Please set CONDA_BASE manually in this bat file.
    pause
    exit /b 1
)

call "%CONDA_BASE%\Scripts\activate.bat" "%CONDA_BASE%"

cd /d "Z:\codes\py"
python -m Chromagnon.hwc_gui

if %ERRORLEVEL% neq 0 (
    echo ERROR: exit code %ERRORLEVEL%
    pause
)
