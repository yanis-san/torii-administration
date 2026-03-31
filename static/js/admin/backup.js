(function () {
    const config = document.getElementById('backup-config');
    if (!config) {
        return;
    }

    const createUrl = config.dataset.backupCreateUrl || '';
    const restoreUrl = config.dataset.backupRestoreUrl || '';

    function getCookie(name) {
        const value = '; ' + document.cookie;
        const parts = value.split('; ' + name + '=');
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return '';
    }

    const csrfToken = getCookie('csrftoken');

    const backupButton = document.getElementById('btn-backup');
    if (backupButton && createUrl) {
        backupButton.addEventListener('click', function () {
            if (!window.confirm('Creer une nouvelle sauvegarde ?')) {
                return;
            }

            fetch(createUrl, {
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken }
            })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    window.alert(data.message || 'Operation terminee');
                    if (data.success) {
                        window.location.reload();
                    }
                })
                .catch(function (error) {
                    window.alert('Erreur: ' + error);
                });
        });
    }

    document.querySelectorAll('.btn-restore[data-backup]').forEach(function (button) {
        button.addEventListener('click', function () {
            const backupName = button.dataset.backup || '';
            const message = 'Attention: ceci va remplacer la base de donnees actuelle.\n\nSauvegarde: ' + backupName;
            if (!window.confirm(message)) {
                return;
            }

            fetch(restoreUrl, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                body: 'backup_name=' + encodeURIComponent(backupName)
            })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    window.alert(data.message || 'Operation terminee');
                    if (data.success) {
                        window.setTimeout(function () {
                            window.location.reload();
                        }, 2000);
                    }
                })
                .catch(function (error) {
                    window.alert('Erreur: ' + error);
                });
        });
    });
})();
