import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///game.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BOT_TOKEN = os.environ.get('BOT_TOKEN', 'your_bot_token_here')
    DAILY_REWARD = 1000
    REFERRAL_BONUS = 500
    WITHDRAWAL_MIN = 50000
