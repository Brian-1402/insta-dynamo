// WebSocket connection
let socket = null;

function initializeWebSocket() {
    // Dynamically construct WebSocket URL based on current location
    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const wsHost = window.location.host; // Automatically picks up current host and port
    const wsPath = "/admin_dashboard"; // WebSocket endpoint

    socket = new WebSocket(`${wsProtocol}://${wsHost}${wsPath}`);

    socket.onopen = function (event) {
        console.log("WebSocket connection established");
        showNotification('Connected', 'WebSocket connection established', 'success');
    };

    socket.onmessage = function (event) {
        try {
            const data = JSON.parse(event.data);
            updateRingStatus(data);
        } catch (error) {
            console.error("Error parsing WebSocket message:", error);
            showNotification('Error', 'Failed to parse WebSocket data', 'error');
        }
    };

    socket.onerror = function (error) {
        console.error("WebSocket error:", error);
        showNotification('Error', 'WebSocket connection error', 'error');
    };

    socket.onclose = function (event) {
        console.log("WebSocket connection closed");
        showNotification('Disconnected', 'WebSocket connection closed. Attempting to reconnect...', 'warning');
        setTimeout(initializeWebSocket, 5000);
    };
}


function updateRingStatus(data) {
    try {
        const virtualNodesElement = document.getElementById('virtual_nodes');
        const physicalNodesElement = document.getElementById('physical_nodes');

        if (virtualNodesElement) {
            virtualNodesElement.innerText = Array.isArray(data.virtual_nodes) ? 
                data.virtual_nodes.join(', ') : 'No virtual nodes';
        }

        if (physicalNodesElement) {
            physicalNodesElement.innerText = Array.isArray(data.physical_nodes) ? 
                data.physical_nodes.join(', ') : 'No physical nodes';
        }
    } catch (error) {
        console.error("Error updating ring status:", error);
        showNotification('Error', 'Failed to update ring status', 'error');
    }
}

async function addNode(event) {
    event.preventDefault();

    const form = event.target;
    const nodeIdInput = form.querySelector('#nodeId');
    const hostInput = form.querySelector('#host');
    const portInput = form.querySelector('#port');

    // Validate inputs before proceeding
    if (!nodeIdInput.value || !hostInput.value || !portInput.value) {
        showNotification('Error', 'All fields are required', 'error');
        return;
    }

    // Create a flag to track if the request is in progress
    if (form.dataset.isSubmitting === 'true') {
        return; // Prevent multiple submissions
    }

    try {
        // Mark form as submitting and disable inputs
        form.dataset.isSubmitting = 'true';
        disableForm(true);

        const response = await fetch('/add_node', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                node_id: nodeIdInput.value,
                host: hostInput.value,
                port: parseInt(portInput.value, 10),
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            showNotification('Success', result.message || 'Node added successfully', 'success');
        } else {
            throw new Error(result.message || 'Failed to add node');
        }
    } catch (error) {
        console.error("Error in addNode:", error);
        showNotification('Error', error.message || 'Error adding node', 'error');
    } finally {
        // Always clean up form state
        form.dataset.isSubmitting = 'false';
        disableForm(false);
        form.reset();
    }
}

function disableForm(disable) {
    try {
        const form = document.getElementById('nodeForm');
        if (!form) return;

        // Get all form controls
        const formControls = form.querySelectorAll('input, button, select, textarea');
        
        formControls.forEach(element => {
            element.disabled = disable;
            // Add visual feedback
            if (disable) {
                element.classList.add('disabled');
            } else {
                element.classList.remove('disabled');
            }
        });

        // Update form opacity to provide visual feedback
        form.style.opacity = disable ? '0.7' : '1';
    } catch (error) {
        console.error("Error in disableForm:", error);
    }
}

function showNotification(title, message, type) {
    try {
        const notificationContainer = document.getElementById('notificationContainer') || 
            (() => {
                const container = document.createElement('div');
                container.id = 'notificationContainer';
                container.style.cssText = `
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    z-index: 1000;
                `;
                document.body.appendChild(container);
                return container;
            })();

        const notification = document.createElement('div');
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
    } catch (error) {
        console.error("Error showing notification:", error);
    }
}

// Initialize WebSocket when page loads
document.addEventListener('DOMContentLoaded', function () {
    try {
        initializeWebSocket();

        // Add form submit handler
        const form = document.getElementById('nodeForm');
        if (form) {
            form.addEventListener('submit', addNode);
            
            // Add input validation
            const inputs = form.querySelectorAll('input');
            inputs.forEach(input => {
                input.addEventListener('input', function() {
                    this.classList.remove('error');
                    if (this.value.trim() === '') {
                        this.classList.add('error');
                    }
                });
            });
        }
    } catch (error) {
        console.error("Error in initialization:", error);
        showNotification('Error', 'Failed to initialize application', 'error');
    }
});

document.addEventListener("DOMContentLoaded", function () {
    const uploadForm = document.getElementById("uploadForm");
    const imageGallery = document.getElementById("imageGallery");

    // Fetch and display the image list when the Image Management tab is selected
    const imageManagementTab = document.getElementById("image-management-tab");
    imageManagementTab.addEventListener("click", fetchImageList);

    // Handle Image Upload
    uploadForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const fileInput = document.getElementById("imageFile");
        const formData = new FormData();
        formData.append("image", fileInput.files[0]);

        try {
            const response = await fetch("/admin/upload_image", {
                method: "POST",
                body: formData,
            });
            const result = await response.json();

            if (result.success) {
                showNotification("Success", "Image uploaded successfully", "success");
                fetchImageList(); // Refresh the gallery after upload
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            showNotification("Error", error.message || "Image upload failed", "error");
        }
        finally {
            fileInput.value = ""; // Clear the file input
        }
    });

    // Fetch and display image list
    async function fetchImageList() {
        try {
            const response = await fetch("/admin/list_images");
            const result = await response.json();

            if (result.success) {
                imageGallery.innerHTML = ""; // Clear existing gallery
                result.images.forEach((filename) => {
                    const imageContainer = document.createElement("div");
                    imageContainer.className = "col-md-3 mb-3";

                    imageContainer.innerHTML = `
                        <div class="card">
                            <a href="/admin/view_image/${filename}" target="_blank">
                                <img src="/admin/view_image/${filename}" class="card-img-top img-thumbnail" alt="${filename}">
                            </a>
                            <div class="card-body text-center">
                                <p class="card-text">${filename}</p>
                            </div>
                        </div>
                    `;

                    imageGallery.appendChild(imageContainer);
                });
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            showNotification("Error", error.message || "Failed to fetch images", "error");
        }
    }
});
