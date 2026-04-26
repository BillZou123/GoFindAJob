from backend import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(db.Model):
    """User model for storing user account information"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    analyses = db.relationship('ResumeAnalysis', backref='user', lazy=True, cascade='all, delete-orphan')
    job_qas = db.relationship('JobQA', backref='user', lazy=True, cascade='all, delete-orphan')
    applied_jobs = db.relationship('AppliedJob', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }


class ResumeAnalysis(db.Model):
    """ResumeAnalysis model for storing resume analysis results"""
    __tablename__ = 'resume_analyses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_post = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, default=5)
    advice = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert analysis to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'job_post': self.job_post,
            'score': self.score,
            'advice': self.advice,
            'created_at': self.created_at.isoformat()
        }


class JobQA(db.Model):
    """JobQA model for storing company question and generated answers"""
    __tablename__ = 'job_qas'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_post = db.Column(db.Text, nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert job Q&A to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'job_post': self.job_post,
            'question': self.question,
            'answer': self.answer,
            'created_at': self.created_at.isoformat()
        }


class AppliedJob(db.Model):
    """AppliedJob model for tracking job applications"""
    __tablename__ = 'applied_jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200), nullable=False)
    job_post_link = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), default='Applied', nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert applied job to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'job_title': self.job_title,
            'company': self.company,
            'job_post_link': self.job_post_link,
            'location': self.location,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
