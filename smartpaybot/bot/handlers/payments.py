# bot/handlers/payments.py
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
