from flask import Flask
from app.routes import bp

def create_app():
    # Set static_folder to ../static to match template_folder='../templates'
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.register_blueprint(bp)

    # Note: Worker thread is now managed internally by JobManager's ThreadPoolExecutor

    return app
