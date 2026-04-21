from flask import request, jsonify, session
from backend import app, db
from backend.models import User, ResumeAnalysis
from backend.utils import call_agent
from datetime import datetime
import PyPDF2
import io
import json


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
