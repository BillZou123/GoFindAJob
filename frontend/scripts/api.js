const API_URL = 'http://localhost:5001';

async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        },
        credentials: 'include',
    };

    if (body) {
        options.body = JSON.stringify(body);
    }

    const response = await fetch(`${API_URL}/api${endpoint}`, options);
    const data = await response.json();

    return { response, data };
}

async function signup(username, email, password) {
    return apiCall('/signup', 'POST', { username, email, password });
}

async function login(username, password) {
    return apiCall('/login', 'POST', { username, password });
}

async function logout() {
    return apiCall('/logout', 'POST');
}

async function getCurrentUser() {
    const { response, data } = await apiCall('/me', 'GET');
    if (response.ok) {
        return data;
    }
    return null;
}
