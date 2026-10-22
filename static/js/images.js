document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('upload-tab-btn').addEventListener('click', () => {
        window.location.href = './upload';
    });

    document.querySelectorAll('.delete-form').forEach(form => {
        form.addEventListener('submit', (event) => {
            if (!confirm('Are you sure you want to delete this image?')) {
                event.preventDefault();
            }
        });
    });
});