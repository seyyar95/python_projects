from flask import Flask

def create_app():
  app = Flask(__name__)
  app.config['SECRET'] = 'mysecret'
  return app