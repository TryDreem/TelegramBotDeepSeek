import asyncio
import json
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")

if not all([TELEGRAM_BOT_TOKEN, API_KEY, MODEL]):
    raise ValueError("Не все ключи были загружены из .env файла")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

is_active = True

def chat_stream(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True
    }
    try:
        with requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            stream=True,
            timeout=90
        ) as response:
            if response.status_code != 200:
                return f"❌ Ошибка API: {response.status_code}"

            full_response = []
            for chunk in response.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8').replace('data: ', '')
                    try:
                        chunk_json = json.loads(chunk_str)
                        if "choices" in chunk_json:
                            content = chunk_json["choices"][0]["delta"].get("content", "")
                            if content:
                                full_response.append(content)
                    except json.JSONDecodeError:
                        pass

            return ''.join(full_response) if full_response else "❌ Ответ пуст, попробуйте снова."
    except requests.exceptions.Timeout:
        return "❌ Запрос занял слишком много времени. Попробуйте позже."


@dp.message(Command("stop"))
async def stop_bot(message: Message):
    global is_active
    is_active = False
    await message.answer("❌ Бот остановлен. Для запуска используйте команду /start.")


@dp.message(Command("start"))
async def start_bot(message: Message):
    global is_active
    is_active = True
    await message.answer("✅ Бот снова активен и готов работать.")


@dp.message()
async def handle_message(message: Message):
    if not is_active:
        await message.answer("❌ Бот остановлен. Используйте команду /start для активации.")
        return

    await message.answer("🤖 Думаю...")

    async def waiting_message():
        await asyncio.sleep(60)
        await message.answer("⏳ Пожалуйста, подождите, я все еще думаю...")

    waiting_task = asyncio.create_task(waiting_message())

    response = await asyncio.to_thread(chat_stream, message.text)

    waiting_task.cancel()

    if response:
        await message.answer(response)
    else:
        await message.answer("❌ Извините, попробуйте снова.")


async def main():

    await bot.set_my_commands([
        types.BotCommand(command="start", description="Запустить бота"),
        types.BotCommand(command="stop", description="Остановить бота"),
    ])

    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
