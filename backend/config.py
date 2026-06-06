import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config():
    SECRET_KEY = 'vendorbridge-secret-key'
    JWT_SECRET_KEY = 'vendorbridge-jwt-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'vendorbridge.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Email Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'happypatel30087@gmail.com'
    MAIL_PASSWORD = 'wqwmzjuambrcnfxb'
    
# Inject for utils.py to access without current_app
os.environ['MAIL_SERVER'] = Config.MAIL_SERVER
os.environ['MAIL_USERNAME'] = Config.MAIL_USERNAME
os.environ['MAIL_PASSWORD'] = Config.MAIL_PASSWORD