import os
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from backend import app, db


class FrontendHandler(SimpleHTTPRequestHandler):
    """Custom handler for frontend static files"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='frontend', **kwargs)
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging"""
        pass


def run_frontend():
    """Run frontend server on port 8000"""
    server = HTTPServer(('localhost', 8000), FrontendHandler)
    print("🌐 Frontend server running on http://localhost:8000")
    server.serve_forever()


def run_backend():
    """Run backend server on port 5001"""
    with app.app_context():
        db.create_all()
    
    print("🔧 Backend server running on http://localhost:5001")
    app.run(host='localhost', port=5001, debug=True, use_reloader=False)


if __name__ == '__main__':
    print("🚀 Starting GoFindAJob...\n")
    
    # Start frontend in a separate thread
    frontend_thread = threading.Thread(target=run_frontend, daemon=True)
    frontend_thread.start()
    
    # Give frontend a moment to start
    time.sleep(1)
    
    # Run backend in main thread
    run_backend()

