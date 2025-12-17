"""
Тест доступу до каналу @payment_trc20_001
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

async def test_channel():
    """Тестує доступ до каналу"""
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    channel_id = "@payment_trc20_001"
    
    print("="*60)
    print("🧪 ТЕСТУВАННЯ ДОСТУПУ ДО КАНАЛУ")
    print("="*60)
    print(f"Канал: {channel_id}")
    print()
    
    try:
        # Перевірка доступу до каналу
        chat = await bot.get_chat(chat_id=channel_id)
        print(f"✅ Канал знайдено: {chat.title}")
        print(f"   Тип: {chat.type}")
        print(f"   Username: @{chat.username}" if chat.username else "   Username: немає")
        
        # Перевірка чи бот є адміністратором
        bot_info = await bot.get_me()
        try:
            member = await bot.get_chat_member(
                chat_id=channel_id, 
                user_id=bot_info.id
            )
            print(f"\n📋 Статус бота в каналі: {member.status}")
            if member.status in ['administrator', 'creator']:
                print("✅ Бот є адміністратором каналу")
            else:
                print("⚠️  Бот НЕ є адміністратором!")
                print("   Додайте бота @DP_payment_bot в канал як адміністратора")
        except TelegramError as e:
            print(f"\n❌ Помилка перевірки прав: {e}")
            print("   Бот не має доступу до каналу")
        
        # Тестова відправка повідомлення
        print("\n📤 Тестова відправка повідомлення...")
        try:
            test_message = "🧪 <b>Тестове повідомлення</b>\n\nЦе перевірка доступу до каналу."
            await bot.send_message(
                chat_id=channel_id,
                text=test_message,
                parse_mode="HTML"
            )
            print("✅ Тестове повідомлення відправлено успішно в канал!")
        except TelegramError as e:
            print(f"❌ Помилка відправки: {e}")
            if "not a member" in str(e).lower():
                print("\n⚠️  БОТ НЕ ДОДАНО В КАНАЛ!")
                print("Інструкції:")
                print("1. Відкрийте канал @payment_trc20_001")
                print("2. Налаштування каналу → Адміністратори")
                print("3. Додайте бота @DP_payment_bot як адміністратора")
                print("4. Надайте права на 'Надсилання повідомлень'")
        
    except TelegramError as e:
        print(f"❌ Помилка доступу до каналу: {e}")
        if "chat not found" in str(e).lower():
            print("\n⚠️  Канал не знайдено!")
            print("   Перевірте правильність username: @payment_trc20_001")
            print("   Переконайтеся, що канал існує та публічний")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(test_channel())

