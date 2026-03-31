(function () {
    function getCookie(name) {
        const value = '; ' + document.cookie;
        const parts = value.split('; ' + name + '=');
        if (parts.length === 2) {
            return parts.pop().split(';').shift();
        }
        return '';
    }

    function buildUrl(template, id) {
        return template.replace('0', String(id));
    }

    const config = document.getElementById('prospects-page-config');
    const urls = {
        uploadCsv: config ? (config.dataset.uploadCsvUrl || '') : '',
        uploadDetailTemplate: config ? (config.dataset.uploadDetailTemplate || '') : '',
        getProspectDataTemplate: config ? (config.dataset.getProspectDataTemplate || '') : '',
        cancelConversionTemplate: config ? (config.dataset.cancelConversionTemplate || '') : '',
        deleteProspectTemplate: config ? (config.dataset.deleteProspectTemplate || '') : '',
        enrollmentForm: config ? (config.dataset.enrollmentFormUrl || '') : ''
    };

    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    const uploadStatus = document.getElementById('uploadStatus');
    const uploadBtn = document.getElementById('uploadBtn');

    function showStatus(msg, cls) {
        if (!uploadStatus) {
            return;
        }
        uploadStatus.className = 'mt-2 text-sm ' + (cls || '');
        uploadStatus.textContent = msg;
    }

    async function uploadCSV(file) {
        showStatus('Import en cours...', 'text-slate-500');
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(urls.uploadCsv, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: formData,
                credentials: 'same-origin'
            });

            if (!response.ok) {
                showStatus('Erreur import CSV', 'text-red-600');
                return;
            }

            const data = await response.json();
            let statusMsg = data.created + ' nouveau(x) • ' + data.skipped + ' fusionnes';
            if (data.duplicates && data.duplicates.length > 0) {
                statusMsg += ' • ' + data.duplicates.length + ' doublon(s) detecte(s)';
            }
            showStatus(statusMsg, 'text-green-700');

            if (uploadStatus) {
                const detailsBtn = document.createElement('button');
                detailsBtn.type = 'button';
                detailsBtn.className = 'mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 font-medium';
                detailsBtn.textContent = 'Voir les details';
                detailsBtn.addEventListener('click', function () {
                    window.location.href = buildUrl(urls.uploadDetailTemplate, data.upload_id);
                });
                uploadStatus.appendChild(detailsBtn);
            }
        } catch (error) {
            showStatus('Erreur reseau pendant l\'import', 'text-red-600');
            console.error(error);
        }
    }

    if (uploadBtn && fileInput) {
        uploadBtn.addEventListener('click', function () {
            fileInput.click();
        });
    }

    if (dropzone && fileInput) {
        dropzone.addEventListener('dragover', function (event) {
            event.preventDefault();
            dropzone.classList.add('dragover');
        });

        dropzone.addEventListener('dragleave', function () {
            dropzone.classList.remove('dragover');
        });

        dropzone.addEventListener('drop', function (event) {
            event.preventDefault();
            dropzone.classList.remove('dragover');
            const file = event.dataTransfer.files[0];
            if (file) {
                uploadCSV(file);
            }
        });

        fileInput.addEventListener('change', function (event) {
            const file = event.target.files[0];
            if (file) {
                uploadCSV(file);
            }
        });
    }

    window.convertProspect = async function (id) {
        try {
            const response = await fetch(buildUrl(urls.getProspectDataTemplate, id));
            if (!response.ok) {
                return;
            }

            const data = await response.json();
            sessionStorage.setItem('converting_prospect_id', String(id));
            sessionStorage.setItem('prospect_prefill', JSON.stringify({
                first_name: data.first_name || '',
                last_name: data.last_name || '',
                email: data.email || '',
                phone: data.phone || '',
                birth_date: data.birth_date || '',
                motivation: data.message || ''
            }));

            if (window.htmx) {
                window.htmx.ajax('GET', urls.enrollmentForm, { target: 'body', swap: 'beforeend' });
            } else {
                window.location.href = urls.enrollmentForm;
            }
        } catch (error) {
            console.error(error);
        }
    };

    window.cancelConversion = async function (id) {
        if (!window.confirm('Etes-vous sur de vouloir annuler cette conversion ? L\'etudiant correspondant sera supprime.')) {
            return;
        }

        try {
            const response = await fetch(buildUrl(urls.cancelConversionTemplate, id), {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                credentials: 'same-origin'
            });

            if (response.ok) {
                window.location.reload();
            } else {
                window.alert('Erreur lors de l\'annulation');
            }
        } catch (error) {
            console.error(error);
            window.alert('Erreur reseau');
        }
    };

    window.deleteProspect = async function (id) {
        if (!window.confirm('Etes-vous sur de vouloir supprimer ce prospect ?')) {
            return;
        }

        try {
            const response = await fetch(buildUrl(urls.deleteProspectTemplate, id), {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                credentials: 'same-origin'
            });

            if (response.ok) {
                window.location.reload();
            } else {
                window.alert('Erreur lors de la suppression');
            }
        } catch (error) {
            console.error(error);
            window.alert('Erreur reseau');
        }
    };

    document.addEventListener('click', function (event) {
        const actionButton = event.target.closest('[data-prospect-action][data-prospect-id]');
        if (!actionButton) {
            return;
        }

        const id = parseInt(actionButton.dataset.prospectId, 10);
        if (!Number.isFinite(id)) {
            return;
        }

        const action = actionButton.dataset.prospectAction;
        if (action === 'convert') {
            window.convertProspect(id);
        }
        if (action === 'cancel') {
            window.cancelConversion(id);
        }
        if (action === 'delete') {
            window.deleteProspect(id);
        }
    });
})();
