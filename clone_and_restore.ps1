#!/usr/bin/env powershell
# Script automatise pour cloner et restaurer sur un autre PC
# Usage: .\clone_and_restore.ps1

Write-Host "================================" -ForegroundColor Green
Write-Host "Clone et Restauration Facile" -ForegroundColor Green
Write-Host "================================`n" -ForegroundColor Green

# Verifier les prerequis
Write-Host "[1/5] Verification des prerequis..." -ForegroundColor Cyan

$checks = @{
    "Python" = "python --version"
    "Git" = "git --version"
    "PostgreSQL" = "psql --version"
}

foreach ($tool in $checks.Keys) {
    try {
        $result = Invoke-Expression $checks[$tool] 2>&1
        Write-Host "  OK $tool`: $($result[0])" -ForegroundColor Green
    } catch {
        Write-Host "  ERREUR: $tool non trouve!" -ForegroundColor Red
        Write-Host "  Installez $tool et relancez le script" -ForegroundColor Yellow
        exit 1
    }
}

# Demander les parametres
Write-Host "`n[2/5] Configuration..." -ForegroundColor Cyan
$repo_url = Read-Host "  URL du repo Git (ex: https://github.com/user/repo.git)"
$postgres_user = Read-Host "  Utilisateur PostgreSQL (defaut: yanis)" 
if ([string]::IsNullOrEmpty($postgres_user)) { $postgres_user = "yanis" }
$postgres_host = Read-Host "  Serveur PostgreSQL (defaut: 127.0.0.1)"
if ([string]::IsNullOrEmpty($postgres_host)) { $postgres_host = "127.0.0.1" }
$backup_path = Read-Host "  Chemin du backup .tar.gz"

if (-not (Test-Path $backup_path)) {
    Write-Host "  ERREUR: Fichier backup non trouve!" -ForegroundColor Red
    exit 1
}

$project_dir = Read-Host "  Dossier destination (defaut: school_management)"
if ([string]::IsNullOrEmpty($project_dir)) { $project_dir = "school_management" }

# Cloner
Write-Host "`n[3/5] Clone du projet..." -ForegroundColor Cyan
try {
    git clone $repo_url $project_dir
    cd $project_dir
    Write-Host "  OK Projet clone" -ForegroundColor Green
} catch {
    Write-Host "  ERREUR: Clone echoue!" -ForegroundColor Red
    exit 1
}

# Creer environnement
Write-Host "`n[4/5] Configuration Python..." -ForegroundColor Cyan
try {
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt --quiet
    Write-Host "  OK Environnement cree" -ForegroundColor Green
} catch {
    Write-Host "  ERREUR: Configuration echouee!" -ForegroundColor Red
    exit 1
}

# Modifier settings si besoin
Write-Host "`n[5/5] Restauration de la base de donnees..." -ForegroundColor Cyan
if ($postgres_host -ne "127.0.0.1" -or $postgres_user -ne "yanis") {
    Write-Host "  Modification de settings.py..." -ForegroundColor Yellow
    $settings_file = "config/settings.py"
    $content = Get-Content $settings_file
    
    # Remplacer les parametres
    $content = $content -replace "'HOST': '[^']*'", "'HOST': '$postgres_host'"
    $content = $content -replace "'USER': '[^']*'", "'USER': '$postgres_user'"
    
    Set-Content $settings_file $content
    Write-Host "  OK settings.py mis a jour" -ForegroundColor Green
}

# Restaurer
try {
    python manage.py restore_data $backup_path --force
    Write-Host "  OK Donnees restaurees" -ForegroundColor Green
} catch {
    Write-Host "  ERREUR: Restauration echouee!" -ForegroundColor Red
    exit 1
}

# Verifier
Write-Host "`n[VERIF] Tests..." -ForegroundColor Cyan
try {
    $result = python manage.py shell -c "from django.db import connection; connection.ensure_connection()" 2>&1
    Write-Host "  OK Connexion base de donnees OK" -ForegroundColor Green
    
    if (Test-Path "media") {
        $media_count = (Get-ChildItem media -Recurse -File | Measure-Object).Count
        Write-Host "  OK Fichiers medias: $media_count fichiers" -ForegroundColor Green
    }
} catch {
    Write-Host "  ATTENTION: Impossible de verifier" -ForegroundColor Yellow
}

# Succes
Write-Host "`n================================" -ForegroundColor Green
Write-Host "OK RESTAURATION REUSSIE!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host "`nPour demarrer:" -ForegroundColor Cyan
Write-Host "  python manage.py runserver" -ForegroundColor Yellow
Write-Host "  http://localhost:8000" -ForegroundColor Yellow
