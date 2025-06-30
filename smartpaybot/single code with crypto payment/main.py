# === main.py ===
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.config import settings
from bot.handlers import start, payments, crypto

async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_routers(start.router, payments.router, crypto.router)
    print("🤖 Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


# === bot/config.py ===
from pydantic import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    DOMAIN_URL: str
    ADMIN_ID: int
    BTC_WALLET_XPUB: str

    class Config:
        env_file = ".env"

settings = Settings()


# === .env ===
BOT_TOKEN=your_telegram_bot_token
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
DOMAIN_URL=https://yourdomain.com
ADMIN_ID=123456789
BTC_WALLET_XPUB=your_xpub_key_here


# === bot/handlers/start.py ===
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

router = Router()

@router.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("👋 Welcome to SmartPayBot!\nUse /pay to pay via Stripe or /paycrypto for BTC.")


# === bot/handlers/payments.py ===
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from bot.utils.payments import create_payment_link
from bot.utils.database import check_payment_status

router = Router()

@router.message(Command("pay"))
async def pay_cmd(message: Message):
    paid = check_payment_status(message.from_user.id)
    if paid:
        await message.answer("✅ You have already completed the payment.")
        return
    link = create_payment_link(user_id=message.from_user.id)
    await message.answer(f"💳 Click the link below to pay:\n{link}")


# === bot/handlers/crypto.py ===
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from bot.utils.crypto import assign_btc_address

router = Router()

@router.message(Command("paycrypto"))
async def pay_crypto_cmd(message: Message):
    address = assign_btc_address(message.from_user.id)
    await message.answer(f"💰 Send BTC to the address below.\nThis address is valid for 10 minutes:\n`{address}`", parse_mode="Markdown")


# === bot/utils/payments.py ===
import stripe
from bot.config import settings
from bot.utils.database import store_payment

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_payment_link(user_id: int) -> str:
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': 'Premium Access'},
                'unit_amount': 500,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url=f"{settings.DOMAIN_URL}/success?user_id={user_id}",
        cancel_url=f"{settings.DOMAIN_URL}/cancel",
        metadata={'user_id': str(user_id)},
    )
    store_payment(user_id, session.id)
    return session.url


# === bot/utils/crypto.py ===
import time
import secrets
from bot.utils.database import store_crypto_payment

btc_addresses = [f"btc_address_{i}" for i in range(1, 51)]  # Simulated static list of BTC addresses
assigned = {}  # user_id -> (address, timestamp)


def assign_btc_address(user_id: int) -> str:
    now = time.time()

    # Clear expired
    expired_users = [uid for uid, (_, t) in assigned.items() if now - t > 600]
    for uid in expired_users:
        del assigned[uid]

    if user_id in assigned:
        return assigned[user_id][0]

    for addr in btc_addresses:
        if addr not in [a for a, _ in assigned.values()]:
            assigned[user_id] = (addr, now)
            store_crypto_payment(user_id, addr)
            return addr

    return "❌ No BTC addresses available. Try again later."


# === bot/utils/database.py ===
import sqlite3

conn = sqlite3.connect("smartpaybot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS payments (
    user_id INTEGER PRIMARY KEY,
    stripe_session_id TEXT,
    paid INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS crypto_payments (
    user_id INTEGER PRIMARY KEY,
    btc_address TEXT,
    paid INTEGER DEFAULT 0,
    timestamp INTEGER
)
""")

conn.commit()

def store_payment(user_id: int, session_id: str):
    cursor.execute("REPLACE INTO payments (user_id, stripe_session_id, paid) VALUES (?, ?, 0)", (user_id, session_id))
    conn.commit()

def mark_paid(user_id: int):
    cursor.execute("UPDATE payments SET paid = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def check_payment_status(user_id: int) -> bool:
    cursor.execute("SELECT paid FROM payments WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row and row[0] == 1

def store_crypto_payment(user_id: int, btc_address: str):
    import time
    timestamp = int(time.time())
    cursor.execute("REPLACE INTO crypto_payments (user_id, btc_address, paid, timestamp) VALUES (?, ?, 0, ?)", (user_id, btc_address, timestamp))
    conn.commit()

def mark_crypto_paid(user_id: int):
    cursor.execute("UPDATE crypto_payments SET paid = 1 WHERE user_id = ?", (user_id,))
    conn.commit()


# === webhooks/stripe.py ===
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
            await client.post(
                f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": settings.ADMIN_ID,
                    "text": f"📥 User {user_id} completed a Stripe payment."
                }
            )

    return {"status": "success"}


# === requirements.txt ===
aiogram
fastapi
stripe
uvicorn
python-dotenv
httpx
