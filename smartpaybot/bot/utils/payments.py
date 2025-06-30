# bot/utils/payments.py
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
