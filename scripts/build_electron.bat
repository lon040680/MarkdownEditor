@echo off
echo.
echo  -------------------------------------------------------
echo   [3/3] Building Electron Installer
echo  -------------------------------------------------------
cd /d "%~dp0..\electron"
call npm install
if errorlevel 1 (
    echo ERROR: npm install failed
    exit /b 1
)
call npm run build
if errorlevel 1 (
    echo ERROR: electron-builder failed
    exit /b 1
)
echo.
echo Electron build complete  -^> dist_electron\
