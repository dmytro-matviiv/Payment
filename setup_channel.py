"""
Простий скрипт для встановлення Channel ID
"""
import sys
import io

# Виправлення кодування для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

print("="*60)
print("Налаштування Channel ID для Telegram бота")
print("="*60)
print("\nВиберіть спосіб отримання Channel ID:\n")
print("1. Якщо ваш канал публічний (має username):")
print("   Використайте @username каналу (наприклад: @my_channel)")
print("\n2. Якщо ваш канал приватний:")
print("   а) Додайте бота @DP_payment_bot в канал як адміністратора")
print("   б) Надішліть будь-яке повідомлення в канал")
print("   в) Відкрийте в браузері:")
print("      https://api.telegram.org/bot8456055614:AAEQcO_4iS3wnJ6ooZ-2BbgWsHSfFnWsPco/getUpdates")
print("   г) Знайдіть 'chat':{'id': -1001234567890} в JSON")
print("\n3. Використайте бота @userinfobot:")
print("   Перешліть повідомлення з каналу боту @userinfobot")
print("="*60)

channel_id = input("\nВведіть Channel ID або @username каналу: ").strip()

if channel_id:
    # Оновлюємо config.py
    try:
        with open('config.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Замінюємо значення TELEGRAM_CHANNEL_ID
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('TELEGRAM_CHANNEL_ID'):
                # Зберігаємо коментар якщо є
                if '#' in line:
                    comment = ' ' + line.split('#', 1)[1]
                else:
                    comment = ''
                lines[i] = f'TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "{channel_id}"){comment}'
                break
        
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print(f"\n✅ Channel ID встановлено: {channel_id}")
        print("Тепер можна запускати бота: python bot.py")
        
    except Exception as e:
        print(f"\n❌ Помилка: {e}")
        print("\nВстановіть Channel ID вручну в config.py:")
        print(f'TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "{channel_id}")')
else:
    print("\n⚠️  Channel ID не введено")

