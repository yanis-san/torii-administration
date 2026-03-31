# 🚀 GUIDE: CLONER SUR UN AUTRE PC - Récupération Facile

**Date**: 29 janvier 2026

---

## ⚡ La Bonne Nouvelle

✅ **OUI, c'est TRÈS FACILE !** Voici pourquoi:

1. ✅ Vos **paramètres BD sont dans settings.py** (codés en dur)
2. ✅ Votre **sauvegarde complète** (DB + médias) est dans **OneDrive**
3. ✅ PostgreSQL peut être **sur le même serveur** ou **un nouveau serveur**

---

## 📋 PRÉREQUIS sur le Nouveau PC

```
✅ Git installé
✅ Python 3.13
✅ PostgreSQL 15+ installé ET démarré
✅ Accès à OneDrive (pour récupérer le backup)
```

---

## 🎯 ÉTAPE 1: Cloner le Projet

```powershell
# Allez dans votre dossier de code
cd "C:\Users\[VOTRE_USER]\Documents\codes"

# Cloner le repo
git clone https://github.com/[YOUR_REPO].git school_management

# Entrer dans le dossier
cd school_management
```

**Ce qui s'est clone:**
```
✅ Code source complet
✅ Migrations Django
✅ Templates HTML/CSS/JS
✅ Scripts et configurations
❌ Fichiers médias (media/) - Dans .gitignore
❌ Environnement virtuel (.venv/) - Dans .gitignore
❌ Base de données - Sur PostgreSQL
```

---

## 🎯 ÉTAPE 2: Créer l'Environnement Virtual

```powershell
# Créer le venv
python -m venv .venv

# Activer le venv
.\.venv\Scripts\Activate.ps1

# Installer les dépendances
pip install -r requirements.txt
```

---

## 🎯 ÉTAPE 3: Configurer PostgreSQL

### Option A: Si vous avez le MÊME utilisateur PostgreSQL

```powershell
# Aucune modification needed! Les settings.py utilisent:
# USER: yanis
# PASSWORD: Orochimarusama1
# HOST: 127.0.0.1
# PORT: 5432
# NAME: institut_torii_db

# Vérifier que PostgreSQL fonctionne
psql -U yanis -h 127.0.0.1 -c "\l"
```

### Option B: Si vous avez un AUTRE utilisateur PostgreSQL

Modifier [config/settings.py](config/settings.py):

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'institut_torii_db',
        'USER': 'VOTRE_USER',           # <-- Changer ici
        'PASSWORD': 'VOTRE_PASSWORD',   # <-- Changer ici
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
```

---

## 🎯 ÉTAPE 4: Récupérer votre Sauvegarde

```powershell
# Les backups sont dans OneDrive:
# C:\Users\[VOTRE_USER]\OneDrive\Torii-management\backups\

# Copier le dernier backup:
copy "C:\Users\[VOTRE_USER]\OneDrive\Torii-management\backups\backup_complet_*.tar.gz" "C:\Backups"

# OU télécharger manuellement depuis OneDrive Web
```

---

## 🎯 ÉTAPE 5: RESTAURER la Base de Données + Médias

```powershell
# Activer le venv d'abord
.\.venv\Scripts\Activate.ps1

# Restaurer le backup (force = sans confirmation)
python manage.py restore_data "C:\Backups\backup_complet_db_20260129_093829.tar.gz" --force
```

**Ce qui se restaure:**
```
✅ Base de données PostgreSQL complète (toutes les données)
✅ Tous les fichiers médias (photos, reçus, etc)
✅ Utilisateurs et authentification
✅ Toutes les années académiques
✅ Tous les élèves et leurs données
```

---

## ✅ ÉTAPE 6: Vérifier que Tout Fonctionne

```powershell
# Démarrer le serveur
python manage.py runserver

# Ouvrir dans le navigateur
# http://localhost:8000
```

Vous devriez voir:
- ✅ Toutes les données
- ✅ Tous les utilisateurs
- ✅ Tous les fichiers médias chargés
- ✅ Pas d'erreurs

---

## 🎯 RÉSUMÉ - 5 Commandes

```powershell
# 1. Cloner
git clone https://github.com/[YOUR_REPO].git school_management
cd school_management

# 2. Environnement
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. Modifier settings.py si besoin (utilisateur PostgreSQL différent)
# [EDITEZ settings.py si nécessaire]

# 4. Restaurer (avec votre backup OneDrive)
python manage.py restore_data "C:\Users\[USER]\OneDrive\Torii-management\backups\backup_complet_db_20260129_093829.tar.gz" --force

# 5. Démarrer
python manage.py runserver
```

---

## ⚠️ ATTENTION - Cas Spéciaux

### Si PostgreSQL N'EXISTE PAS sur le nouveau PC

```powershell
# 1. Installer PostgreSQL d'abord
# https://www.postgresql.org/download/windows/

# 2. Créer l'utilisateur et la base:
psql -U postgres
CREATE USER yanis WITH PASSWORD 'Orochimarusama1';
CREATE DATABASE institut_torii_db OWNER yanis;
\q

# 3. Puis faire la restauration (Étape 5)
```

### Si c'est sur un AUTRE SERVEUR PostgreSQL

Modifier settings.py:

```python
DATABASES = {
    'default': {
        'HOST': '192.168.1.100',  # Adresse IP du serveur
        'PORT': '5432',
        # Reste pareil
    }
}
```

### Si vous n'avez PAS accès à OneDrive

Créer un nouveau backup du PC actuel:

```powershell
python manage.py backup_data --dest "D:\USB_externe\backup"

# Puis transférer le fichier .tar.gz sur une clé USB
# Et le restaurer sur le nouveau PC
```

---

## 🔍 VÉRIFICATION - Checklist

Après la restauration, vérifier:

```powershell
# 1. Les données sont là
python manage.py dbshell
SELECT COUNT(*) FROM academics_cohort;  # Doit avoir des cohorts

# 2. Les fichiers médias sont présents
ls media/

# 3. Le serveur démarre sans erreur
python manage.py runserver

# 4. L'interface web fonctionne
# Ouvrir http://localhost:8000 et vérifier les données
```

---

## 🎓 EXEMPLE RÉEL

**Votre situation:**
- PC1: Windows, Python 3.13, PostgreSQL (yanis/Orochimarusama1)
- PC2: Windows, Python 3.13, PostgreSQL (même user et password)
- Backup dans OneDrive: 25.18 MB

**Processus complet:**

```powershell
# === PC2 ===
# 1. Clone
git clone https://github.com/[YOUR_REPO].git school_management
cd school_management

# 2. Env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. PostgreSQL déjà correct (même user/password)
# Aucune modification de settings.py needed!

# 4. Copier le backup
copy "C:\Users\yanis\OneDrive\Torii-management\backups\backup_complet_db_20260129_093829.tar.gz" .

# 5. Restaurer
python manage.py restore_data "backup_complet_db_20260129_093829.tar.gz" --force

# 6. Vérifier
python manage.py runserver

# RÉSULTAT: Toutes les données, tous les fichiers médias, prêt à l'emploi!
```

**Temps total: ~5-10 minutes** (selon la vitesse internet pour OneDrive)

---

## 🚀 TRÈS IMPORTANT

⚠️ **NE PAS OUBLIER:**

```
1. Les identifiants PostgreSQL doivent être les MÊMES
   OU modifier settings.py avec les nouveaux

2. PostgreSQL doit être DÉMARRÉ sur le nouveau PC

3. OneDrive doit être synchronisé (ou télécharger manuellement)

4. Faire une restauration de TEST avant de déployer en prod
```

---

## ✅ CONCLUSION

✅ **OUI, c'est TRÈS FACILE!**

Grâce à:
- ✅ Vos identifiants codés en dur dans settings.py
- ✅ Votre sauvegarde complète (DB + médias) dans OneDrive
- ✅ Les migrations Django automatiques

**Vous pouvez cloner et restaurer en ~10 minutes!**

Aucune manipulation compliquée, aucune perte de données.
