# 🚀 ACCÈS RAPIDE - Sauvegarde & Clone

**Mise à jour: 29 Janvier 2026**

---

## ✅ VOTRE QUESTION

> "Si je clone avec git sur autre PC et que j'ai le même user et postgresql je peux tout récupérer facilement?"

### 🎯 RÉPONSE DIRECTE: **OUI! C'est TRÈS FACILE!**

Voir: [REPONSE_CLONE_FACILE.md](REPONSE_CLONE_FACILE.md) pour la réponse complète (30 sec de lecture)

---

## ⚡ 3 COMMANDES - C'EST TOUT!

### Sur le Nouveau PC

```bash
# 1. Clone
git clone https://github.com/[YOUR_REPO].git school_management
cd school_management

# 2. Environnement
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 3. RESTAURER (une seule commande!)
python manage.py restore_data "backup_complet_db_20260129_093829.tar.gz" --force

# 4. Vérifier
python manage.py runserver
# http://localhost:8000 → Tout est là! ✅
```

**Temps: ~5 minutes**

---

## 📚 DOCUMENTS PAR CAS

### Je dois cloner sur autre PC
→ [REPONSE_CLONE_FACILE.md](REPONSE_CLONE_FACILE.md) (5 min lecture)

### Je veux juste les commandes
→ [QUICK_REF_BACKUP.md](QUICK_REF_BACKUP.md) (2 min lecture)

### Je veux comprendre
→ [CLONE_SUMMARY.md](CLONE_SUMMARY.md) (10 min lecture)

### Je veux instructions détaillées
→ [GUIDE_CLONE_AUTRE_PC.md](GUIDE_CLONE_AUTRE_PC.md) (20 min lecture)

### Je veux savoir ce qui a changé
→ [AUDIT_SAUVEGARDE_FINAL.md](AUDIT_SAUVEGARDE_FINAL.md) (30 min lecture)

### Je veux tout comprendre
→ [DOCUMENTS_INDEX.md](DOCUMENTS_INDEX.md) (index complet)

---

## 🛠️ SCRIPTS AUTOMATISÉS

### Option 1: PowerShell (RECOMMANDÉ)
```powershell
.\clone_and_restore.ps1
# Wizard interactif qui gère tout
```

### Option 2: Batch (Très simple)
```cmd
clone_and_restore.bat https://github.com/user/repo.git "C:\Backups\backup.tar.gz"
```

---

## 📋 PRÉREQUIS (5 min)

```
✅ Python 3.13
✅ Git
✅ PostgreSQL (MÊME USER: yanis/Orochimarusama1)
```

**Si user différent:** Modifier 2 lignes dans `config/settings.py`

---

## ✅ APRÈS RESTAURATION

```bash
# Vérifier que tout marche
python manage.py runserver

# http://localhost:8000
# Vous devez voir:
# ✅ Interface web
# ✅ Tous les utilisateurs
# ✅ Toutes les données
# ✅ Tous les fichiers médias
```

---

## 🎁 BONUS: CRÉER UN BACKUP

```bash
python manage.py backup_data
```

Fichier généré: `backup_complet_db_20260129_093829.tar.gz` dans OneDrive

---

## ❓ QUESTIONS COURANTS

### Q: Et si j'ai pas le même user PostgreSQL?
**A:** Modifier 2 lignes dans `config/settings.py` avant de restaurer

### Q: Et si PostgreSQL n'existe pas?
**A:** Installer PostgreSQL d'abord, puis faire restore

### Q: Combien de temps pour cloner?
**A:** ~5-10 minutes (selon la vitesse internet)

### Q: Y a-t-il un risque de perte de données?
**A:** NON! Backup complet = zéro risque

---

## 🎯 RÉSUMÉ

✅ **C'est TRÈS FACILE!**
- ✅ Code dans Git (clone facile)
- ✅ Backup complet dans OneDrive (DB + médias)
- ✅ Une seule commande: `restore_data`
- ✅ Tout fonctionne en 5 minutes

**C'est FAIT!** 🎉

---

**Pour plus: [DOCUMENTS_INDEX.md](DOCUMENTS_INDEX.md)**
