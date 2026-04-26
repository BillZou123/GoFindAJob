async function loadQAPage() {
    try {
        const user = await getCurrentUser();
        if (user) {
            document.getElementById('username').textContent = user.username;
            setupFormHandler();
        } else {
            // Not authenticated, redirect to login
            window.location.href = '/';
        }
    } catch (error) {
        showError('Connection error. Please refresh the page or log in again.');
    }
}

function setupFormHandler() {
    document.getElementById('qaForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const resumeFile = document.getElementById('resumeFile').files[0];
        const jobPost = document.getElementById('jobPost').value;
        const question = document.getElementById('question').value;
        
        if (!resumeFile) {
            showError('Please select a resume file');
            return;
        }
        
        if (!jobPost.trim()) {
            showError('Please paste a job posting');
            return;
        }
        
        if (!question.trim()) {
            showError('Please enter a question');
            return;
        }
        
        // Show loading
        document.getElementById('loadingSpinner').classList.remove('hidden');
        
        try {
            const formData = new FormData();
            formData.append('resume', resumeFile);
            formData.append('job_post', jobPost);
            formData.append('question', question);
            
            const response = await fetch('http://localhost:5001/api/job-qa', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Question answering failed');
            }
            
            showSuccess('Question answered successfully!');
            
            // Display current Q&A result
            const qa = data.qa;
            const resultsList = document.getElementById('resultsList');
            const newResult = createQAResultElement(qa);
            
            // Replace with just the latest result
            resultsList.innerHTML = newResult;
            document.getElementById('resultsSection').classList.remove('hidden');
            
            // Only clear the question field for the next question
            document.getElementById('question').value = '';
            
        } catch (error) {
            showError(error.message || 'Failed to get answer');
        } finally {
            document.getElementById('loadingSpinner').classList.add('hidden');
        }
    });
}

function createQAResultElement(qa) {
    return `
        <div class="qa-result-item">
            <div class="result-header">
                <div class="qa-date">${new Date(qa.created_at).toLocaleDateString()}</div>
            </div>
            <div class="company-question">
                <strong>Company's Question:</strong>
                <p>${escapeHtml(qa.question)}</p>
            </div>
            <div class="generated-answer">
                <strong>Your Answer:</strong>
                <p>${escapeHtml(qa.answer)}</p>
            </div>
        </div>
    `;
}

async function loadQAHistory() {
    try {
        const response = await fetch('http://localhost:5001/api/job-qa-history', {
            method: 'GET',
            credentials: 'include'
        });
        
        if (!response.ok) {
            console.log('No Q&A history available');
            return;
        }
        
        const data = await response.json();
        
        if (data && data.length > 0) {
            const resultsList = document.getElementById('resultsList');
            resultsList.innerHTML = data.map(qa => createQAResultElement(qa)).join('');
            document.getElementById('resultsSection').classList.remove('hidden');
        }
    } catch (error) {
        console.error('Failed to load Q&A history:', error);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    const errorEl = document.getElementById('errorMessage');
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
    setTimeout(() => errorEl.classList.add('hidden'), 5000);
}

function showSuccess(message) {
    const successEl = document.getElementById('successMessage');
    successEl.textContent = message;
    successEl.classList.remove('hidden');
    setTimeout(() => successEl.classList.add('hidden'), 5000);
}

async function handleLogout() {
    try {
        await apiCall('/api/logout', 'POST');
        window.location.href = '/pages/home.html';
    } catch (error) {
        showError('Logout failed');
    }
}

function navigateHome() {
    window.location.href = '/pages/home.html';
}

// Load Q&A page on page load
window.addEventListener('load', loadQAPage);
