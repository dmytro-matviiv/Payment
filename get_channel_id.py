"""
Утиліта для отримання Channel ID Telegram каналу
"""
import asyncio
import sys
import io
from telegram import Bot
from telegram.error import TelegramError
import config

# Виправлення кодування для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

async def get_channel_id():
    """Отримує ID каналу через бота"""
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    
    try:
        # Отримуємо інформацію про бота
        bot_info = await bot.get_me()
        print(f"🤖 Бот: @{bot_info.username}")
        print(f"📝 Ім'я: {bot_info.first_name}")
        print("\n" + "="*50)
        print("Інструкції:")
        print("1. Додайте бота в ваш канал як адміністратора")
        print("2. Надішліть будь-яке повідомлення в канал")
        print("3. Перешліть це повідомлення боту @userinfobot")
        print("4. Або використайте метод нижче:")
        print("="*50 + "\n")
        
        # Отримуємо оновлення
        updates = await bot.get_updates()
        
        if updates:
            print("Останні оновлення:")
            for update in updates[-5:]:  # Показуємо останні 5
                if update.channel_post or update.message:
                    chat = update.channel_post.chat if update.channel_post else update.message.chat
                    if chat.type == "channel":
                        print(f"\n channel ID: {chat.id}")
                        print(f"📝 Назва: {chat.title}")
                        print(f"📌 Username: @{chat.username}" if chat.username else "📌 Username: немає")
                        print("-" * 30)
        else:
            print("⚠️  Оновлення не знайдено.")
            print("\nАльтернативний спосіб:")
            print(f"1. Відкрийте: https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates")
            print("2. Знайдіть 'chat':{'id': ...} в JSON відповіді")
            print("3. Для публічних каналів можна використати @channel_name")
        
    except TelegramError as e:
        print(f"❌ Помилка: {e}")
        print("\nПеревірте правильність токену бота в config.py")

if __name__ == "__main__":
    asyncio.run(get_channel_id())

