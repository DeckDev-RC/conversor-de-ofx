@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   OFX TOP - Build Completo (One-Shot)
echo ============================================
echo.

REM Step 1: Clean previous builds
echo [1/4] Limpando builds anteriores...
if exist backend_dist rmdir /s /q backend_dist
if exist frontend\release rmdir /s /q frontend\release
if exist backend\dist rmdir /s /q backend\dist
if exist backend\build rmdir /s /q backend\build
echo       OK
echo.

REM Step 2: Build Python backend with PyInstaller
echo [2/4] Compilando backend Python com PyInstaller...
cd backend
python -m PyInstaller --clean --noconfirm backend_server.spec
if %errorlevel% neq 0 (
    echo.
    echo ERRO: PyInstaller falhou!
    exit /b 1
)
cd ..
echo       OK
echo.

REM Step 3: Copy PyInstaller output to expected location
echo [3/4] Copiando distribuicao do backend...
xcopy /E /I /Y /Q backend\dist\backend_server backend_dist\backend_server >nul
if %errorlevel% neq 0 (
    echo.
    echo ERRO: Falha ao copiar backend_dist!
    exit /b 1
)
echo       OK
echo.

REM Step 4: Build Electron app and create installer
echo [4/4] Compilando Electron e criando instalador...
cd frontend
call npm run dist
if %errorlevel% neq 0 (
    echo.
    echo ERRO: Build do Electron falhou!
    exit /b 1
)
cd ..
echo       OK
echo.

echo ============================================
echo   Build concluido com sucesso!
echo   Instalador: frontend\release\
echo ============================================
dir /b frontend\release\*.exe 2>nul
