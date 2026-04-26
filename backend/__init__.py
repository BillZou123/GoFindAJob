from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / '.env')

# Get the project root directory
ROOT_DIR = Path(__file__).parent.parent
FRONTEND_DIR = ROOT_DIR / 'frontend'
PAGES_DIR = FRONTEND_DIR / 'pages'
STYLES_DIR = FRONTEND_DIR / 'styles'
SCRIPTS_DIR = FRONTEND_DIR / 'scripts'

# Create Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gofindajob.db'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Enable CORS for frontend requests
CORS(app, supports_credentials=True, origins=['http://localhost:5001', 'http://localhost:8000'])

db = SQLAlchemy(app)

from backend import routes
