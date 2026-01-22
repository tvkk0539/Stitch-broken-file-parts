import threading
from flask import Flask
from app.core.job_manager import worker, job_manager
from app.routes import bp

def create_app():
    # Set static_folder to ../static to match template_folder='../templates'
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.register_blueprint(bp)

    # Start worker
    threading.Thread(target=worker, args=(job_manager,), daemon=True).start()

    return app
