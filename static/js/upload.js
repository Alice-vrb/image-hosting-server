document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape' || event.key === 'F5') {
            event.preventDefault();

            sessionStorage.removeItem('pageWasVisited');
            window.location.href = '../';
        }
    });
});

document.addEventListener('DOMContentLoaded', () => {
    const fileUpload = document.getElementById('file-upload');
    const imagesButton = document.getElementById('images-tab-btn');
    const dropzone = document.querySelector('.upload__dropzone');
    const currentUploadInput = document.querySelector('.upload__input');
    const copyButton = document.querySelector('.upload__copy');

    const updateTabStyles = () => {
        const uploadTab = document.getElementById('upload-tab-btn');
        const imagesTab = document.getElementById('images-tab-btn');

        const isImagesPage = window.location.pathname.includes('/images');

        uploadTab.classList.remove('upload__tab--active');
        imagesTab.classList.remove('upload__tab--active');

        if (isImagesPage) {
            imagesTab.classList.add('upload__tab--active');
        } else {
            uploadTab.classList.add('upload__tab--active');
        }
    };

    const handleAndStoreFiles = async (files) => {
        if (!files || files.length === 0) {
            return;
        }
        const storedFiles = JSON.parse(localStorage.getItem('uploadedImages')) || [];
        let filesAdded = false;

        const formData = new FormData();

        const fileNames = [];

        for (const file of files) {
            fileNames.push(file.name);
            formData.append('files', file);

            filesAdded = true;
        }
        formData.append('names', JSON.stringify(fileNames));
        console.log('Names JSON:', formData);
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                console.error('Upload failed:', response.status, errorData.error);
                alert(errorData.error || 'Upload failed.');
                return;
            }

            const result = await response.json();

            result.files.forEach(f => {
                storedFiles.push({ name: f.name, url: f.url });
            });
            localStorage.setItem('uploadedImages', JSON.stringify(storedFiles));
            updateTabStyles();

            if (currentUploadInput && result.files.length > 0) {
                currentUploadInput.value = result.files[result.files.length - 1].url;
            }
            alert("Files selected successfully! Go to the 'Images' tab to view them.");

        } catch (error) {
            console.error('Upload error:', error);
        }
    };

    if (copyButton && currentUploadInput) {
        copyButton.addEventListener('click', () => {
            const textToCopy = currentUploadInput.value;

            if (textToCopy && textToCopy !== 'https://') {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    copyButton.textContent = 'COPIED!';
                    setTimeout(() => {
                        copyButton.textContent = 'COPY';
                    }, 2000);
                }).catch(err => {
                    console.error('Failed to copy text: ', err);
                });
            }
        });
    }

    if (imagesButton) {
        imagesButton.addEventListener('click', () => {
            window.location.href = './images';
        });
    }

    fileUpload.addEventListener('change', async (event) => {
        await handleAndStoreFiles(event.target.files);
        event.target.value = '';
    });

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    dropzone.addEventListener('drop', async (event) => {
        await handleAndStoreFiles(event.dataTransfer.files);
    });

    updateTabStyles();
});