@echo off
echo.
echo  -------------------------------------------------------
echo   [2/3] Building Backend (PyInstaller)
echo  -------------------------------------------------------
cd /d "%~dp0..\backend"

REM Resolve Python command (python first, then py -3)
set "PYTHON_CMD=python"
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
  set "PYTHON_CMD=py -3"
  %PYTHON_CMD% --version >nul 2>&1
)
if errorlevel 1 (
  echo ERROR: Python not found. Please install Python 3.10+ and add it to PATH.
  exit /b 1
)

REM Install Python deps
%PYTHON_CMD% -m pip install -r requirements.txt
%PYTHON_CMD% -m pip install pyinstaller
if errorlevel 1 (
    echo ERROR: pip install failed
    exit /b 1
)

REM Copy frontend dist -> backend\static
if exist static rmdir /s /q static
xcopy /s /e /i /q "..\frontend\dist" "static"

REM PyInstaller (--onedir for faster startup)
%PYTHON_CMD% -m PyInstaller --noconfirm --clean ^
  --name server ^
  --distpath dist ^
  --add-data "static;static" ^
  --add-data "app\routes\assets\fonts\NotoSansTC-Regular.ttf;assets\fonts" ^
  --hidden-import uvicorn.logging ^
  --hidden-import uvicorn.loops ^
  --hidden-import uvicorn.loops.auto ^
  --hidden-import uvicorn.protocols ^
  --hidden-import uvicorn.protocols.http ^
  --hidden-import uvicorn.protocols.http.auto ^
  --hidden-import uvicorn.protocols.http.h11_impl ^
  --hidden-import uvicorn.protocols.http.httptools_impl ^
  --hidden-import uvicorn.protocols.websockets ^
  --hidden-import uvicorn.protocols.websockets.auto ^
  --hidden-import uvicorn.protocols.websockets.wsproto_impl ^
  --hidden-import uvicorn.lifespan ^
  --hidden-import uvicorn.lifespan.on ^
  --hidden-import uvicorn.lifespan.off ^
  --hidden-import markdown ^
  --hidden-import markdown.extensions ^
  --hidden-import markdown.extensions.toc ^
  --hidden-import markdown.extensions.fenced_code ^
  --hidden-import markdown.extensions.tables ^
  --hidden-import fpdf ^
  --hidden-import fpdf.enums ^
  --hidden-import fpdf.html ^
  --collect-all fpdf ^
  server.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    exit /b 1
)
echo.
echo Backend build complete  -^> backend\dist\server\
