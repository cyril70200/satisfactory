// main.js - Handles extra product UI for recipe cards

document.addEventListener('DOMContentLoaded', function() {
    // Toggle use_extra_rate ON (+ button)
    document.body.addEventListener('click', function(e) {
        if (e.target.classList.contains('add-extra-product-btn')) {
            const itemUuid = e.target.getAttribute('data-item-uuid');
            const projectId = window.location.pathname.split('/')[2];
            const formData = new FormData();
            formData.append('use_extra_rate', 'true');
            fetch(`/project/${projectId}/item/${itemUuid}/set_use_extra_rate`, {
                method: 'POST',
                body: formData
            }).then(() => window.location.reload());
        }
        // Toggle use_extra_rate OFF (remove/cross button)
        if (e.target.classList.contains('remove-extra-product-btn')) {
            const itemUuid = e.target.getAttribute('data-item-uuid');
            const projectId = window.location.pathname.split('/')[2];
            const formData = new FormData();
            formData.append('use_extra_rate', 'false');
            fetch(`/project/${projectId}/item/${itemUuid}/set_use_extra_rate`, {
                method: 'POST',
                body: formData
            }).then(() => window.location.reload());
        }
    });

    // Update extra rate
    document.body.addEventListener('change', function(e) {
        if (e.target.classList.contains('extra-product-rate-input')) {
            const itemUuid = e.target.getAttribute('data-item-uuid');
            const newRate = parseFloat(e.target.value);
            const projectId = window.location.pathname.split('/')[2];
            const formData = new FormData();
            formData.append('extra_rate', newRate);
            fetch(`/project/${projectId}/item/${itemUuid}/set_extra_rate`, {
                method: 'POST',
                body: formData
            }).then(() => window.location.reload());
        }
    });
});
