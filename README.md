# Webhook Server

Standalone webhook server for handling external service callbacks (Stripe payments, etc.).

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your actual values

# Run locally
python main.py
```

### Railway Deployment

1. **Connect GitHub Repository**
   - Go to Railway.app
   - Create new project from GitHub
   - Select this webhook-server folder

2. **Set Environment Variables**
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   TELEGRAM_BOT_TOKEN=your-bot-token
   STRIPE_SECRET_KEY=sk_your-stripe-secret-key
   STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret
   ```

3. **Deploy**
   - Railway will automatically detect and deploy
   - Get your domain: `https://your-app.up.railway.app`

## Endpoints

- `POST /webhook/stripe` - Stripe payment webhooks
- `GET /health` - Health check
- `GET /` - Service info

## Configure External Services

### Stripe Dashboard
1. Go to Stripe Dashboard > Webhooks
2. Add endpoint: `https://your-app.up.railway.app/webhook/stripe`
3. Select events: `checkout.session.completed`, `payment_intent.succeeded`
4. Copy webhook secret to environment variables

## Testing

```bash
# Test health endpoint
curl https://your-app.up.railway.app/health

# Test webhook (replace with your URL)
curl -X POST https://your-app.up.railway.app/webhook/stripe \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```