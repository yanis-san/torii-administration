# 🚀 Guide de démarrage rapide - Gestionnaire d'École

## Installation du raccourci (Une seule fois)

### Option 1 : Créer le raccourci automatiquement (Recommandé)

1. **Ouvrez PowerShell en tant qu'administrateur**
   - Clic droit sur le bouton Windows
   - Sélectionnez "Windows PowerShell (Administrateur)"

2. **Naviguez vers le dossier du projet**
   ```powershell
   cd "c:\Users\Social Media Manager\Documents\codes\school_management"
   ```

3. **Exécutez le script de création de raccourci**
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   .\create_shortcut.ps1
   ```

4. **✅ C'est fait !** Un raccourci "Gestionnaire d'Ecole" apparaît sur votre bureau.

---

### Option 2 : Créer le raccourci manuellement

1. **Clic droit sur le bureau** → **Nouveau** → **Raccourci**

2. **Entrez le chemin du fichier batch**
   ```
   c:\Users\Social Media Manager\Documents\codes\school_management\run_app.bat
   ```

3. **Donnez un nom** : `Gestionnaire d'Ecole`

4. **Finish** et c'est tout !

---

## Utilisation quotidienne

### Pour lancer l'application :
1. **Double-clic** sur le raccourci "Gestionnaire d'Ecole" sur le bureau
2. **Attendez 2-3 secondes** que le serveur démarre
3. **Votre navigateur s'ouvre automatiquement** sur l'application

### Pour arrêter l'application :
- Fermer la fenêtre noire du serveur (la console)
- Fermer l'onglet du navigateur

---

## Fichiers créés

- **`run_app.bat`** : Script qui démarre le serveur et ouvre le navigateur
- **`run_app.py`** : Alternative Python (plus avancée)
- **`create_shortcut.ps1`** : Script pour créer automatiquement le raccourci

---

## Dépannage

### Le raccourci ne fonctionne pas ?
- ✅ Vérifiez que le dossier du projet est au bon endroit
- ✅ Vérifiez que le virtual environment est configuré (dossier `.venv`)
- ✅ Essayez de relancer le script `create_shortcut.ps1`

### Le port 8000 est déjà utilisé ?
- Fermez toutes les instances du serveur Django
- Si le problème persiste, modifiez le port dans `run_app.bat` :
  ```
  .venv\Scripts\python.exe manage.py runserver 0.0.0.0:8001
  ```

### Le navigateur ne s'ouvre pas automatiquement ?
- Ouvrez manuellement : `http://127.0.0.1:8000`
- Vérifiez que votre navigateur par défaut est configuré

---

## Notes de sécurité

⚠️ **Ne partagez pas le raccourci** en dehors de votre machine locale
- L'application démarre en mode `DEBUG = True` (développement seulement)
- Le port 8000 n'est accessible que localement

---

**Besoin d'aide ?** Consultez le fichier `guide1.md`
