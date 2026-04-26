async function loadAppliedJobsPage() {
    try {
        const user = await getCurrentUser();
        if (user) {
            document.getElementById('username').textContent = user.username;
            loadAppliedJobs();
            setupFormHandler();
        } else {
            window.location.href = '/';
        }
    } catch (error) {
        showError('Connection error. Please refresh the page or log in again.');
    }
}

let allJobs = [];
const JOBS_PER_PAGE = 5;
let currentPage = 1;

async function loadAppliedJobs() {
    try {
        const response = await fetch('http://localhost:5001/api/applied-jobs', {
            method: 'GET',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to load applied jobs');
        }
        
        allJobs = await response.json();
        currentPage = 1;
        displayJobsPage();
    } catch (error) {
        showError('Failed to load applied jobs: ' + error.message);
    }
}

function displayJobsPage() {
    const startIdx = (currentPage - 1) * JOBS_PER_PAGE;
    const endIdx = startIdx + JOBS_PER_PAGE;
    const jobsToDisplay = allJobs.slice(startIdx, endIdx);
    
    const jobsList = document.getElementById('jobsList');
    const jobCount = document.getElementById('jobCount');
    
    jobCount.textContent = allJobs.length;
    
    if (allJobs.length === 0) {
        jobsList.innerHTML = '<p class="no-jobs">No applications yet. Add one to get started!</p>';
        document.getElementById('paginationControls').innerHTML = '';
        return;
    }
    
    jobsList.innerHTML = jobsToDisplay.map(job => createJobCard(job)).join('');
    updatePaginationControls();
}

function updatePaginationControls() {
    const totalPages = Math.ceil(allJobs.length / JOBS_PER_PAGE);
    const paginationControls = document.getElementById('paginationControls');
    
    if (totalPages <= 1) {
        paginationControls.innerHTML = '';
        return;
    }
    
    let paginationHTML = '<div class="pagination">';
    
    // Previous button
    if (currentPage > 1) {
        paginationHTML += `<button class="page-btn" onclick="goToPage(${currentPage - 1})">← Previous</button>`;
    }
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === currentPage) {
            paginationHTML += `<span class="page-number active">${i}</span>`;
        } else {
            paginationHTML += `<button class="page-number" onclick="goToPage(${i})">${i}</button>`;
        }
    }
    
    // Next button
    if (currentPage < totalPages) {
        paginationHTML += `<button class="page-btn" onclick="goToPage(${currentPage + 1})">Next →</button>`;
    }
    
    paginationHTML += '</div>';
    paginationControls.innerHTML = paginationHTML;
}

function goToPage(pageNum) {
    const totalPages = Math.ceil(allJobs.length / JOBS_PER_PAGE);
    if (pageNum >= 1 && pageNum <= totalPages) {
        currentPage = pageNum;
        displayJobsPage();
        // Scroll to top
        window.scrollTo(0, 0);
    }
}

function createJobCard(job) {
    const statusClass = `status-${job.status.toLowerCase().replace(/\s+/g, '-')}`;
    const updatedDate = new Date(job.updated_at).toLocaleDateString();
    
    return `
        <div class="job-card">
            <div class="job-header">
                <div class="job-title-company">
                    <h4>${escapeHtml(job.job_title)}</h4>
                    <p class="company">${escapeHtml(job.company)}</p>
                </div>
                <span class="status-badge ${statusClass}">${escapeHtml(job.status)}</span>
            </div>
            
            <div class="job-details">
                <div class="detail">
                    <span class="label">📍 Location:</span>
                    <span>${escapeHtml(job.location)}</span>
                </div>
                <div class="detail">
                    <span class="label">🔗 Link:</span>
                    <a href="${escapeHtml(job.job_post_link)}" target="_blank" rel="noopener noreferrer">View Job Post</a>
                </div>
                <div class="detail">
                    <span class="label">� Updated:</span>
                    <span>${updatedDate}</span>
                </div>
            </div>
            
            <div class="job-actions">
                <button class="edit-btn" onclick="openEditForm(${job.id}, '${escapeHtml(job.job_title)}', '${escapeHtml(job.company)}', '${escapeHtml(job.location)}', '${escapeHtml(job.job_post_link)}', '${escapeHtml(job.status)}')">Edit</button>
                <button class="delete-btn" onclick="deleteJob(${job.id})">Delete</button>
            </div>
        </div>
    `;
}

function setupFormHandler() {
    document.getElementById('jobForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = {
            job_title: document.getElementById('jobTitle').value,
            company: document.getElementById('company').value,
            location: document.getElementById('location').value,
            job_post_link: document.getElementById('jobPostLink').value,
            status: document.getElementById('status').value,
            notes: document.getElementById('notes').value
        };
        
        try {
            const response = await fetch('http://localhost:5001/api/applied-jobs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData),
                credentials: 'include'
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to add job');
            }
            
            showSuccess('Job application added successfully!');
            document.getElementById('jobForm').reset();
            toggleAddJobForm();
            loadAppliedJobs();
            
        } catch (error) {
            showError(error.message || 'Failed to add job');
        }
    });
}

function toggleAddJobForm() {
    const form = document.getElementById('addJobForm');
    form.classList.toggle('hidden');
}

function openEditForm(jobId, jobTitle, company, location, jobPostLink, status) {
    const editForm = document.getElementById('editJobForm');
    
    document.getElementById('editJobId').value = jobId;
    document.getElementById('editJobTitle').value = jobTitle;
    document.getElementById('editCompany').value = company;
    document.getElementById('editLocation').value = location;
    document.getElementById('editJobPostLink').value = jobPostLink;
    document.getElementById('editStatus').value = status;
    
    editForm.classList.remove('hidden');
    editForm.scrollIntoView({ behavior: 'smooth' });
}

function closeEditForm() {
    document.getElementById('editJobForm').classList.add('hidden');
}

async function submitEditForm(event) {
    event.preventDefault();
    
    const jobId = document.getElementById('editJobId').value;
    const formData = {
        job_title: document.getElementById('editJobTitle').value,
        company: document.getElementById('editCompany').value,
        location: document.getElementById('editLocation').value,
        job_post_link: document.getElementById('editJobPostLink').value,
        status: document.getElementById('editStatus').value
    };
    
    try {
        const response = await fetch(`http://localhost:5001/api/applied-jobs/${jobId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData),
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to update job');
        }
        
        showSuccess('Job application updated successfully!');
        closeEditForm();
        loadAppliedJobs();
        
    } catch (error) {
        showError(error.message || 'Failed to update job');
    }
}

async function deleteJob(jobId) {
    if (!confirm('Are you sure you want to delete this application?')) {
        return;
    }
    
    try {
        const response = await fetch(`http://localhost:5001/api/applied-jobs/${jobId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete job');
        }
        
        showSuccess('Job application deleted');
        loadAppliedJobs();
    } catch (error) {
        showError(error.message || 'Failed to delete job');
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
        await apiCall('/logout', 'POST');
        window.location.href = '/pages/home.html';
    } catch (error) {
        showError('Logout failed');
    }
}

function navigateHome() {
    window.location.href = '/pages/home.html';
}

window.addEventListener('load', loadAppliedJobsPage);
