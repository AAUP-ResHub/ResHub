from flask import Flask
from extensions import db, migrate
from os import path

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev'  # Change this in production

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)

# Import models after db initialization
from models import User, Role

@app.route('/')
def index():
    return {'status': 'ok', 'message': 'ResHub API is running'}

if __name__ == '__main__':
    app.run(debug=True)
