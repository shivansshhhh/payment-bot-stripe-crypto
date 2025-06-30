# bot/handlers/start.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart

router = Router()

@router.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("👋 Welcome to SmartPayBot!\nUse /pay to make a payment.")
