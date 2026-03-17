@echo off
echo.
echo  -------------------------------------------------------
echo   Markdown Editor - Full Build
echo  -------------------------------------------------------
echo.

call "%~dp0build_frontend.bat"
if errorlevel 1 goto :fail

echo.
call "%~dp0build_backend.bat"
if errorlevel 1 goto :fail

echo.
call "%~dp0build_electron.bat"
if errorlevel 1 goto :fail

echo.
echo  -------------------------------------------------------
echo   BUILD SUCCESS
echo   Output: dist_electron\
echo  -------------------------------------------------------
pause
exit /b 0

:fail
echo.
echo  -------------------------------------------------------
echo   BUILD FAILED - See errors above
echo  -------------------------------------------------------
pause
exit /b 1
