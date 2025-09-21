import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_ADMIN_ID = int(os.getenv('TELEGRAM_ADMIN_ID', '0'))
    
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-large')
    GPT_MODEL = os.getenv('GPT_MODEL', 'gpt-4o-mini')
    SEARCH_LIMIT = int(os.getenv('SEARCH_LIMIT', '5'))
    
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    RATE_LIMIT_REQUESTS_PER_DAY = int(os.getenv('RATE_LIMIT_REQUESTS_PER_DAY', '50'))
    WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://your-webapp-domain.com')
    CALENDLY_LINK = os.getenv('CALENDLY_LINK', 'https://calendly.com/your-calendar')
    STRIPE_PAYMENT_LINK = os.getenv('STRIPE_PAYMENT_LINK', 'https://buy.stripe.com/your-payment-link')
    STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')
    STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
    
    @classmethod
    def validate(cls):
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'OPENAI_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not getattr(cls, var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Validate URL formats
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        # Validate SUPABASE_URL
        if cls.SUPABASE_URL and not url_pattern.match(cls.SUPABASE_URL):
            raise ValueError(f"Invalid SUPABASE_URL format: '{cls.SUPABASE_URL}'. Expected format: https://your-project.supabase.co")
        
        # Validate other URLs if they're not default placeholders
        urls_to_check = [
            ('WEBAPP_URL', cls.WEBAPP_URL),
            ('CALENDLY_LINK', cls.CALENDLY_LINK),
            ('STRIPE_PAYMENT_LINK', cls.STRIPE_PAYMENT_LINK)
        ]
        
        for var_name, url_value in urls_to_check:
            if url_value and 'your-' not in url_value and not url_pattern.match(url_value):
                raise ValueError(f"Invalid {var_name} format: '{url_value}'")
        
        return True