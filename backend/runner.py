from flask import Flask
from api import api_v1
from config import SECRET_KEY
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

if __name__ == "__main__":
    app.register_blueprint(api_v1)
    app.run()