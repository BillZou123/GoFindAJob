function switchTab(tab) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(el => {
        el.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(el => {
        el.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tab).classList.add('active');
    event.target.classList.add('active');

    // Clear messages
    clearMessages();
}

function clearMessages() {
    document.querySelectorAll('.error-message, .success-message').forEach(el => {
        el.style.display = 'none';
    });
}

function showError(message, type) {
    const errorEl = document.getElementById(`${type}-error`);
    errorEl.textContent = message;
    errorEl.style.display = 'block';
}

function showSuccess(message, type) {
    const successEl = document.getElementById(`${type}-success`);
    successEl.textContent = message;
    successEl.style.display = 'block';
}

function setLoading(isLoading, type) {
    const btn = document.getElementById(`${type}-btn`);
    const loading = document.getElementById(`${type}-loading`);
    
    if (isLoading) {
        btn.style.display = 'none';
        loading.style.display = 'block';
    } else {
        btn.style.display = 'block';
        loading.style.display = 'none';
    }
}

async function handleSignIn(event) {
    event.preventDefault();
    clearMessages();

    const username = document.getElementById('signin-username').value;
    const password = document.getElementById('signin-password').value;

    // Validate input
    if (!username || !password) {
        showError('Please enter both username and password', 'signin');
        return;
    }

    setLoading(true, 'signin');

    try {
        const { response, data } = await login(username, password);

        if (response.ok) {
            showSuccess(`Welcome, ${data.user.username}!`, 'signin');
            setTimeout(() => {
                window.location.href = '/pages/home.html';
            }, 1500);
        } else {
            // Show specific error from backend
            showError(data.error || 'Invalid username or password', 'signin');
        }
    } catch (error) {
        console.error('Login error:', error);
        showError('Cannot connect to server. Make sure backend is running on http://localhost:5001', 'signin');
    } finally {
        setLoading(false, 'signin');
    }
}

async function handleSignUp(event) {
    event.preventDefault();
    clearMessages();

    const username = document.getElementById('signup-username').value;
    const email = document.getElementById('signup-email').value;
    const password = document.getElementById('signup-password').value;
    const confirmPassword = document.getElementById('signup-confirm-password').value;

    // Validate input
    if (!username || !email || !password || !confirmPassword) {
        showError('Please fill in all fields', 'signup');
        return;
    }

    // Validate passwords match
    if (password !== confirmPassword) {
        showError('Passwords do not match', 'signup');
        return;
    }

    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showError('Please enter a valid email address', 'signup');
        return;
    }

    setLoading(true, 'signup');

    try {
        const { response, data } = await signup(username, email, password);

        if (response.ok) {
            showSuccess('Account created successfully! You can now sign in.', 'signup');
            setTimeout(() => {
                switchTab('signin');
                document.getElementById('signin-username').value = username;
            }, 1500);
        } else {
            showError(data.error || 'Sign up failed', 'signup');
        }
    } catch (error) {
        console.error('Sign up error:', error);
        showError('Cannot connect to server. Make sure backend is running on http://localhost:5001', 'signup');
    } finally {
        setLoading(false, 'signup');
    }
}

// Load page on page load
window.addEventListener('load', () => {
    // Check if user is already logged in
    getCurrentUser().then(user => {
        if (user) {
            window.location.href = '/pages/home.html';
        }
    });
});
