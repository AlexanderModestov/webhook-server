"""Webhook handler for Stripe payment notifications"""

import logging
from datetime import datetime
from aiogram import Router, Bot
from aiogram.types import Update
from fastapi import Request, HTTPException
from .stripe_service import StripeService
from bot.config import Config

# Create router for payment webhooks
payments_router = Router()
logger = logging.getLogger(__name__)

# Initialize Stripe service
stripe_service = StripeService(webhook_secret=getattr(Config, 'STRIPE_WEBHOOK_SECRET', ''))

async def handle_stripe_webhook(request: Request, bot: Bot, supabase_client):
    """Handle incoming Stripe webhook"""
    try:
        # Get raw body and signature
        body = await request.body()
        signature = request.headers.get('stripe-signature', '')

        # Verify webhook signature
        if not stripe_service.verify_webhook_signature(body, signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Parse webhook event
        event = stripe_service.parse_webhook_event(body.decode('utf-8'))
        if not event:
            logger.error("Failed to parse webhook event")
            raise HTTPException(status_code=400, detail="Invalid event data")

        # Check if this is a subscription payment
        if not stripe_service.is_subscription_payment(event):
            logger.info(f"Ignoring non-subscription event: {event.get('type')}")
            return {"status": "ignored"}

        # Extract customer information
        customer_info = stripe_service.extract_customer_info(event)
        if not customer_info:
            logger.error("Failed to extract customer info")
            raise HTTPException(status_code=400, detail="Invalid customer data")

        # Get Telegram user ID
        telegram_id = stripe_service.get_telegram_user_id(customer_info)
        if not telegram_id:
            logger.error("No Telegram ID found in metadata")
            raise HTTPException(status_code=400, detail="No Telegram ID found")

        # Log the payment event
        stripe_service.log_payment_event(event.get('type'), customer_info, telegram_id)

        # Process the successful payment
        await process_successful_payment(bot, supabase_client, telegram_id, customer_info, event)

        logger.info(f"Successfully processed payment for user {telegram_id}")
        return {"status": "success"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_successful_payment(bot: Bot, supabase_client, telegram_id: int, customer_info: dict, event: dict):
    """Process successful payment and update user subscription"""
    try:
        # Get user from database
        user = await supabase_client.get_user_by_telegram_id(telegram_id)
        if not user:
            logger.error(f"User {telegram_id} not found in database")
            return

        # Calculate subscription period
        subscription_period = stripe_service.calculate_subscription_period()

        # Update user subscription status (using existing fields for now)
        subscription_data = {
            'telegram_id': telegram_id,
            # Use notification field as premium status indicator for now
            'notification': True,  # This can represent premium status
        }

        # Update user in database
        await supabase_client.create_or_update_user(subscription_data)

        # Send success message to user
        await send_subscription_success_message(bot, telegram_id, supabase_client)

        # Notify admin about new subscription
        await notify_admin_new_subscription(bot, telegram_id, customer_info)

        logger.info(f"Updated subscription for user {telegram_id}")

    except Exception as e:
        logger.error(f"Error processing successful payment for user {telegram_id}: {e}")
        # Send error message to user
        await send_subscription_error_message(bot, telegram_id, supabase_client)

async def send_subscription_success_message(bot: Bot, telegram_id: int, supabase_client):
    """Send subscription success message to user"""
    try:
        # Get user language for localized message
        from bot.commands.commands import get_user_language_async, get_messages_class

        # Create a dummy message object for language detection
        class DummyUser:
            def __init__(self, telegram_id):
                self.id = telegram_id

        class DummyMessage:
            def __init__(self, telegram_id):
                self.from_user = DummyUser(telegram_id)

        dummy_message = DummyMessage(telegram_id)
        user_language = await get_user_language_async(dummy_message, supabase_client)
        messages_class = get_messages_class(user_language)

        # Send success message
        await bot.send_message(
            chat_id=telegram_id,
            text=messages_class.SUBSCRIBE_CMD["payment_success"],
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error sending subscription success message to {telegram_id}: {e}")

async def send_subscription_error_message(bot: Bot, telegram_id: int, supabase_client):
    """Send subscription error message to user"""
    try:
        # Get user language for localized message
        from bot.commands.commands import get_user_language_async, get_messages_class

        # Create a dummy message object for language detection
        class DummyUser:
            def __init__(self, telegram_id):
                self.id = telegram_id

        class DummyMessage:
            def __init__(self, telegram_id):
                self.from_user = DummyUser(telegram_id)

        dummy_message = DummyMessage(telegram_id)
        user_language = await get_user_language_async(dummy_message, supabase_client)
        messages_class = get_messages_class(user_language)

        # Send error message
        await bot.send_message(
            chat_id=telegram_id,
            text=messages_class.SUBSCRIBE_CMD["payment_error"],
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error sending subscription error message to {telegram_id}: {e}")

async def notify_admin_new_subscription(bot: Bot, telegram_id: int, customer_info: dict):
    """Notify admin about new subscription"""
    try:
        if hasattr(Config, 'TELEGRAM_ADMIN_ID') and Config.TELEGRAM_ADMIN_ID:
            admin_message = f"""🔥 **New Subscription!**

👤 **User:** {telegram_id}
💳 **Customer ID:** {customer_info.get('customer_id', 'N/A')}
💰 **Amount:** ${customer_info.get('amount', customer_info.get('amount_total', 0))}
🕐 **Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC

User now has premium access! 🚀"""

            await bot.send_message(
                chat_id=Config.TELEGRAM_ADMIN_ID,
                text=admin_message,
                parse_mode="Markdown"
            )

    except Exception as e:
        logger.error(f"Error notifying admin about new subscription: {e}")