# webhooks/stripe.py
from fastapi import FastAPI, Request, Header
import stripe
from bot.config import settings
from bot.utils.database import mark_paid
import httpx

app = FastAPI()
stripe.api_key = settings.STRIPE_SECRET_KEY

@app.post("/webhook/stripe")
async def stripe_webhook(request: Request, stripe_signature: str = Header(...)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        print("❌ Stripe webhook error:", e)
        return {"status": "error"}

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = int(session['metadata']['user_id'])
        mark_paid(user_id)

        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": user_id,
                    "text": "✅ Your payment has been confirmed. Thank you!"
                }
            )
    return {"status": "success"}
