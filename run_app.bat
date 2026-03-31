@echo off
REM Script de démarrage de l'application Django
REM Ce fichier doit être dans le dossier racine du projet

cd /d "%~dp0"
echo.
echo ================================================
echo    Gestionnaire d'Ecole - Demarrage
echo ================================================
echo.

REM Vérifier que le venv existe
if not exist ".venv\Scripts\python.exe" (
    echo Erreur: Le virtual environment n'a pas ete trouve
    echo.
    pause
    exit /b 1
)

echo Demarrage du serveur...
start "Serveur Django - Gestionnaire d'Ecole" .venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000

REM Attendre plus longtemps que le serveur démarre complètement
echo Attente du demarrage du serveur (5 secondes)...
timeout /t 5 /nobreak

REM Ouvrir le navigateur
echo Ouverture de l'application web...
start http://127.0.0.1:8000

echo.
echo Application prete!
echo URL: http://127.0.0.1:8000
echo.
