"""
Утиліта для отримання правильного Channel ID Telegram каналу
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
        bot_info = await bot.get_me()
        print(f"🤖 Бот: @{bot_info.username}")
        print("\n" + "="*60)
        print("ІНСТРУКЦІЇ ДЛЯ ОТРИМАННЯ CHANNEL ID:")
        print("="*60)
        print("\nВАЖЛИВО: Channel ID має бути негативним числом!")
        print("Наприклад: -1001234567890")
        print("\nСпособи отримання:")
        print("\n1. Через @userinfobot (найпростіше):")
        print("   - Надішліть будь-яке повідомлення в ваш канал")
        print("   - Перешліть це повідомлення боту @userinfobot")
        print("   - Він покаже Channel ID (негативне число)")
        print("\n2. Через веб-інтерфейс:")
        print("   - Додайте бота в канал як адміністратора")
        print("   - Надішліть повідомлення в канал")
        print("   - Відкрийте в браузері:")
        print(f"     https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/getUpdates")
        print("   - Знайдіть 'chat':{'id': -1001234567890}")
        print("     (ID має бути негативним!)")
        print("\n3. Якщо канал публічний:")
        print("   - Можна використати @username каналу")
        print("   - Наприклад: @my_channel")
        print("="*60)
        
        # Перевіряємо поточний Channel ID
        if config.TELEGRAM_CHANNEL_ID:
            current_id = config.TELEGRAM_CHANNEL_ID
            print(f"\n📌 Поточний Channel ID: {current_id}")
            
            # Перевіряємо чи це негативне число (канал) чи позитивне (особистий чат)
            try:
                id_num = int(current_id)
                if id_num > 0:
                    print("⚠️  УВАГА: Це позитивне число - це ID особистого чату з ботом!")
                    print("   Для каналу потрібен негативний ID (наприклад: -1001234567890)")
                elif id_num < 0:
                    print("✅ Це негативне число - правильно для каналу")
                else:
                    print("⚠️  ID не може бути нулем")
            except ValueError:
                # Можливо це username
                if current_id.startswith('@'):
                    print("✅ Це username каналу - правильно")
                else:
                    print("⚠️  Невідомий формат")
            
            # Перевіряємо доступ
            try:
                chat = await bot.get_chat(chat_id=current_id)
                print(f"\n📢 Канал знайдено: {chat.title}")
                print(f"   Тип: {chat.type}")
                if chat.type == "channel":
                    print("✅ Це канал - правильно!")
                elif chat.type == "private":
                    print("❌ Це особистий чат з ботом, а не канал!")
                    print("   Потрібно встановити ID каналу (негативне число)")
                else:
                    print(f"⚠️  Це {chat.type}, можливо не канал")
            except TelegramError as e:
                print(f"\n❌ Помилка доступу: {e}")
        
        # Отримуємо оновлення
        print("\n" + "="*60)
        print("ОСТАННІ ОНОВЛЕННЯ (якщо є):")
        print("="*60)
        updates = await bot.get_updates()
        
        if updates:
            channels_found = []
            for update in updates:
                chat = None
                if update.channel_post:
                    chat = update.channel_post.chat
                elif update.message:
                    chat = update.message.chat
                
                if chat and chat.type == "channel":
                    if chat.id not in [c['id'] for c in channels_found]:
                        channels_found.append({
                            'id': chat.id,
                            'title': chat.title,
                            'username': chat.username
                        })
            
            if channels_found:
                print("\nЗнайдені канали:")
                for ch in channels_found:
                    print(f"\n  📢 {ch['title']}")
                    print(f"     ID: {ch['id']}")
                    if ch['username']:
                        print(f"     Username: @{ch['username']}")
            else:
                print("\n⚠️  Канали в оновленнях не знайдено")
                print("   Надішліть повідомлення в канал після додавання бота")
        else:
            print("\n⚠️  Оновлення не знайдено")
            print("   Додайте бота в канал та надішліть повідомлення")
        
        print("\n" + "="*60)
        
    except TelegramError as e:
        print(f"❌ Помилка: {e}")

if __name__ == "__main__":
    asyncio.run(get_channel_id())

