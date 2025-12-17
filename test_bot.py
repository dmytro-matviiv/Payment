"""
Тестовий скрипт для перевірки роботи бота
"""
import asyncio
import sys
import io
from telegram import Bot
from telegram.error import TelegramError
import config
from bot import PaymentMonitor

# Виправлення кодування для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

async def test_bot():
    """Тестує роботу бота"""
    print("="*60)
    print("🧪 ТЕСТУВАННЯ БОТА")
    print("="*60)
    
    # Перевірка налаштувань
    print("\n1. Перевірка налаштувань...")
    print(f"   Telegram Bot Token: {'✅ Встановлено' if config.TELEGRAM_BOT_TOKEN else '❌ Не встановлено'}")
    print(f"   Channel ID: {config.TELEGRAM_CHANNEL_ID if config.TELEGRAM_CHANNEL_ID else '❌ Не встановлено'}")
    print(f"   Tronscan API Token: {'✅ Встановлено' if config.TRONSCAN_API_TOKEN else '❌ Не встановлено'}")
    print(f"   TRON Address: {config.TRON_ADDRESS}")
    
    # Перевірка підключення до Telegram
    print("\n2. Перевірка підключення до Telegram...")
    try:
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        bot_info = await bot.get_me()
        print(f"   ✅ Бот підключено: @{bot_info.username}")
    except Exception as e:
        print(f"   ❌ Помилка підключення: {e}")
        return
    
    # Перевірка доступу до каналу
    print("\n3. Перевірка доступу до каналу...")
    if config.TELEGRAM_CHANNEL_ID:
        try:
            chat = await bot.get_chat(chat_id=config.TELEGRAM_CHANNEL_ID)
            print(f"   ✅ Канал знайдено: {chat.title}")
            
            # Перевірка чи бот є адміністратором
            try:
                member = await bot.get_chat_member(
                    chat_id=config.TELEGRAM_CHANNEL_ID, 
                    user_id=bot_info.id
                )
                if member.status in ['administrator', 'creator']:
                    print(f"   ✅ Бот є адміністратором каналу")
                else:
                    print(f"   ⚠️  Бот не є адміністратором!")
            except Exception as e:
                print(f"   ⚠️  Не вдалося перевірити права: {e}")
            
            # Тестова відправка повідомлення
            print("\n4. Тестова відправка повідомлення...")
            try:
                test_message = "🧪 <b>Тестове повідомлення</b>\n\nЦе тестова перевірка роботи бота."
                await bot.send_message(
                    chat_id=config.TELEGRAM_CHANNEL_ID,
                    text=test_message,
                    parse_mode="HTML"
                )
                print("   ✅ Тестове повідомлення відправлено успішно!")
            except TelegramError as e:
                print(f"   ❌ Помилка відправки: {e}")
        except TelegramError as e:
            print(f"   ❌ Помилка доступу до каналу: {e}")
    else:
        print("   ⚠️  Channel ID не встановлено")
    
    # Перевірка Tronscan API
    print("\n5. Перевірка Tronscan API...")
    monitor = PaymentMonitor()
    transactions = monitor.get_recent_transactions()
    if transactions:
        print(f"   ✅ Отримано {len(transactions)} транзакцій")
        if len(transactions) > 0:
            latest = transactions[0]
            print(f"   Остання транзакція:")
            print(f"      Hash: {latest.get('hash', 'Невідомо')[:20]}...")
            print(f"      Timestamp: {latest.get('timestamp', 'Невідомо')}")
    else:
        print("   ⚠️  Транзакції не отримано (може бути нормально якщо транзакцій немає)")
    
    print("\n" + "="*60)
    print("✅ Тестування завершено!")
    print("="*60)
    print("\n📝 Інструкції для тестової транзакції:")
    print("1. Надішліть 1 USDT на адресу:", config.TRON_ADDRESS)
    print("2. Запустіть бота: python bot.py")
    print("3. Бот автоматично виявить транзакцію та відправить повідомлення в канал")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_bot())

