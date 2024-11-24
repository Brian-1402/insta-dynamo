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
            window.location.href = "/";
        } else {
            alert(data.error || "Login failed");
        }
    } catch (error) {
        console.error("Login error:", error);
        alert("An error occurred during login");
    }
}
  
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
            alert("Signup successful");
            window.location.href = "/";
        } else {
            alert(data.error || "Signup failed");
        }
    } catch (error) {
        console.error("Signup error:", error);
        alert("An error occurred during signup");
    }
}

// Add event listeners when the document loads
document.addEventListener('DOMContentLoaded', () => {
    const signupForm = document.getElementById("signupForm");
    if (signupForm) {
        signupForm.addEventListener("submit", handleSignup);
    }
    
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", handleLogin);
    }
});