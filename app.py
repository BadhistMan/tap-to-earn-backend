import os
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config.from_object('config.Config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Import models after db is initialized
from models import User, Referral, Withdrawal, Tap, Upgrade

# Telegram authentication helper
def verify_telegram_data(data):
    if not data:
        return False
    
    # Parse the data string into a dictionary
    data_dict = {}
    pairs = data.split('&')
    hash_value = None
    
    for pair in pairs:
        key, value = pair.split('=', 1)
        if key == 'hash':
            hash_value = value
        else:
            data_dict[key] = value
    
    if not hash_value:
        return False
    
    # Create data check string
    data_pairs = []
    for key in sorted(data_dict.keys()):
        if key == 'user' or key == 'auth_date':
            data_pairs.append(f"{key}={data_dict[key]}")
        else:
            data_pairs.append(f"{key}={data_dict[key]}")
    
    data_check_string = '\n'.join(data_pairs)
    
    # Compute secret key
    secret_key = hashlib.sha256(app.config['BOT_TOKEN'].encode()).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    return computed_hash == hash_value

# API Endpoints
@app.route('/api/tap', methods=['POST'])
def handle_tap():
    data = request.json
    init_data = data.get('init_data')
    
    if not verify_telegram_data(init_data):
        return jsonify({'error': 'Invalid Telegram data'}), 401
    
    # Extract user data from initData
    init_data_dict = {}
    for pair in init_data.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            init_data_dict[key] = value
    
    user_data = json.loads(init_data_dict.get('user', '{}'))
    telegram_id = str(user_data.get('id'))
    
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Anti-cheat: Max 10 taps/sec (0.1s cooldown)
    now = datetime.utcnow()
    if user.last_tap and (now - user.last_tap).total_seconds() < 0.1:
        return jsonify({'error': 'Tap too fast! Try slower'}), 429
    
    # Record tap
    new_tap = Tap(user_id=user.id)
    db.session.add(new_tap)
    
    # Update coins and last tap time
    user.coins += user.tap_power
    user.last_tap = now
    db.session.commit()
    
    return jsonify({
        'coins': user.coins,
        'tap_power': user.tap_power
    })

@app.route('/api/upgrade', methods=['POST'])
def handle_upgrade():
    data = request.json
    init_data = data.get('init_data')
    
    if not verify_telegram_data(init_data):
        return jsonify({'error': 'Invalid Telegram data'}), 401
    
    # Extract user data from initData
    init_data_dict = {}
    for pair in init_data.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            init_data_dict[key] = value
    
    user_data = json.loads(init_data_dict.get('user', '{}'))
    telegram_id = str(user_data.get('id'))
    
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Calculate cost (exponential scaling)
    cost = 100 * (2 ** (user.tap_power - 1))
    
    if user.coins < cost:
        return jsonify({'error': f'Not enough coins! Need {cost}, have {user.coins}'}), 400
    
    # Perform upgrade
    user.coins -= cost
    new_power = user.tap_power + 1
    
    # Record upgrade
    new_upgrade = Upgrade(
        user_id=user.id,
        new_power_level=new_power,
        cost=cost
    )
    db.session.add(new_upgrade)
    
    user.tap_power = new_power
    db.session.commit()
    
    return jsonify({
        'tap_power': user.tap_power,
        'coins': user.coins
    })

@app.route('/api/daily', methods=['POST'])
def claim_daily_reward():
    data = request.json
    init_data = data.get('init_data')
    
    if not verify_telegram_data(init_data):
        return jsonify({'error': 'Invalid Telegram data'}), 401
    
    # Extract user data from initData
    init_data_dict = {}
    for pair in init_data.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            init_data_dict[key] = value
    
    user_data = json.loads(init_data_dict.get('user', '{}'))
    telegram_id = str(user_data.get('id'))
    
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    now = datetime.utcnow()
    
    # Check if daily reward already claimed
    if user.last_daily_claim:
        # Check if at least 24 hours have passed
        time_since_last = now - user.last_daily_claim
        if time_since_last < timedelta(hours=24):
            next_claim = user.last_daily_claim + timedelta(hours=24)
            return jsonify({
                'error': f'Daily reward already claimed! Next available: {next_claim.strftime("%Y-%m-%d %H:%M:%S")} UTC'
            }), 400
    
    # Claim reward
    user.coins += app.config['DAILY_REWARD']
    user.last_daily_claim = now
    db.session.commit()
    
    return jsonify({
        'coins': user.coins,
        'last_daily_claim': user.last_daily_claim.isoformat()
    })

@app.route('/api/referral', methods=['POST'])
def handle_referral():
    data = request.json
    init_data = data.get('init_data')
    referral_code = data.get('referral_code')
    
    if not verify_telegram_data(init_data):
        return jsonify({'error': 'Invalid Telegram data'}), 401
    
    # Extract user data from initData
    init_data_dict = {}
    for pair in init_data.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            init_data_dict[key] = value
    
    user_data = json.loads(init_data_dict.get('user', '{}'))
    telegram_id = str(user_data.get('id'))
    
    # Find existing user
    existing_user = User.query.filter_by(telegram_id=telegram_id).first()
    if existing_user:
        return jsonify({'error': 'User already registered'}), 400
    
    # Find referrer by code
    referrer = User.query.filter_by(referral_code=referral_code).first()
    if not referrer:
        return jsonify({'error': 'Invalid referral code'}), 400
    
    # Create new user
    new_user = User(
        telegram_id=telegram_id,
        username=user_data.get('username'),
        avatar_url=user_data.get('photo_url'),
        referral_code=str(uuid.uuid4())[:8].upper(),  # Generate unique referral code
        referrer_id=referrer.id
    )
    db.session.add(new_user)
    db.session.flush()  # Get new_user ID
    
    # Create referral record
    referral = Referral(
        referrer_id=referrer.id,
        referred_id=new_user.id
    )
    db.session.add(referral)
    
    # Reward both users
    referrer.coins += app.config['REFERRAL_BONUS']
    new_user.coins += app.config['REFERRAL_BONUS']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Referral successful! You both earned bonus coins',
        'coins': new_user.coins
    })

@app.route('/api/withdraw', methods=['POST'])
def handle_withdrawal():
    data = request.json
    init_data = data.get('init_data')
    method = data.get('method')
    address = data.get('address')
    
    if not verify_telegram_data(init_data):
        return jsonify({'error': 'Invalid Telegram data'}), 401
    
    # Extract user data from initData
    init_data_dict = {}
    for pair in init_data.split('&'):
        if '=' in pair:
            key, value = pair.split('=', 1)
            init_data_dict[key] = value
    
    user_data = json.loads(init_data_dict.get('user', '{}'))
    telegram_id = str(user_data.get('id'))
    
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check minimum balance
    if user.coins < app.config['WITHDRAWAL_MIN']:
        return jsonify({
            'error': f'Minimum {app.config["WITHDRAWAL_MIN"]} coins required for withdrawal'
        }), 400
    
    # Validate withdrawal method
    valid_methods = ['paypal', 'usdt', 'telebirr', 'bank']
    if method not in valid_methods:
        return jsonify({'error': 'Invalid withdrawal method'}), 400
    
    # Validate address
    if not address or len(address) < 3:
        return jsonify({'error': 'Invalid payment address'}), 400
    
    # Create withdrawal request
    withdrawal = Withdrawal(
        user_id=user.id,
        method=method,
        address=address,
        amount=user.coins
    )
    db.session.add(withdrawal)
    
    # Reset user's coins
    user.coins = 0
    db.session.commit()
    
    return jsonify({
        'message': 'Withdrawal request submitted successfully!',
        'coins': user.coins
    })

@app.route('/api/user/<telegram_id>', methods=['GET'])
def get_user(telegram_id):
    user = User.query.filter_by(telegram_id=telegram_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get referral count
    referral_count = Referral.query.filter_by(referrer_id=user.id).count()
    
    # Calculate next daily claim time
    next_daily_claim = None
    if user.last_daily_claim:
        next_daily_claim = (user.last_daily_claim + timedelta(hours=24)).isoformat()
    
    return jsonify({
        'telegram_id': user.telegram_id,
        'username': user.username,
        'avatar_url': user.avatar_url,
        'coins': user.coins,
        'tap_power': user.tap_power,
        'referral_code': user.referral_code,
        'referral_count': referral_count,
        'joined_at': user.joined_at.isoformat(),
        'last_daily_claim': user.last_daily_claim.isoformat() if user.last_daily_claim else None,
        'next_daily_claim': next_daily_claim
    })

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    # Get top 100 users by coins
    top_users = User.query.order_by(User.coins.desc()).limit(100).all()
    
    leaderboard = [{
        'username': user.username,
        'coins': user.coins,
        'tap_power': user.tap_power
    } for user in top_users]
    
    return jsonify(leaderboard)

@app.route('/')
def health_check():
    return jsonify({
        'status': 'active',
        'message': 'Tap to Earn API is running',
        'timestamp': datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])
