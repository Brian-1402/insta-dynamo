document.addEventListener("DOMContentLoaded", () => {
    // Check if the upload form exists and initialize its functionality
    const uploadForm = document.getElementById("uploadForm");
    if (uploadForm) {
        initializeUploadForm(uploadForm);
    }

    // Check if the gallery element exists (when the gallery tab is accessed)
    const galleryElement = document.getElementById("gallery");
    if (galleryElement) {
        loadGalleryImages(galleryElement);
    }
});

function initializeUploadForm(uploadForm) {
    uploadForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const formData = new FormData();
        const fileInput = document.getElementById("image");
        const username = sessionStorage.getItem("loggedInUser"); // Retrieve the logged-in user

        if (!username) {
            showNotification("Error", "You must be logged in to upload images.", "error");
            return;
        }

        if (!fileInput.files.length) {
            showNotification("Error", "Please select a file to upload.", "error");
            return;
        }

        formData.append("image", fileInput.files[0]);
        formData.append("username", username);

        try {
            const response = await fetch("/image/upload", {
                method: "POST",
                body: formData,
            });

            if (response.ok) {
                const result = await response.json();
                showNotification("Success", "Image uploaded successfully!", "success");
                uploadForm.reset(); // Reset the form after successful upload
            } else {
                const error = await response.json();
                showNotification("Error", error.detail || "Upload failed.", "error");
            }
        } catch (err) {
            console.error("Error uploading image:", err);
            showNotification("Error", "Error uploading image. Check console for details.", "error");
        }
    });
}

async function loadGalleryImages(galleryElement) {
    try {
        const response = await fetch("/image/list"); // Adjust if your API endpoint differs
        if (response.ok) {
            const images = await response.json();

            if (images.length > 0) {
                galleryElement.innerHTML = images.map(image => `
                    <div class="image-block">
                        <img src="/images/${image.key}" alt="Image">
                    </div>
                `).join("");
            } else {
                galleryElement.innerHTML = "<p>No images found in the gallery.</p>";
            }
        } else {
            galleryElement.innerHTML = "<p>Failed to load images.</p>";
        }
    } catch (err) {
        console.error("Error loading gallery images:", err);
        galleryElement.innerHTML = "<p>Error loading images. Check console for details.</p>";
    }
}

function showNotification(title, message, type) {
    const notificationContainer = document.getElementById("notificationContainer") || 
        (() => {
            const container = document.createElement("div");
            container.id = "notificationContainer";
            container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
            `;
            document.body.appendChild(container);
            return container;
        })();

    const notification = document.createElement("div");
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <strong>${title}:</strong> ${message}
        <button onclick="this.parentElement.remove()" class="close-btn">&times;</button>
    `;

    notification.style.cssText = `
        margin-bottom: 10px;
        padding: 10px;
        border-radius: 4px;
        background-color: ${type === 'success' ? '#d4edda' : 
                          type === 'error' ? '#f8d7da' : 
                          type === 'warning' ? '#fff3cd' : '#cce5ff'};
        border: 1px solid ${type === 'success' ? '#c3e6cb' : 
                           type === 'error' ? '#f5c6cb' : 
                           type === 'warning' ? '#ffeeba' : '#b8daff'};
        color: ${type === 'success' ? '#155724' : 
                type === 'error' ? '#721c24' : 
                type === 'warning' ? '#856404' : '#004085'};
    `;

    notificationContainer.appendChild(notification);

    // Remove notification after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}
