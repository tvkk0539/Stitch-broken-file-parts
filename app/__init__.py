import threading
from flask import Flask
from app.core.job_manager import worker, job_manager
from app.routes import bp

def create_app():
    app = Flask(__name__, template_folder='../templates')
    app.register_blueprint(bp)

    # Start worker
    threading.Thread(target=worker, args=(job_manager,), daemon=True).start()

    return app
