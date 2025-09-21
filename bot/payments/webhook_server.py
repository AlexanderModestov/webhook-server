"""FastAPI server for handling Stripe webhooks"""

import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from aiogram import Bot
from bot.config import Config
from bot.supabase_client import SupabaseClient
from .webhook_handler import handle_stripe_webhook

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Payment Webhook Server", version="1.0.0")

# Global variables for bot and supabase client
_bot_instance = None
_supabase_instance = None

def get_bot():
    """Get bot instance"""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    return _bot_instance

def get_supabase():
    """Get Supabase client instance"""
    global _supabase_instance
    if _supabase_instance is None:
        _supabase_instance = SupabaseClient(
            supabase_url=Config.SUPABASE_URL,
            supabase_key=Config.SUPABASE_KEY
        )
    return _supabase_instance

@app.post("/webhook/stripe")
async def stripe_webhook_endpoint(
    request: Request,
    bot: Bot = Depends(get_bot),
    supabase_client: SupabaseClient = Depends(get_supabase)
):
    """Stripe webhook endpoint"""
    try:
        result = await handle_stripe_webhook(request, bot, supabase_client)
        return JSONResponse(content=result, status_code=200)
    except HTTPException as e:
        logger.error(f"HTTP exception in webhook: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "payment-webhook"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Payment Webhook Server",
        "endpoints": {
            "stripe_webhook": "/webhook/stripe",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn

    # Run the webhook server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(Config.WEBHOOK_PORT if hasattr(Config, 'WEBHOOK_PORT') else 8000),
        log_level="info"
    )