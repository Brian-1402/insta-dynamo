// WebSocket connection
let socket = null;

function initializeWebSocket() {
    socket = new WebSocket("ws://localhost:8000/admin_dashboard");
    
    socket.onopen = function(event) {
        console.log("WebSocket connection established");
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        updateRingStatus(data);
    };

    socket.onerror = function(error) {
        console.error("WebSocket error:", error);
    };

    socket.onclose = function(event) {
        console.log("WebSocket connection closed");
        // Try to reconnect after 5 seconds
        setTimeout(initializeWebSocket, 5000);
    };
}

function updateRingStatus(data) {
    document.getElementById('virtual_nodes').innerText = 
        Array.isArray(data.virtual_nodes) ? data.virtual_nodes.join(', ') : '';
    document.getElementById('physical_nodes').innerText = 
        Array.isArray(data.physical_nodes) ? data.physical_nodes.join(', ') : '';
}

function addNode(event) {
    event.preventDefault();
    
    const nodeId = document.getElementById('nodeId').value;
    const host = document.getElementById('host').value;
    const port = document.getElementById('port').value;

    try {
        const response = fetch('/add_node', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                node_id: nodeId,
                host: host,
                port: parseInt(port)
            })
        });

        const result = response.json();
        
        if (result.status === 'success') {
            showNotification('Success', result.message || 'Node added successfully', 'success');
            // Clear the form
            document.getElementById('nodeForm').reset();
        } else {
            showNotification('Error', result.message || 'Failed to add node', 'error');
        }
    } catch (error) {
        showNotification('Error', 'Error adding node: ' + error, 'error');
    }
}

function showNotification(title, message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <strong>${title}:</strong> ${message}
    `;
    
    document.body.appendChild(notification);
    
    // Remove notification after 3 seconds
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Initialize WebSocket when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
    
    // Add form submit handler
    const form = document.getElementById('nodeForm');
    if (form) {
        form.addEventListener('submit', addNode);
    }
});