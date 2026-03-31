# ⚡ RÉFÉRENCE RAPIDE - Backup & Clone

## SAUVEGARDE

```bash
# Créer un backup complet (DB + médias)
python manage.py backup_data

# Créer vers destination personnalisée
python manage.py backup_data --dest "C:\Backups"

# Lister les backups
python manage.py backup_data --list

# Vérifier l'intégrité (comparer hash)
python manage.py backup_data --verify
```

**Localisation par défaut:** `C:\Users\[User]\OneDrive\Torii-management\backups\`

**Format:** `backup_complet_db_YYYYMMDD_HHMMSS.tar.gz` + `.json` (métadonnées)

---

## RESTAURATION

```bash
# Depuis OneDrive (le plus récent)
python manage.py restore_data backup_complet_db_20260129_093829.tar.gz --force

# Depuis un chemin personnalisé
python manage.py restore_data "C:\Backups\backup.tar.gz" --force

# Avec confirmation (demande yes/no)
python manage.py restore_data backup.tar.gz
```

**Restaure:** BD complète + tous les fichiers médias + utilisateurs + données

---

## CLONER SUR AUTRE PC

### Option 1: Script Auto (Recommandé)
```powershell
# Lancer le wizard
.\clone_and_restore.ps1

# Répondez aux questions:
# - URL du repo
# - User PostgreSQL
# - Chemin backup
```

### Option 2: Commande Unique
```cmd
clone_and_restore.bat https://github.com/user/repo.git "C:\Backups\backup.tar.gz"
```

### Option 3: Étapes Manuelles
```bash
git clone https://github.com/user/repo.git school_management
cd school_management
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py restore_data "C:\Backups\backup.tar.gz" --force
python manage.py runserver
```

---

## VÉRIFIER QUE ÇA MARCHE

```bash
# Tester la connexion BD
python manage.py dbshell
\q

# Vérifier les fichiers médias
ls media/

# Compter les données
python manage.py shell
>>> from academics.models import Cohort
>>> Cohort.objects.count()

# Lancer le serveur
python manage.py runserver
# http://localhost:8000
```

---

## PRÉREQUIS AUTRE PC

```
✅ Python 3.13
✅ Git
✅ PostgreSQL (démarré)
✅ Même user PostgreSQL OU modification settings.py
✅ Accès OneDrive (ou copie du backup)
```

---

## MODIFICATION SETTINGS (Si User Différent)

Éditer `config/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'institut_torii_db',
        'USER': 'NOUVEAU_USER',       # Changer ici
        'PASSWORD': 'NOUVEAU_PASSWORD', # Changer ici
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}
```

---

## CAS SPÉCIAUX

### PostgreSQL pas encore créé
```bash
psql -U postgres
CREATE USER yanis WITH PASSWORD 'Orochimarusama1';
CREATE DATABASE institut_torii_db OWNER yanis;
\q
```

### Serveur PostgreSQL externe
```python
# Dans settings.py:
'HOST': '192.168.1.100',  # Adresse IP du serveur
```

### Pas d'accès à OneDrive
```bash
# Créer nouveau backup d'abord
python manage.py backup_data --dest "D:\USB"

# Puis transférer sur clé USB
```

---

## FICHIERS IMPORTANTS

| Fichier | Rôle |
|---------|------|
| `backup_complet_db_*.tar.gz` | Archive complète (DB + médias) |
| `backup_complet_db_*.json` | Métadonnées + hash |
| `config/settings.py` | Config BD (user/password) |
| `media/` | Fichiers médias (restaurés) |
| `.venv/` | Environnement Python (créé) |

---

## TEMPS ESTIMÉ

| Action | Temps |
|--------|-------|
| Créer un backup | 30-60 sec |
| Cloner nouveau PC | 5-10 min |
| Restaurer | 30-60 sec |
| Vérifier | 1-2 min |
| **TOTAL** | **~7-15 min** |

---

## PIÈGES À ÉVITER

```
❌ Oublier .venv\Scripts\Activate.ps1
❌ PostgreSQL pas démarré
❌ User PostgreSQL différent (pas modifié settings.py)
❌ Backup pas trouvé (chemin incorrect)
❌ Pas vérifier l'intégrité avant restauration
```

---

## DOCUMENTS COMPLETS

| Document | Objectif |
|----------|----------|
| [AUDIT_SAUVEGARDE_FINAL.md](AUDIT_SAUVEGARDE_FINAL.md) | Rapport détaillé + tests |
| [GUIDE_CLONE_AUTRE_PC.md](GUIDE_CLONE_AUTRE_PC.md) | Instructions complètes |
| [CLONE_SUMMARY.md](CLONE_SUMMARY.md) | Vue d'ensemble |
| [BACKUP_INDEX.md](BACKUP_INDEX.md) | Index et vue globale |

---

## RÉSUMÉ

✅ **Sauvegarde:** Automatique, complète (DB + médias), vérifiée  
✅ **Restauration:** Simple, rapide, sûre  
✅ **Clonage:** 3 options (auto, cmd, manuel)  
✅ **Temps:** 5-15 minutes pour tout  

**C'est TRÈS FACILE!** 🚀
