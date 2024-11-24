// navManager.js

// Store the logged in user in sessionStorage to persist across page loads
function setLoggedInUser(username) {
    sessionStorage.setItem('loggedInUser', username);
}

function getLoggedInUser() {
    return sessionStorage.getItem('loggedInUser');
}

function clearLoggedInUser() {
    sessionStorage.removeItem('loggedInUser');
}

// Function to update the navigation based on auth state
function updateNavigation() {
    const username = getLoggedInUser();
    const navElement = document.querySelector('#navigation');
    const title = document.title;
    
    if (username) {
        // User is logged in
        navElement.innerHTML = `
            <header>
                <div style="display: flex; justify-content: space-between; align-items: center">
                    <div style="flex: 1"></div>
                    <h1 style="flex: 1; text-align: center; margin: 0">${title}</h1>
                    <div style="flex: 1; text-align: right">
                        <div style="margin-bottom: 8px">Logged in as ${username}</div>
                        <a href="#" onclick="handleLogout(); return false;">Logout</a>
                    </div>
                </div>
                <br>
                <nav style="margin-top: 16px">
                    <a href="/">Home</a>
                    <a href="/upload">Upload</a>
                    <a href="/gallery">Gallery</a>
                </nav>
            </header>
        `;
    } else {
        // User is not logged in
        navElement.innerHTML = `
            <header>
                <h1>${title}</h1>
                <br>
                <nav>
                    <a href="/">Home</a>
                    <a href="/login">Login</a>
                </nav>
            </header>
        `;
    }
}

// Logout handler
async function handleLogout() {
    try {
        const response = await fetch("/auth/logout", {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });

        if (response.ok) {
            clearLoggedInUser();
            updateNavigation();
            window.location.href = "/";
        } else {
            showNotification("Error", "Logout failed", "error");
        }
    } catch (error) {
        console.error("Logout error:", error);
    showNotification("Error", "An error occurred during logout", "error");
    }
}

// Login handler
async function handleLogin(event) {
    event.preventDefault();
  
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
  
    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
        });
  
        const data = await response.json();
  
        if (response.ok) {
            if (data)
                setLoggedInUser(username);  // Store the username
                showNotification("Success", "Login successful!", "success");
                // wait for some time until notif can be read
                setTimeout(() => { window.location.href = "/"; }, 800);
                // window.location.href = "/";
        } else {
            // output returned is a HTTPException with status code 400
            showNotification("Error", "Login failed", "error");
        }
    } catch (error) {
        console.error("Login error:", error);
        showNotification("Error", "An error occurred during login", "error");
    }
}

// Signup handler
async function handleSignup(event) {
    event.preventDefault();
    
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const confirm_password = document.getElementById("confirm_password").value;

    try {
        const response = await fetch("/auth/signup", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password, confirm_password }),
        });

        const data = await response.json();

        if (response.ok) {
            setLoggedInUser(username);  // Store the username after successful signup
            showNotification("Success", "Signup successful!", "success");
            // wait for sometime until notif can be read
            setTimeout(() => { window.location.href = "/"; }, 800);
            // window.location.href = "/";
        } else {
            showNotification("Error", "Signin failed", "error");
        }
    } catch (error) {
        console.error("Signup error:", error);
        showNotification("Error", "An error occurred during signup", "error");
    }
}

// Initialize navigation when the page loads
document.addEventListener('DOMContentLoaded', () => {
    updateNavigation();
    
    // Add login form handler
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", handleLogin);
    }

    // Add signup form handler
    const signupForm = document.getElementById("signupForm");
    if (signupForm) {
        signupForm.addEventListener("submit", handleSignup);
    }
});


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
