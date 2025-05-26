import os
from datetime import timedelta

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # MongoDB settings
    MONGO_URI = mongodb+srv://argulex_db:ArguLex123@argulexcluster.w4iopjs.mongodb.net/?retryWrites=true&w=majority&appName=ArguLexCluster
    
    # Application settings
    DEBUG = True
    
    # Flask configuration
    SESSION_TYPE = 'filesystem'
    
    # Application configuration
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes 