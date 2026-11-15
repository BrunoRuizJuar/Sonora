@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1
if not errorlevel 1 (
    py -3 "%~dp0serve.py" --open %*
    goto finished
)
python --version >nul 2>&1
if not errorlevel 1 (
    python "%~dp0serve.py" --open %*
    goto finished
)
echo No se encontro Python 3.
echo Instala Python desde https://www.python.org/downloads/windows/
echo Despues cierra esta ventana y vuelve a abrir INICIAR_LOCAL.cmd.
pause
exit /b 1
:finished
if errorlevel 1 pause
endlocal
