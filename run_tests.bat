@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

REM Script para ejecutar todos los tests de METIS en Windows
REM Ejecuta: unitarios, lint (ruff + black), integracion y e2e
REM Los logs se guardan en la carpeta raiz del proyecto

echo.
echo  ============================================
echo   TESTS DE METIS
echo  ============================================
echo.

REM Verificar directorio correcto
if not exist "pyproject.toml" (
    echo  [X] Ejecutar desde el directorio raiz de METIS
    exit /b 1
)

REM Fecha para referencia
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "dt=%%I"
set "FECHA=%dt:~0,4%-%dt:~4,2%-%dt:~6,2% %dt:~8,2%:%dt:~10,2%:%dt:~12,2%"
echo  Fecha: %FECHA%
echo.

set "PASS=0"
set "FAIL=0"

REM ============================================================================
REM 1. TESTS UNITARIOS
REM ============================================================================
echo  --------------------------------------------
echo   1/5 - Tests Unitarios
echo  --------------------------------------------
(
    echo ==========================================
    echo TESTS UNITARIOS — %FECHA%
    echo ==========================================
    pytest tests/unit/ -v
) > UnitTestLog.txt 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Tests unitarios pasaron
    set /a PASS+=1
) else (
    echo   [FAIL] Tests unitarios fallaron
    set /a FAIL+=1
)
echo.

REM ============================================================================
REM 2. RUFF LINTER
REM ============================================================================
echo  --------------------------------------------
echo   2/5 - Ruff Linter (check --fix)
echo  --------------------------------------------
(
    echo ==========================================
    echo RUFF CHECK — %FECHA%
    echo ==========================================
    ruff check --fix
) > RuffLog.txt 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Ruff: sin errores
    set /a PASS+=1
) else (
    echo   [!] Ruff: problemas encontrados
    set /a FAIL+=1
)
echo.

REM ============================================================================
REM 3. BLACK FORMATTER
REM ============================================================================
echo  --------------------------------------------
echo   3/5 - Black Formatter
echo  --------------------------------------------
(
    echo ==========================================
    echo BLACK FORMAT — %FECHA%
    echo ==========================================
    black .
) > BlackLog.txt 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Black: formato aplicado
    set /a PASS+=1
) else (
    echo   [!] Black: error
    set /a FAIL+=1
)
echo.

REM ============================================================================
REM 4. TESTS DE INTEGRACION
REM ============================================================================
echo  --------------------------------------------
echo   4/5 - Tests de Integracion
echo  --------------------------------------------
(
    echo ==========================================
    echo TESTS DE INTEGRACION — %FECHA%
    echo ==========================================
    python -m pytest tests/integration -q
) > IntegrationTestLog.txt 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Tests de integracion pasaron
    set /a PASS+=1
) else (
    echo   [FAIL] Tests de integracion fallaron
    set /a FAIL+=1
)
echo.

REM ============================================================================
REM 5. TESTS E2E
REM ============================================================================
echo  --------------------------------------------
echo   5/5 - Tests End-to-End
echo  --------------------------------------------
(
    echo ==========================================
    echo TESTS E2E — %FECHA%
    echo ==========================================
    pytest tests/e2e/ -v
) > E2ETestLog.txt 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Tests E2E pasaron
    set /a PASS+=1
) else (
    echo   [FAIL] Tests E2E fallaron
    set /a FAIL+=1
)
echo.

REM ============================================================================
REM RESUMEN
REM ============================================================================
echo  ============================================
echo   RESUMEN
echo  ============================================
echo   Pasaron:  %PASS%/5
echo   Fallaron: %FAIL%/5
echo.
echo  Logs guardados:
echo    UnitTestLog.txt
echo    RuffLog.txt
echo    BlackLog.txt
echo    IntegrationTestLog.txt
echo    E2ETestLog.txt
echo.

if %FAIL% gtr 0 (
    echo  [!] %FAIL% conjunto(s) con problemas. Revisar logs.
    exit /b 1
) else (
    echo  [OK] Todos los tests pasaron!
    exit /b 0
)