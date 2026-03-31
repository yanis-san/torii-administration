@echo off
REM Script simple pour cloner et restaurer
REM Utilisation: clone_and_restore.bat <repo_url> <backup_file>

setlocal enabledelayedexpansion

echo ================================
echo Clone et Restauration Facile
echo ================================
echo.

REM Verifier les parametres
if "%~1"=="" (
    echo ERREUR: URL du repo manquante!
    echo Usage: clone_and_restore.bat ^<repo_url^> ^<backup_file^>
    echo Exemple: clone_and_restore.bat https://github.com/user/repo.git backup_complet_db_20260129_093829.tar.gz
    exit /b 1
)

if "%~2"=="" (
    echo ERREUR: Chemin du backup manquant!
    echo Usage: clone_and_restore.bat ^<repo_url^> ^<backup_file^>
    exit /b 1
)

if not exist "%~2" (
    echo ERREUR: Fichier backup non trouve: %~2
    exit /b 1
)

set REPO_URL=%~1
set BACKUP_FILE=%~2
set PROJECT_DIR=school_management

echo [1/5] Verification des prerequis...
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERREUR: Python non trouve!
    exit /b 1
)
echo  OK Python
git --version >nul 2>&1
if errorlevel 1 (
    echo  ERREUR: Git non trouve!
    exit /b 1
)
echo  OK Git

echo.
echo [2/5] Clone du projet...
git clone %REPO_URL% %PROJECT_DIR%
if errorlevel 1 (
    echo  ERREUR: Clone echoue!
    exit /b 1
)
cd %PROJECT_DIR%
echo  OK Projet clone

echo.
echo [3/5] Configuration Python...
python -m venv .venv
call .venv\Scripts\activate.bat
pip install -r requirements.txt -q
if errorlevel 1 (
    echo  ERREUR: Installation dependances echouee!
    exit /b 1
)
echo  OK Environnement cree

echo.
echo [4/5] Restauration de la base de donnees...
python manage.py restore_data "%BACKUP_FILE%" --force
if errorlevel 1 (
    echo  ERREUR: Restauration echouee!
    exit /b 1
)
echo  OK Donnees restaurees

echo.
echo [VERIF] Tests...
python manage.py shell -c "from django.db import connection; connection.ensure_connection()" >nul 2>&1
if errorlevel 1 (
    echo  ATTENTION: Impossible de verifier la connexion DB
) else (
    echo  OK Base de donnees OK
)

if exist "media" (
    echo  OK Dossier medias present
)

echo.
echo ================================
echo OK RESTAURATION REUSSIE!
echo ================================
echo.
echo Pour demarrer:
echo   python manage.py runserver
echo   http://localhost:8000
echo.

pause
