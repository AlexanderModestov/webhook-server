"""Stripe payment service for handling payment verification and webhooks"""

import logging
import json
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class StripeService:
    """Service for handling Stripe payment operations"""

    def __init__(self, webhook_secret: str):
        self.webhook_secret = webhook_secret
        self.logger = logging.getLogger(__name__)

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature"""
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Stripe signature format: "v1=<signature>"
            received_signature = signature.split('=')[1] if '=' in signature else signature

            return hmac.compare_digest(expected_signature, received_signature)
        except Exception as e:
            self.logger.error(f"Error verifying webhook signature: {e}")
            return False

    def parse_webhook_event(self, payload: str) -> Optional[Dict[str, Any]]:
        """Parse Stripe webhook event payload"""
        try:
            event = json.loads(payload)
            return event
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing webhook payload: {e}")
            return None

    def is_subscription_payment(self, event: Dict[str, Any]) -> bool:
        """Check if the event is a subscription payment"""
        event_type = event.get('type', '')
        return event_type in [
            'payment_intent.succeeded',
            'invoice.payment_succeeded',
            'checkout.session.completed'
        ]

    def extract_customer_info(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract customer information from webhook event"""
        try:
            event_type = event.get('type', '')
            data = event.get('data', {}).get('object', {})

            if event_type == 'checkout.session.completed':
                return {
                    'customer_id': data.get('customer'),
                    'payment_intent': data.get('payment_intent'),
                    'amount_total': data.get('amount_total', 0) / 100,  # Convert from cents
                    'metadata': data.get('metadata', {}),
                    'subscription_id': data.get('subscription')
                }
            elif event_type == 'payment_intent.succeeded':
                return {
                    'customer_id': data.get('customer'),
                    'payment_intent': data.get('id'),
                    'amount': data.get('amount', 0) / 100,  # Convert from cents
                    'metadata': data.get('metadata', {}),
                    'subscription_id': data.get('invoice', {}).get('subscription') if 'invoice' in data else None
                }
            elif event_type == 'invoice.payment_succeeded':
                return {
                    'customer_id': data.get('customer'),
                    'subscription_id': data.get('subscription'),
                    'amount': data.get('amount_paid', 0) / 100,  # Convert from cents
                    'metadata': data.get('metadata', {}),
                    'period_start': datetime.fromtimestamp(data.get('period_start', 0)),
                    'period_end': datetime.fromtimestamp(data.get('period_end', 0))
                }

            return None
        except Exception as e:
            self.logger.error(f"Error extracting customer info: {e}")
            return None

    def get_telegram_user_id(self, customer_info: Dict[str, Any]) -> Optional[int]:
        """Extract Telegram user ID from customer metadata"""
        try:
            metadata = customer_info.get('metadata', {})
            telegram_id = metadata.get('telegram_id') or metadata.get('telegram_user_id')

            if telegram_id:
                return int(telegram_id)

            return None
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error extracting telegram user ID: {e}")
            return None

    def calculate_subscription_period(self) -> Dict[str, datetime]:
        """Calculate subscription start and end dates for monthly subscription"""
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=30)  # 30-day subscription

        return {
            'start': start_date,
            'end': end_date
        }

    def log_payment_event(self, event_type: str, customer_info: Dict[str, Any], telegram_id: Optional[int]):
        """Log payment event for debugging"""
        self.logger.info(
            f"Payment event: {event_type}, "
            f"Telegram ID: {telegram_id}, "
            f"Customer: {customer_info.get('customer_id')}, "
            f"Amount: {customer_info.get('amount', customer_info.get('amount_total', 0))}"
        )