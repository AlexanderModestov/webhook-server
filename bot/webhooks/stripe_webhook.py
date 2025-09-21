import logging
import stripe
import json
from fastapi import FastAPI, Request, HTTPException
from bot.config import Config
from bot.supabase_client.client import SupabaseClient

# Initialize Stripe
stripe.api_key = Config.STRIPE_SECRET_KEY

# Initialize Supabase client
supabase_client = SupabaseClient(Config.SUPABASE_URL, Config.SUPABASE_KEY)

app = FastAPI()

@app.post("/stripe-webhook")
async def handle_stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        
        if not Config.STRIPE_WEBHOOK_SECRET:
            logging.error("STRIPE_WEBHOOK_SECRET not configured")
            raise HTTPException(status_code=400, detail="Webhook secret not configured")
        
        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, Config.STRIPE_WEBHOOK_SECRET
            )
        except ValueError as e:
            logging.error(f"Invalid payload: {e}")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError as e:
            logging.error(f"Invalid signature: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            await handle_successful_payment(session)
            
        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            await handle_payment_intent_success(payment_intent)
            
        else:
            logging.info(f"Unhandled event type: {event['type']}")
        
        return {"status": "success"}
        
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

async def handle_successful_payment(session):
    """Handle successful checkout session"""
    try:
        customer_email = session.get('customer_details', {}).get('email')
        customer_name = session.get('customer_details', {}).get('name')
        amount_total = session.get('amount_total', 0) / 100  # Convert from cents
        currency = session.get('currency', 'usd')
        
        # Get custom metadata if available (e.g., telegram_user_id)
        metadata = session.get('metadata', {})
        telegram_user_id = metadata.get('telegram_user_id')
        
        logging.info(f"Payment successful: {customer_email}, Amount: {amount_total} {currency}")
        
        # Update user payment status in database
        if telegram_user_id:
            # Find user by telegram ID and update payment status
            await supabase_client.update_user_payment_status(
                telegram_id=int(telegram_user_id),
                payment_status=True,
                payment_amount=amount_total,
                payment_currency=currency
            )
            
            # Send confirmation message to user
            from bot.main import bot
            await bot.send_message(
                chat_id=int(telegram_user_id),
                text=f"✅ Платеж успешно обработан!\n\n"
                     f"💰 Сумма: {amount_total} {currency.upper()}\n"
                     f"📧 Email: {customer_email}\n\n"
                     f"Спасибо за оплату! Ваш доступ к сервису активирован."
            )
        elif customer_email:
            # Find user by email if telegram_user_id not available
            await supabase_client.update_user_payment_status_by_email(
                email=customer_email,
                payment_status=True,
                payment_amount=amount_total,
                payment_currency=currency
            )
        
        logging.info(f"Successfully processed payment for user: {telegram_user_id or customer_email}")
        
    except Exception as e:
        logging.error(f"Error processing successful payment: {e}")

async def handle_payment_intent_success(payment_intent):
    """Handle successful payment intent"""
    try:
        amount = payment_intent.get('amount', 0) / 100
        currency = payment_intent.get('currency', 'usd')
        customer_id = payment_intent.get('customer')
        
        logging.info(f"Payment intent succeeded: Amount {amount} {currency}, Customer: {customer_id}")
        
        # Additional processing if needed
        
    except Exception as e:
        logging.error(f"Error processing payment intent: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)