// Auto-Fill Application Page Script

function navigateTo(page) {
    window.location.href = '/pages/' + page;
}

document.addEventListener('DOMContentLoaded', async function() {
    // Check authentication first
    try {
        const user = await getCurrentUser();
        if (!user) {
            window.location.href = '/';
            return;
        }
        
        // Load username from user object
        if (user.username) {
            document.getElementById('username').textContent = user.username;
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/';
        return;
    }

    // Handle form submission
    const form = document.getElementById('autofillForm');
    if (form) {
        console.log('✓ Form found, attaching submit handler');
        form.addEventListener('submit', handleAutofillSubmit);
    } else {
        console.error('✗ Form with id "autofillForm" not found!');
    }

    // Prevent file input clearing on form submission
    const resumeInput = document.getElementById('resumeFile');
    if (resumeInput) {
        // Store the DataTransfer object when a file is selected
        resumeInput.addEventListener('change', function(e) {
            window.selectedResumeFile = this.files[0];
            window.selectedResumeDataTransfer = e.dataTransfer;
            console.log('Resume file stored:', this.files[0]?.name);
        });
    }
});

async function handleAutofillSubmit(e) {
    e.preventDefault();
    console.log('Form submitted!');

    const jobLink = document.getElementById('jobLink').value.trim();
    const resumeFile = document.getElementById('resumeFile').files[0] || window.selectedResumeFile;
    const firstName = document.getElementById('firstName').value.trim();
    const lastName = document.getElementById('lastName').value.trim();
    const email = document.getElementById('email').value.trim();
    const phone = document.getElementById('phone').value.trim();

    console.log('Form values:', { jobLink, resumeFile: resumeFile?.name, firstName, lastName, email, phone });

    // Validation
    if (!jobLink) {
        showError('Please provide a LinkedIn job link');
        return;
    }

    if (!resumeFile) {
        showError('Please upload a resume');
        return;
    }

    // Validate job link
    if (!jobLink.includes('linkedin.com') || !jobLink.includes('/jobs/view/')) {
        showError('Please provide a valid LinkedIn job link');
        return;
    }

    // Validate file size (max 10MB)
    if (resumeFile.size > 10 * 1024 * 1024) {
        showError('Resume file is too large (max 10MB)');
        return;
    }

    // Show loading state
    showLoading(true);
    hideMessages();

    try {
        // Create FormData for file upload
        const formData = new FormData();
        formData.append('job_link', jobLink);
        formData.append('resume', resumeFile);
        if (firstName) formData.append('first_name', firstName);
        if (lastName) formData.append('last_name', lastName);
        if (email) formData.append('email', email);
        if (phone) formData.append('phone', phone);

        console.log('📤 Sending request to /api/autofill-application');
        // Call backend API
        const response = await fetch('http://localhost:5001/api/autofill-application', {
            method: 'POST',
            body: formData,
            credentials: 'include'  // Important: send session cookies
        });

        console.log('📥 Response status:', response.status);

        let data;
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            data = await response.json();
        } else {
            // If not JSON, it's likely an error page
            const text = await response.text();
            console.error('Unexpected response:', text);
            throw new Error('Server error: ' + response.statusText);
        }

        console.log('📦 Response data:', data);

        if (!response.ok) {
            throw new Error(data.error || 'Failed to start auto-fill process');
        }

        // Success
        showLoading(false);
        showSuccess('Application auto-fill started! The browser will open and fill out the form. Please keep it open.');

        // Optional: Poll for status updates
        if (data.task_id) {
            console.log('📊 Polling for status updates with task_id:', data.task_id);
            pollAutofillStatus(data.task_id);
        }

        // Restore the resume file to the input using DataTransfer API
        // Note: Due to browser security, we can't directly set file inputs,
        // but we store the file globally so it persists
        setTimeout(() => {
            const resumeInput = document.getElementById('resumeFile');
            if (resumeInput && window.selectedResumeFile) {
                const dt = new DataTransfer();
                dt.items.add(window.selectedResumeFile);
                resumeInput.files = dt.files;
                console.log('Resume file restored to input');
            }
        }, 100);

    } catch (error) {
        showLoading(false);
        console.error('❌ Error:', error);
        showError(error.message || 'An error occurred. Please try again.');
    }
}

async function pollAutofillStatus(taskId) {
    const maxAttempts = 60; // Poll for up to 5 minutes
    let attempts = 0;

    const pollInterval = setInterval(async () => {
        attempts++;

        if (attempts > maxAttempts) {
            clearInterval(pollInterval);
            hideProgress();
            return;
        }

        try {
            const response = await fetch(`http://localhost:5001/api/autofill-status/${taskId}`, {
                credentials: 'include'  // Important: send session cookies
            });
            const data = await response.json();

            if (data.status === 'completed') {
                clearInterval(pollInterval);
                showSuccess(`✓ Application submitted! Applied to: ${data.job_title}`);
                hideProgress();
            } else if (data.status === 'failed') {
                clearInterval(pollInterval);
                showError(`Application failed: ${data.error}`);
                hideProgress();
            } else {
                // Update progress
                showProgress(data.current_step, data.total_steps, data.message);
            }
        } catch (error) {
            console.error('Error polling status:', error);
        }
    }, 5000); // Poll every 5 seconds
}

function showLoading(show) {
    const spinner = document.getElementById('loadingSpinner');
    const btn = document.querySelector('.autofill-btn');

    if (show) {
        spinner.classList.remove('hidden');
        btn.disabled = true;
    } else {
        spinner.classList.add('hidden');
        btn.disabled = false;
    }
}

function showSuccess(message) {
    const msgDiv = document.getElementById('successMessage');
    const msgText = document.getElementById('successText');
    msgText.textContent = message;
    msgDiv.classList.remove('hidden');
}

function showError(message) {
    const msgDiv = document.getElementById('errorMessage');
    const msgText = document.getElementById('errorText');
    msgText.textContent = message;
    msgDiv.classList.remove('hidden');
}

function hideMessages() {
    document.getElementById('successMessage').classList.add('hidden');
    document.getElementById('errorMessage').classList.add('hidden');
}

function showProgress(current, total, message) {
    const progressInfo = document.getElementById('progressInfo');
    const progressText = document.getElementById('progressText');
    const progressFill = document.getElementById('progressFill');

    progressInfo.classList.remove('hidden');
    progressText.textContent = message || `Processing step ${current} of ${total}...`;
    
    const percentage = total > 0 ? (current / total) * 100 : 0;
    progressFill.style.width = percentage + '%';
}

function hideProgress() {
    document.getElementById('progressInfo').classList.add('hidden');
}

function navigateHome() {
    window.location.href = '/';
}

async function handleLogout() {
    try {
        await fetch('/api/logout', { method: 'POST' });
        sessionStorage.clear();
        window.location.href = '/';
    } catch (error) {
        console.error('Logout error:', error);
    }
}
