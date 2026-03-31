(function () {
    document.addEventListener('keydown', (event) => {
        if (event.altKey && event.key.toLowerCase() === 'a') {
            event.preventDefault();
            const button = document.getElementById('new-cohort-btn');
            if (button) {
                button.click();
            }
        }
    });
}());
