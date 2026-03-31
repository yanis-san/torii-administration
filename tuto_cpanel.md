# Tuto Deploiement cPanel (Django + MySQL + WhiteNoise + Tailwind offline)

Ce guide est la procedure complete pour deployer l'app sur cPanel et retrouver exactement:
- les memes donnees
- les memes fichiers media (photos, cartes d'identite, recus)
- le frontend offline (Tailwind compile, HTMX/Alpine locaux)

Domaine cible: **adminstitute.ajitorii.com**

---

## 1) Variables d'environnement a mettre dans cPanel (interface)

Dans cPanel (Application Python / Environment Variables), ajoute exactement:

```env
DJANGO_SETTINGS_MODULE=config.settings.prod

SECRET_KEY=mettez_une_vraie_cle_secrete_longue

ALLOWED_HOSTS=adminstitute.ajitorii.com
CSRF_TRUSTED_ORIGINS=https://adminstitute.ajitorii.com

DB_NAME=ma_base_de_donnees
DB_USER=nom_utilisateur
DB_PASSWORD=mot_de_passe
DB_HOST=localhost
DB_PORT=3306

# Optionnel (utile si cPanel ne mappe pas /media vers le dossier media)
SERVE_MEDIA_WITH_DJANGO=True

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=votre_email@gmail.com
EMAIL_HOST_PASSWORD=votre_mot_de_passe_app
```

Notes:
- `DJANGO_SETTINGS_MODULE=config.settings.prod` est obligatoire en prod.
- `SERVE_MEDIA_WITH_DJANGO=True` est un fallback pratique si besoin.

---

## 2) Exporter les donnees depuis votre local

Depuis votre machine locale, dans le dossier projet:

```powershell
python manage.py dumpdata --exclude auth.permission --exclude contenttypes --indent 2 -o db_backup_postgres_before_mysql_20260324.json
```

Fichier JSON de donnees deja present dans votre projet (racine):

`db_backup_postgres_before_mysql_20260324.json`

Chemin complet local:

`C:\Users\Social Media Manager\Documents\codes\school_management\db_backup_postgres_before_mysql_20260324.json`

---

## 3) Uploader le code + donnees + media sur cPanel

A uploader sur le serveur:
- tout le code du projet
- `db_backup_postgres_before_mysql_20260324.json`
- le dossier `media/` local

Emplacement conseille sur serveur:
- projet: `~/.../school_management/`
- medias: `~/.../school_management/media/`

Chemin local du dossier media a uploader:

`C:\Users\Social Media Manager\Documents\codes\school_management\media\`

Important:
- `MEDIA_ROOT` pointe vers `BASE_DIR / media`.
- Donc le dossier `media` doit etre **a la racine du projet Django**.

---

## 4) Installer les dependances en prod

Dans le terminal cPanel (dans le dossier projet):

```bash
pip install -r requirements.txt
```

---

## 5) Appliquer la structure DB puis restaurer les donnees

Toujours dans le dossier projet:

```bash
python manage.py migrate --settings=config.settings.prod
python manage.py loaddata db_backup_postgres_before_mysql_20260324.json --settings=config.settings.prod
```

Ordre obligatoire:
1. `migrate`
2. `loaddata`

Si vous voyez une erreur de doublons, utilisez une base vide ou recreez la base MySQL puis relancez `migrate` + `loaddata`.

---

## 6) Build Tailwind (offline) + collectstatic

Le projet est configure pour un frontend offline.

Lancer:

```bash
python manage.py tailwind build --settings=config.settings.prod
python manage.py collectstatic --noinput --settings=config.settings.prod
```

Resultat:
- CSS Tailwind compile
- fichiers statiques servis via WhiteNoise

---

## 7) Redemarrer l'application Python cPanel

Apres migration/import/build, redemarrez l'app (Passenger) depuis cPanel.

---

## 8) Verifications rapides apres deploiement

### A. Verification donnees

```bash
python manage.py shell --settings=config.settings.prod
```

Puis:

```python
from core.models import User
from students.models import Student
from finance.models import Payment
print('Users:', User.objects.count())
print('Students:', Student.objects.count())
print('Payments:', Payment.objects.count())
```

### B. Verification media

- Ouvrir une page etudiant avec photo
- Ouvrir un recu upload
- Si 404 media: laisser `SERVE_MEDIA_WITH_DJANGO=True` ou configurer correctement le mapping media cPanel

### C. Verification statiques

- Ouvrir dashboard
- verifier CSS/JS charges (pas de page sans style)

---

## 9) Procedure de mise a jour ulterieure (sans reset)

Pour une mise a jour classique:

```bash
pip install -r requirements.txt
python manage.py migrate --settings=config.settings.prod
python manage.py tailwind build --settings=config.settings.prod
python manage.py collectstatic --noinput --settings=config.settings.prod
```

Si vous devez aussi synchroniser les donnees local -> prod:
1. refaire `dumpdata` local
2. uploader nouveau JSON
3. `loaddata` (idealement sur base cible propre pour eviter doublons)

---

## 10) Checklist finale (resume)

1. Variables env cPanel configurees (prod + DB + domaine)
2. Code + `db_backup_postgres_before_mysql_20260324.json` + `media/` uploades
3. `pip install -r requirements.txt`
4. `migrate`
5. `loaddata`
6. `tailwind build`
7. `collectstatic`
8. Restart Passenger
9. Test login + dashboard + media + paiement

---

Si tout est fait dans cet ordre, le site doit fonctionner directement avec les memes donnees et les memes fichiers media.

---

## Bloc Ultra Court (Copier-Coller Jour J)

### A) Variables cPanel (Environment Variables)

```env
DJANGO_SETTINGS_MODULE=config.settings.prod
SECRET_KEY=mettez_une_vraie_cle_secrete_longue

ALLOWED_HOSTS=adminstitute.ajitorii.com
CSRF_TRUSTED_ORIGINS=https://adminstitute.ajitorii.com

DB_NAME=ma_base_de_donnees
DB_USER=nom_utilisateur
DB_PASSWORD=mot_de_passe
DB_HOST=localhost
DB_PORT=3306

SERVE_MEDIA_WITH_DJANGO=True

EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=votre_email@gmail.com
EMAIL_HOST_PASSWORD=votre_mot_de_passe_app
```

### B) Fichiers a uploader

1. Code du projet complet
2. `db_backup_postgres_before_mysql_20260324.json`
3. Dossier `media/` complet

### C) Commandes terminal cPanel (dans la racine du projet)

```bash
pip install -r requirements.txt
python manage.py migrate --settings=config.settings.prod
python manage.py loaddata db_backup_postgres_before_mysql_20260324.json --settings=config.settings.prod
python manage.py tailwind build --settings=config.settings.prod
python manage.py collectstatic --noinput --settings=config.settings.prod
```

### D) Final

Redemarrer l'app Python (Passenger) depuis cPanel.
