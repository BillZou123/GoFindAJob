async function loadWelcomePage() {
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
    document.getElementById('analyzeForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const resumeFile = document.getElementById('resumeFile').files[0];
        const jobPost = document.getElementById('jobPost').value;
        
        if (!resumeFile) {
            showError('Please select a resume file');
            return;
        }
        
        if (!jobPost.trim()) {
            showError('Please paste a job posting');
            return;
        }
        
        // Show loading
        document.getElementById('loadingSpinner').classList.remove('hidden');
        
        try {
            const formData = new FormData();
            formData.append('resume', resumeFile);
            formData.append('job_post', jobPost);
            
            const response = await fetch('http://localhost:5001/api/analyze-resume', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Analysis failed');
            }
            
            showSuccess('Resume analyzed successfully!');
            
            // Display current analysis result
            const analysis = data.analysis;
            const resultsList = document.getElementById('resultsList');
            resultsList.innerHTML = `
                <div class="result-item">
                    <div class="result-header">
                        <div class="score-badge score-${analysis.score}">
                            Score: ${analysis.score}/10
                        </div>
                        <span class="result-date">${new Date(analysis.created_at).toLocaleDateString()}</span>
                    </div>
                    <div class="result-advice">
                        <strong>Advice:</strong>
                        <p>${analysis.advice}</p>
                    </div>
                </div>
            `;
            document.getElementById('resultsSection').classList.remove('hidden');
            
            document.getElementById('analyzeForm').reset();
            
        } catch (error) {
            showError(error.message || 'Failed to analyze resume');
        } finally {
            document.getElementById('loadingSpinner').classList.add('hidden');
        }
    });
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

// Load welcome page on page load
window.addEventListener('load', loadWelcomePage);
