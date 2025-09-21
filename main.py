#!/usr/bin/env python3
"""
Webhook Server Entry Point for Railway Deployment
"""

import os
import uvicorn
from bot.payments.webhook_server import app

if __name__ == "__main__":
    # Railway automatically sets PORT environment variable
    port = int(os.getenv('PORT', 8000))
    host = os.getenv('HOST', '0.0.0.0')

    print(f"Starting webhook server on {host}:{port}")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )