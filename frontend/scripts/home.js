async function loadHomePage() {
    try {
        const user = await getCurrentUser();
        if (user) {
            document.getElementById('username').textContent = user.username;
        } else {
            // Not authenticated, redirect to login
            window.location.href = '/';
        }
    } catch (error) {
        showError('Connection error. Please refresh the page or log in again.');
    }
}

function navigateTo(page) {
    window.location.href = '/pages/' + page;
}

function showError(message) {
    const errorEl = document.getElementById('errorMessage');
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
    setTimeout(() => errorEl.classList.add('hidden'), 5000);
}

async function handleLogout() {
    try {
        await apiCall('/logout', 'POST');
        window.location.href = '/';
    } catch (error) {
        showError('Logout failed');
    }
}

// Load home page on page load
window.addEventListener('load', loadHomePage);
