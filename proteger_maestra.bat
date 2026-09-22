@echo off
REM ============================================================================
REM  Deja la base MAESTRA accesible solo para la cuenta que corre el scraping y
REM  la suite (la cuenta que ejecuta este script), Administradores y SYSTEM.
REM  El resto de usuarios no puede abrirla; ellos usan db\suite_data_replica.db.
REM
REM  Ejecutar UNA VEZ, como administrador, con la cuenta que corre la tarea
REM  programada (run_scraper.bat) y la suite (run_suite.bat).
REM ============================================================================
cd /d "%~dp0"

if not exist "db\suite_data_maestra.db" (
    echo No existe db\suite_data_maestra.db
    exit /b 1
)

REM *S-1-5-32-544 = Administradores, *S-1-5-18 = SYSTEM (funciona en Windows en espanol o ingles)
icacls "db\suite_data_maestra.db" /inheritance:r /grant:r "%USERDOMAIN%\%USERNAME%":F "*S-1-5-32-544":F "*S-1-5-18":F
icacls "db\backups" /inheritance:r /grant:r "%USERDOMAIN%\%USERNAME%":(OI)(CI)F "*S-1-5-32-544":(OI)(CI)F "*S-1-5-18":(OI)(CI)F

echo.
echo Permisos actuales de la maestra:
icacls "db\suite_data_maestra.db"
pause
