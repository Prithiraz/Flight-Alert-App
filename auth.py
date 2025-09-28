#!/usr/bin/env python3
"""
Authentication and payment verification for Flight Alert App
"""

import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from typing import Optional
import stripe
from config import settings
from models import db, User, SubscriptionStatus

# Configure Stripe
stripe.api_key = settings.stripe_secret_key

def generate_token(user_id: int, email: str) -> str:
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def is_subscription_active(user: User) -> bool:
    """Check if user's subscription is active"""
    if user.subscription_status != SubscriptionStatus.ACTIVE:
        return False
    
    if user.subscription_end and user.subscription_end < datetime.now():
        # Update subscription status to expired
        db.update_user_subscription_status(user.id, SubscriptionStatus.EXPIRED)
        return False
    
    return True

def require_payment(f):
    """Decorator to require valid payment/subscription"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please provide Authorization header with valid token',
                'payment_info': {
                    'monthly_price': f'£{settings.monthly_price_gbp}',
                    'lifetime_price': f'£{settings.lifetime_price_gbp}',
                    'payment_endpoint': '/api/auth/subscribe'
                }
            }), 401
        
        try:
            token = auth_header.split(' ')[1]  # Bearer <token>
        except IndexError:
            return jsonify({
                'error': 'Invalid authorization header',
                'message': 'Format: Bearer <token>'
            }), 401
        
        # Verify token
        payload = verify_token(token)
        if not payload:
            return jsonify({
                'error': 'Invalid or expired token',
                'message': 'Please login again or purchase a subscription'
            }), 401
        
        # Get user
        user = db.get_user_by_email(payload['email'])
        if not user:
            return jsonify({
                'error': 'User not found',
                'message': 'Please register for a subscription'
            }), 401
        
        # Check subscription
        if not is_subscription_active(user):
            return jsonify({
                'error': 'Subscription required',
                'message': 'Your subscription has expired or is inactive',
                'subscription_status': user.subscription_status,
                'payment_info': {
                    'monthly_price': f'£{settings.monthly_price_gbp}',
                    'lifetime_price': f'£{settings.lifetime_price_gbp}',
                    'payment_endpoint': '/api/auth/subscribe'
                }
            }), 402  # Payment Required
        
        # Increment API call counter
        db.increment_api_calls(user.id)
        
        # Add user to Flask's g object for use in the route
        g.current_user = user
        
        return f(*args, **kwargs)
    
    return decorated_function

def create_stripe_checkout_session(email: str, subscription_type: str) -> dict:
    """Create Stripe checkout session"""
    try:
        # Determine price based on subscription type
        if subscription_type == 'lifetime':
            price_data = {
                'currency': 'gbp',
                'product_data': {
                    'name': 'Flight Alert App - Lifetime Access',
                    'description': 'Unlimited access to premium flight search and alerts'
                },
                'unit_amount': int(settings.lifetime_price_gbp * 100)  # Stripe uses cents
            }
            mode = 'payment'
        else:  # monthly
            price_data = {
                'currency': 'gbp',
                'product_data': {
                    'name': 'Flight Alert App - Monthly Subscription',
                    'description': 'Monthly access to premium flight search and alerts'
                },
                'unit_amount': int(settings.monthly_price_gbp * 100),
                'recurring': {'interval': 'month'}
            }
            mode = 'subscription'
        
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': price_data,
                'quantity': 1,
            }],
            mode=mode,
            success_url='http://localhost:8000/payment/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://localhost:8000/payment/cancel',
            customer_email=email,
            metadata={
                'subscription_type': subscription_type,
                'email': email
            }
        )
        
        return {
            'session_id': session.id,
            'checkout_url': session.url,
            'success': True
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'success': False
        }

def handle_stripe_webhook(payload: str, signature: str) -> dict:
    """Handle Stripe webhook events"""
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, settings.stripe_webhook_secret
        )
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            email = session['metadata']['email']
            subscription_type = session['metadata']['subscription_type']
            customer_id = session['customer']
            
            # Get or create user
            user = db.get_user_by_email(email)
            if not user:
                user = User(email=email)
                user = db.create_user(user)
            
            # Update subscription
            db.update_user_subscription(user.id, subscription_type, customer_id)
            
            return {'success': True, 'message': 'Subscription activated'}
        
        elif event['type'] == 'invoice.payment_failed':
            # Handle failed payment for recurring subscriptions
            customer_id = event['data']['object']['customer']
            # TODO: Update user subscription status to expired
            return {'success': True, 'message': 'Payment failure handled'}
        
        return {'success': True, 'message': 'Event processed'}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}