import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config():
    SECRET_KEY = 'vendorbridge-secret-key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'vendorbridge.sqlite')
    SQLALCHEMY_TRACK_MODIFICATIONS = False