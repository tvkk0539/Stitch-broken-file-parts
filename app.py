from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    DOWNLOAD_ROOT = os.environ.get('DOWNLOAD_ROOT', '/data/downloads')
    if not os.path.exists(DOWNLOAD_ROOT):
        try: os.makedirs(DOWNLOAD_ROOT)
        except: pass
    app.run(host='0.0.0.0', port=5000, debug=False)
