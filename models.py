from datetime import datetime
from . import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(80), unique=True, nullable=False)
    username = db.Column(db.String(50))
    avatar_url = db.Column(db.String(200))
    coins = db.Column(db.Integer, default=0)
    tap_power = db.Column(db.Integer, default=1)
    referral_code = db.Column(db.String(10), unique=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_daily_claim = db.Column(db.DateTime)
    last_tap = db.Column(db.DateTime)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    referrals = db.relationship('Referral', foreign_keys='Referral.referrer_id', backref='referrer', lazy=True)
    withdrawals = db.relationship('Withdrawal', backref='user', lazy=True)
    taps = db.relationship('Tap', backref='user', lazy=True)
    upgrades = db.relationship('Upgrade', backref='user', lazy=True)

class Referral(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    rewarded = db.Column(db.Boolean, default=False)

class Withdrawal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    method = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)

class Tap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Upgrade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    new_power_level = db.Column(db.Integer, nullable=False)
    cost = db.Column(db.Integer, nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
