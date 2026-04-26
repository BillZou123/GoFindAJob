from flask import request, jsonify, session, send_from_directory, redirect
from backend import app, db, PAGES_DIR, STYLES_DIR, SCRIPTS_DIR
from backend.models import User, ResumeAnalysis, JobQA, AppliedJob
from backend.utils import call_agent, call_job_qa_agent
from backend.linkedin_autofiller import LinkedInAutoFiller
from backend import autofill_status
from datetime import datetime
import PyPDF2
import io
import json
import os
import subprocess
import threading
import asyncio
import logging

logger = logging.getLogger(__name__)


# Serve frontend pages at /pages/
@app.route('/pages/<filename>')
def serve_pages(filename):
    """Serve HTML pages"""
    return send_from_directory(PAGES_DIR, filename)


# Serve styles at /styles/
@app.route('/styles/<filename>')
def serve_styles(filename):
    """Serve CSS stylesheets"""
    return send_from_directory(STYLES_DIR, filename)


# Serve scripts at /scripts/
@app.route('/scripts/<filename>')
def serve_scripts(filename):
    """Serve JavaScript files"""
    return send_from_directory(SCRIPTS_DIR, filename)


@app.route('/')
def index():
    """Serve login/signup page at root, or redirect to home if authenticated"""
    if 'user_id' in session:
        return redirect('/pages/home.html')
    else:
        # Serve index.html for unauthenticated users
        frontend_dir = os.path.join(os.path.dirname(app.root_path), 'frontend')
        return send_from_directory(frontend_dir, 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'}), 200


@app.route('/api/signup', methods=['POST'])
def signup():
    """Register a new user"""
    data = request.get_json()
    
    # Validate input
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Missing required fields'}), 400
    
    username = data.get('username').strip()
    email = data.get('email').strip()
    password = data.get('password')
    
    # Validate password strength
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters long'}), 400
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409
    
    # Create new user
    try:
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Set session
        session['user_id'] = user.id
        session['username'] = user.username
        
        return jsonify({
            'message': 'User created successfully',
            'user': user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    
    # Validate input
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'error': 'Missing username or password'}), 400
    
    username = data.get('username').strip()
    password = data.get('password')
    
    # Find user
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Set session
    session['user_id'] = user.id
    session['username'] = user.username
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    }), 200


@app.route('/api/logout', methods=['POST'])
def logout():
    """Logout user"""
    session.clear()
    return jsonify({'message': 'Logout successful'}), 200


@app.route('/api/me', methods=['GET'])
def get_current_user():
    """Get current logged-in user"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    
    if not user:
        session.clear()
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200


@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID"""
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200


@app.route('/api/analyze-resume', methods=['POST'])
def analyze_resume():
    """Analyze resume against job posting"""
    app.logger.info("=== Starting resume analysis ===")
    user_id = session.get('user_id')
    app.logger.debug(f"User ID: {user_id}")
    
    if not user_id:
        app.logger.warning("Not authenticated")
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        app.logger.warning(f"User not found: {user_id}")
        return jsonify({'error': 'User not found'}), 404
    
    app.logger.info(f"User found: {user.username}")
    
    # Get job posting from form
    job_post = request.form.get('job_post')
    if not job_post:
        app.logger.warning("Missing job posting")
        return jsonify({'error': 'Missing job posting'}), 400
    
    app.logger.debug(f"Job posting length: {len(job_post)}")
    
    # Get PDF file
    if 'resume' not in request.files:
        app.logger.warning("No resume file provided")
        return jsonify({'error': 'No resume file provided'}), 400
    
    file = request.files['resume']
    app.logger.info(f"Resume file: {file.filename}")
    if file.filename == '':
        app.logger.warning("No file selected")
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.pdf'):
        app.logger.warning(f"Invalid file type: {file.filename}")
        return jsonify({'error': 'Only PDF files are supported'}), 400
    
    try:
        # Extract text from PDF
        app.logger.info("Extracting text from PDF...")
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
        resume_text = ""
        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            resume_text += text
            app.logger.debug(f"Extracted {len(text)} chars from page {i+1}")
        
        app.logger.info(f"Total extracted text: {len(resume_text)} chars")
        
        if not resume_text.strip():
            app.logger.warning("No text extracted from PDF")
            return jsonify({'error': 'Could not extract text from PDF'}), 400
        
        # Call analyzer agent
        try:
            app.logger.info("Calling analyzer agent...")
            prompt = f"""
Analyze this resume against the job posting:

RESUME:
{resume_text}

JOB POSTING:
{job_post}
"""
            user_context = {
                "username": user.username,
                "email": user.email
            }
            
            result = call_agent(str(user_id), prompt, user_context)
            app.logger.info(f"Agent returned: {result}")
            
            # Parse result
            try:
                analysis_data = json.loads(result)
                score = analysis_data.get('score', 5)
                advice = analysis_data.get('advice', '')
                app.logger.info(f"Parsed score: {score}, advice length: {len(advice)}")
            except Exception as parse_error:
                # Fallback if agent returns non-JSON
                app.logger.warning(f"Could not parse JSON: {parse_error}")
                score = 5
                advice = result
        except Exception as agent_error:
            app.logger.error(f"Agent error: {agent_error}", exc_info=True)
            score = 5
            advice = f"Error from analyzer: {str(agent_error)}"
        
        # Store in database
        app.logger.info(f"Storing analysis in database: score={score}")
        analysis = ResumeAnalysis(
            user_id=user_id,
            job_post=job_post,
            score=score,
            advice=advice
        )
        db.session.add(analysis)
        db.session.commit()
        app.logger.info(f"Analysis saved with ID: {analysis.id}")
        
        return jsonify({
            'message': 'Resume analyzed successfully',
            'analysis': analysis.to_dict()
        }), 201
        
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyses', methods=['GET'])
def get_user_analyses():
    """Get all analyses for current user"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    analyses = ResumeAnalysis.query.filter_by(user_id=user_id).order_by(ResumeAnalysis.created_at.desc()).all()
    
    return jsonify([analysis.to_dict() for analysis in analyses]), 200


@app.route('/api/job-qa', methods=['POST'])
def job_qa():
    """Answer company questions based on resume and job posting"""
    app.logger.info("=== Starting job Q&A ===")
    user_id = session.get('user_id')
    app.logger.debug(f"User ID: {user_id}")
    
    if not user_id:
        app.logger.warning("Not authenticated")
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get user
    user = User.query.get(user_id)
    if not user:
        app.logger.warning(f"User not found: {user_id}")
        return jsonify({'error': 'User not found'}), 404
    
    app.logger.info(f"User found: {user.username}")
    
    # Get job posting from form
    job_post = request.form.get('job_post')
    if not job_post:
        app.logger.warning("Missing job posting")
        return jsonify({'error': 'Missing job posting'}), 400
    
    # Get company's question from form
    question = request.form.get('question')
    if not question:
        app.logger.warning("Missing company question")
        return jsonify({'error': 'Missing company question'}), 400
    
    app.logger.debug(f"Job posting length: {len(job_post)}")
    app.logger.debug(f"Question length: {len(question)}")
    
    # Get PDF file
    if 'resume' not in request.files:
        app.logger.warning("No resume file provided")
        return jsonify({'error': 'No resume file provided'}), 400
    
    file = request.files['resume']
    app.logger.info(f"Resume file: {file.filename}")
    if file.filename == '':
        app.logger.warning("No file selected")
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.pdf'):
        app.logger.warning(f"Invalid file type: {file.filename}")
        return jsonify({'error': 'Only PDF files are supported'}), 400
    
    try:
        # Extract text from PDF
        app.logger.info("Extracting text from PDF...")
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
        resume_text = ""
        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            resume_text += text
            app.logger.debug(f"Extracted {len(text)} chars from page {i+1}")
        
        app.logger.info(f"Total extracted text: {len(resume_text)} chars")
        
        if not resume_text.strip():
            app.logger.warning("No text extracted from PDF")
            return jsonify({'error': 'Could not extract text from PDF'}), 400
        
        # Call Q&A agent
        try:
            app.logger.info("Calling job Q&A agent...")
            prompt = f"""
RESUME:
{resume_text}

JOB POSTING:
{job_post}

COMPANY'S QUESTION:
{question}

Please answer the company's question based on the candidate's resume and the job posting.
"""
            user_context = {
                "username": user.username,
                "email": user.email
            }
            
            result = call_job_qa_agent(str(user_id), prompt, user_context)
            app.logger.info(f"Agent returned: {result}")
            
            # Parse result
            try:
                qa_data = json.loads(result)
                answer = qa_data.get('answer', '')
                app.logger.info(f"Parsed answer length: {len(answer)}")
            except Exception as parse_error:
                # Fallback if agent returns non-JSON
                app.logger.warning(f"Could not parse JSON: {parse_error}")
                answer = result
        except Exception as agent_error:
            app.logger.error(f"Agent error: {agent_error}", exc_info=True)
            answer = f"Error from Q&A agent: {str(agent_error)}"
        
        # Store in database
        app.logger.info(f"Storing Q&A in database")
        qa = JobQA(
            user_id=user_id,
            job_post=job_post,
            question=question,
            answer=answer
        )
        db.session.add(qa)
        db.session.commit()
        app.logger.info(f"Q&A saved with ID: {qa.id}")
        
        return jsonify({
            'message': 'Question answered successfully',
            'qa': qa.to_dict()
        }), 201
        
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/job-qa-history', methods=['GET'])
def get_job_qa_history():
    """Get all job Q&A for current user"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    qas = JobQA.query.filter_by(user_id=user_id).order_by(JobQA.created_at.desc()).all()
    
    return jsonify([qa.to_dict() for qa in qas]), 200


@app.route('/api/applied-jobs', methods=['GET'])
def get_applied_jobs():
    """Get all applied jobs for current user"""
    user_id = session.get('user_id')
    app.logger.debug(f"Getting applied jobs for user: {user_id}")
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    jobs = AppliedJob.query.filter_by(user_id=user_id).order_by(AppliedJob.updated_at.desc()).all()
    app.logger.debug(f"Found {len(jobs)} applied jobs")
    
    return jsonify([job.to_dict() for job in jobs]), 200


@app.route('/api/applied-jobs', methods=['POST'])
def add_applied_job():
    """Add a new applied job"""
    user_id = session.get('user_id')
    app.logger.info("=== Adding applied job ===")
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['job_title', 'company', 'job_post_link', 'location']
    if not data or not all(data.get(field) for field in required_fields):
        return jsonify({'error': 'Missing required fields: job_title, company, job_post_link, location'}), 400
    
    try:
        job = AppliedJob(
            user_id=user_id,
            job_title=data.get('job_title'),
            company=data.get('company'),
            job_post_link=data.get('job_post_link'),
            location=data.get('location'),
            status=data.get('status', 'Applied'),
            notes=data.get('notes', '')
        )
        db.session.add(job)
        db.session.commit()
        app.logger.info(f"Applied job added with ID: {job.id}")
        
        return jsonify({
            'message': 'Applied job added successfully',
            'job': job.to_dict()
        }), 201
    except Exception as e:
        app.logger.error(f"Error adding applied job: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/applied-jobs/<int:job_id>', methods=['PUT'])
def update_applied_job(job_id):
    """Update an applied job"""
    user_id = session.get('user_id')
    app.logger.info(f"=== Updating applied job {job_id} ===")
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    job = AppliedJob.query.filter_by(id=job_id, user_id=user_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    data = request.get_json()
    
    try:
        if 'job_title' in data:
            job.job_title = data['job_title']
        if 'company' in data:
            job.company = data['company']
        if 'job_post_link' in data:
            job.job_post_link = data['job_post_link']
        if 'location' in data:
            job.location = data['location']
        if 'status' in data:
            job.status = data['status']
        if 'notes' in data:
            job.notes = data['notes']
        
        job.updated_at = datetime.utcnow()
        db.session.commit()
        app.logger.info(f"Applied job {job_id} updated")
        
        return jsonify({
            'message': 'Applied job updated successfully',
            'job': job.to_dict()
        }), 200
    except Exception as e:
        app.logger.error(f"Error updating applied job: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/applied-jobs/<int:job_id>', methods=['DELETE'])
def delete_applied_job(job_id):
    """Delete an applied job"""
    user_id = session.get('user_id')
    app.logger.info(f"=== Deleting applied job {job_id} ===")
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    job = AppliedJob.query.filter_by(id=job_id, user_id=user_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    try:
        db.session.delete(job)
        db.session.commit()
        app.logger.info(f"Applied job {job_id} deleted")
        
        return jsonify({'message': 'Applied job deleted successfully'}), 200
    except Exception as e:
        app.logger.error(f"Error deleting applied job: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/autofill-application', methods=['POST'])
def autofill_application():
    """Auto-fill LinkedIn Easy Apply form - async wrapper"""
    app.logger.info("=== Starting auto-fill application ===")
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    app.logger.info(f"User: {user.username}")
    
    # Validate job link
    job_link = request.form.get('job_link', '').strip()
    if not job_link:
        return jsonify({'error': 'Missing job link'}), 400
    
    if 'linkedin.com' not in job_link or '/jobs/view/' not in job_link:
        return jsonify({'error': 'Invalid LinkedIn job link'}), 400
    
    app.logger.info(f"Job link: {job_link}")
    
    # Validate and get resume file
    if 'resume' not in request.files:
        return jsonify({'error': 'No resume file provided'}), 400
    
    file = request.files['resume']
    if file.filename == '' or not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Only PDF files are supported'}), 400
    
    app.logger.info(f"Resume file: {file.filename}")
    
    # Get optional user info
    first_name = request.form.get('first_name', '').strip()
    last_name = request.form.get('last_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    
    try:
        # Create task ID and track progress
        task_id = autofill_status.create_task(job_link, user_id)
        app.logger.info(f"Created autofill task: {task_id}")
        
        # Prepare user info
        user_info = {
            "first_name": first_name or user.username.split()[0] if user.username else "User",
            "last_name": last_name or (user.username.split()[1] if len(user.username.split()) > 1 else ""),
            "email": email or user.email,
            "mobile_phone": phone or "",
            "country_code": "Canada (+1)",
            "phone_country_code": "Canada (+1)"
        }
        app.logger.info(f"User info: {user_info}")
        
        # Save resume to project resumes directory (not temp)
        from werkzeug.utils import secure_filename
        
        # Create resumes directory if it doesn't exist
        resumes_dir = os.path.join(os.path.dirname(app.root_path), 'resumes')
        os.makedirs(resumes_dir, exist_ok=True)
        app.logger.info(f"Resumes directory: {resumes_dir}")
        
        resume_path = os.path.join(resumes_dir, secure_filename(file.filename))
        file.save(resume_path)
        app.logger.info(f"Resume saved to: {resume_path}")
        
        # Start autofill in background thread
        def run_autofill():
            """Run the autofill process asynchronously"""
            try:
                # Create autofiller with status callback
                autofiller = LinkedInAutoFiller(
                    user_info=user_info,
                    use_ai=True,
                    resume_file_path=resume_path  # Pass the resume file path
                )
                
                # Set status callback
                autofiller.set_status_callback(
                    lambda step, msg: autofill_status.update_task_status(task_id, step, msg)
                )
                
                # Run in event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    success = loop.run_until_complete(autofiller.run(job_link, pause_seconds=60))
                    if success:
                        app.logger.info(f"Task {task_id} completed successfully")
                    else:
                        app.logger.warning(f"Task {task_id} failed")
                finally:
                    loop.close()
            except Exception as e:
                app.logger.error(f"Error in autofill task {task_id}: {e}", exc_info=True)
                autofill_status.update_task_status(task_id, "error", f"Error: {str(e)}")
            finally:
                # Note: Resume file is kept in resumes/ directory, not deleted
                pass
        
        # Start in background thread (non-blocking)
        thread = threading.Thread(target=run_autofill, daemon=True)
        thread.start()
        app.logger.info(f"Autofill thread started for task {task_id}")
        
        return jsonify({
            'message': 'Auto-fill process started',
            'task_id': task_id,
            'job_link': job_link,
            'status': 'started'
        }), 202  # 202 Accepted - processing in background
        
    except Exception as e:
        app.logger.error(f"Error in auto-fill: {e}", exc_info=True)
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/api/autofill-status/<task_id>', methods=['GET'])
def autofill_status_endpoint(task_id):
    """Get status of auto-fill task"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        status = autofill_status.get_task_status(task_id)
        
        if not status:
            return jsonify({'error': 'Task not found'}), 404
        
        # Verify user owns this task
        if status['user_id'] != user_id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        return jsonify(status), 200
        
    except Exception as e:
        app.logger.error(f"Error getting status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

