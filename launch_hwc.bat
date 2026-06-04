@echo off
:: ============================================================
::  HWC GUI ランチャー
::  Miniforge (conda) 環境を初期化してから hwc_gui.py を起動します
:: ============================================================

:: --- Miniforge のインストール場所を探す（よくある場所を順番に確認）---
set CONDA_BASE=
for %%P in (
    "%USERPROFILE%\miniforge3"
    "%USERPROFILE%\Miniforge3"
    "%LOCALAPPDATA%\miniforge3"
    "%LOCALAPPDATA%\Miniforge3"
    "C:\miniforge3"
    "C:\Miniforge3"
    "C:\ProgramData\miniforge3"
    "C:\ProgramData\Miniforge3"
) do (
    if exist "%%~P\Scripts\activate.bat" (
        set CONDA_BASE=%%~P
        goto :found
    )
)

echo [ERROR] Miniforge が見つかりませんでした。
echo         インストール先を launch_hwc.bat の CONDA_BASE に直接指定してください。
pause
exit /b 1

:found
echo Miniforge を検出しました: %CONDA_BASE%

:: --- conda を初期化 ---
call "%CONDA_BASE%\Scripts\activate.bat" "%CONDA_BASE%"

:: --- 使用する conda 環境を指定（base のままでよければそのまま）---
::  別の環境を使う場合は下の行のコメントを外して環境名を書き換えてください
:: call conda activate myenv

:: --- スクリプトのディレクトリへ移動して実行 ---
cd /d "Z:\codes\py"
python -m Chromagnon.hwc_gui

:: エラーが出た場合にウィンドウが閉じないように pause
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] 終了コード: %ERRORLEVEL%
    pause
)
