import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///game.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get('DEBUG', 'False') == 'True'
    
    # Telegram configuration
    BOT_TOKEN = os.environ.get('BOT_TOKEN', '8246236846:AAHW_hPy5wALCrnjip1iX_Gr-MnBYZneTko')
    
    # Game configuration
    DAILY_REWARD = int(os.environ.get('DAILY_REWARD', '1000'))
    REFERRAL_BONUS = int(os.environ.get('REFERRAL_BONUS', '500'))
    WITHDRAWAL_MIN = int(os.environ.get('WITHDRAWAL_MIN', '50000'))
    
    # CORS configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
