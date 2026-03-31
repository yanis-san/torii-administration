(function () {
    const body = document.body;

    const syncProgressBars = (root = document) => {
        root.querySelectorAll('[data-progress-width]').forEach((bar) => {
            const rawValue = parseFloat(bar.dataset.progressWidth || '0');
            const progress = Math.max(0, Math.min(100, Number.isFinite(rawValue) ? rawValue : 0));
            bar.style.width = `${progress}%`;
        });
    };

    const hexToRgba = (hex, alpha) => {
        const value = String(hex || '').trim().replace('#', '');
        if (!/^[0-9a-fA-F]{6}$/.test(value)) {
            return '';
        }

        const red = parseInt(value.slice(0, 2), 16);
        const green = parseInt(value.slice(2, 4), 16);
        const blue = parseInt(value.slice(4, 6), 16);
        return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
    };

    const syncCategoryChips = (root = document) => {
        root.querySelectorAll('[data-category-color]').forEach((chip) => {
            const color = chip.dataset.categoryColor || '';
            const bgAlpha = parseFloat(chip.dataset.categoryBgAlpha || '0.13');
            const borderAlpha = parseFloat(chip.dataset.categoryBorderAlpha || '0');

            const backgroundColor = hexToRgba(color, Number.isFinite(bgAlpha) ? bgAlpha : 0.13);
            if (!backgroundColor) {
                return;
            }

            chip.style.backgroundColor = backgroundColor;
            chip.style.color = color;

            const safeBorderAlpha = Number.isFinite(borderAlpha) ? borderAlpha : 0;
            if (safeBorderAlpha > 0) {
                const borderColor = hexToRgba(color, safeBorderAlpha);
                if (borderColor) {
                    chip.style.border = `1px solid ${borderColor}`;
                }
            }
        });
    };

    const scheduleBackupDismiss = (root = document) => {
        root.querySelectorAll('[data-backup-auto-dismiss="true"]').forEach((element) => {
            if (element.dataset.dismissScheduled === 'true') {
                return;
            }
            element.dataset.dismissScheduled = 'true';
            window.setTimeout(() => {
                if (document.body.contains(element)) {
                    element.remove();
                }
            }, 8000);
        });
    };

    const runConfirm = (message) => {
        if (!message) {
            return true;
        }
        const parts = message.split('||').map((part) => part.trim()).filter(Boolean);
        return parts.every((part) => window.confirm(part));
    };

    body.addEventListener('htmx:configRequest', (event) => {
        event.detail.headers['X-CSRFToken'] = body.dataset.csrfToken;
    });

    document.addEventListener('htmx:afterSwap', (event) => {
        syncProgressBars(event.target);
        scheduleBackupDismiss(event.target);
        syncCategoryChips(event.target);
    });

    document.addEventListener('keydown', (e) => {
        const activeTag = document.activeElement ? document.activeElement.tagName : '';

        if (e.key === '/' && !e.ctrlKey && !e.metaKey && !['INPUT', 'TEXTAREA'].includes(activeTag)) {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        if (e.key === 'k' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }

        if (e.key === 'Escape' && activeTag === 'INPUT') {
            document.activeElement.blur();
        }

        if (e.key === 'Escape') {
            const modal = Array.from(document.querySelectorAll('[data-close-on-escape="true"]')).pop();
            if (modal) {
                modal.remove();
            }
        }

        if (e.altKey && !e.ctrlKey && !e.metaKey && !e.shiftKey && e.key.toLowerCase() === 's') {
            e.preventDefault();
            const sidebarButton = document.querySelector('aside button[class*="absolute"]');
            if (sidebarButton) {
                sidebarButton.click();
            }
        }

        if (e.ctrlKey && e.altKey && e.key.toLowerCase() === 's') {
            e.preventDefault();
            const backupButton = Array.from(document.querySelectorAll('button')).find((btn) => (
                btn.textContent.includes('Sauvegarder') || btn.textContent.includes('💾')
            ));
            if (backupButton) {
                backupButton.click();
            }
        }

        if (e.altKey && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
            const shortcuts = {
                Backquote: body.dataset.urlDashboard,
                Digit1: body.dataset.urlStudents,
                Digit2: body.dataset.urlAcademics,
                Digit3: body.dataset.urlProspects,
                Digit4: body.dataset.urlPaymentStatus,
                Digit5: body.dataset.urlTeacherPayroll,
                Digit6: body.dataset.urlCashDashboard,
            };

            if (shortcuts[e.code]) {
                e.preventDefault();
                window.location.href = shortcuts[e.code];
            }
        }

        if (e.altKey && e.ctrlKey && e.key.toLowerCase() === 'q' && !e.metaKey && !e.shiftKey) {
            e.preventDefault();
            window.location.href = body.dataset.urlSyncPage;
        }
    });

    document.addEventListener('submit', (event) => {
        const form = event.target.closest('form[data-confirm]');
        if (!form) {
            return;
        }
        if (!runConfirm(form.dataset.confirm)) {
            event.preventDefault();
        }
    });

    document.addEventListener('change', (event) => {
        const autoSubmit = event.target.closest('[data-auto-submit="true"]');
        if (autoSubmit && autoSubmit.form) {
            autoSubmit.form.submit();
            return;
        }

        const navigateSelect = event.target.closest('select[data-navigate-value="true"]');
        if (navigateSelect && navigateSelect.value) {
            window.location.href = navigateSelect.value;
        }
    });

    document.addEventListener('click', (event) => {
        const trigger = event.target.closest('[data-confirm], [data-click-target], [data-toggle-class-target], [data-window-open-select], [data-remove-selector], [data-remove-closest]');
        if (!trigger) {
            return;
        }

        if (trigger.dataset.confirm && !runConfirm(trigger.dataset.confirm)) {
            event.preventDefault();
            return;
        }

        if (trigger.dataset.clickTarget) {
            event.preventDefault();
            const target = document.querySelector(trigger.dataset.clickTarget);
            if (target) {
                target.click();
            }
        }

        if (trigger.dataset.toggleClassTarget && trigger.dataset.toggleClassName) {
            event.preventDefault();
            const target = document.querySelector(trigger.dataset.toggleClassTarget);
            if (!target) {
                return;
            }
            const mode = trigger.dataset.toggleClassMode || 'toggle';
            if (mode === 'add') {
                target.classList.add(trigger.dataset.toggleClassName);
            } else if (mode === 'remove') {
                target.classList.remove(trigger.dataset.toggleClassName);
            } else {
                target.classList.toggle(trigger.dataset.toggleClassName);
            }
        }

        if (trigger.dataset.windowOpenSelect) {
            event.preventDefault();
            const select = document.querySelector(trigger.dataset.windowOpenSelect);
            if (select && select.value) {
                window.open(select.value, '_blank');
            }
        }

        if (trigger.dataset.removeSelector) {
            event.preventDefault();
            const target = document.querySelector(trigger.dataset.removeSelector);
            if (target) {
                target.remove();
            }
        }

        if (trigger.dataset.removeClosest) {
            event.preventDefault();
            const target = trigger.closest(trigger.dataset.removeClosest);
            if (target) {
                target.remove();
            }
        }
    });

    syncProgressBars();
    scheduleBackupDismiss();
    syncCategoryChips();
}());
