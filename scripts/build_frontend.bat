@echo off
echo.
echo  -------------------------------------------------------
echo   [1/3] Building Frontend (Vue.js)
echo  -------------------------------------------------------
cd /d "%~dp0..\frontend"
call npm install
if errorlevel 1 (
    echo ERROR: npm install failed
    exit /b 1
)
call npm run build
if errorlevel 1 (
    echo ERROR: npm build failed
    exit /b 1
)
echo.
echo Frontend build complete  -^> frontend\dist\
