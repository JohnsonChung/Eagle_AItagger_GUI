@echo off
chcp 65001 >nul
echo ====================================
echo  Eagle AI Tagger - 打包工具
echo ====================================
echo.

REM 檢查 PyInstaller
python -c "import PyInstaller" 2>nul
if %ERRORLEVEL% neq 0 (
    echo [安裝] 正在安裝 PyInstaller...
    pip install pyinstaller
)

REM 切換到專案根目錄
cd /d "%~dp0.."

echo [打包] 開始打包 EagleTagger...
echo.

pyinstaller build/eagle_tagger.spec --distpath dist --workpath build/temp --clean -y

if %ERRORLEVEL% equ 0 (
    echo.
    echo ====================================
    echo  打包成功！
    echo  輸出目錄: dist\EagleTagger\
    echo ====================================
    echo.
    
    REM 複製需要使用者自行準備的檔案
    if not exist "dist\EagleTagger\config.ini" (
        copy config.ini "dist\EagleTagger\config.ini"
        echo [複製] config.ini
    )
    
    if not exist "dist\EagleTagger\model" (
        mkdir "dist\EagleTagger\model"
        echo [建立] model\ 目錄（請將 ONNX 模型放入此處）
    )
    
    if not exist "dist\EagleTagger\image_list.txt" (
        echo. > "dist\EagleTagger\image_list.txt"
        echo [建立] image_list.txt
    )
    
    echo.
    echo 打包完成！請將 dist\EagleTagger 資料夾分發給使用者。
    echo 注意：使用者仍需自行安裝 CUDA 與 cuDNN。
) else (
    echo.
    echo [錯誤] 打包失敗，請檢查上方錯誤訊息。
)

echo.
pause
