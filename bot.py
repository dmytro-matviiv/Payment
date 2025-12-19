import asyncio
import time
import requests
import json
import os
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
import config

class PaymentMonitor:
    def __init__(self):
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        # Зберігаємо адресу в оригінальному форматі для API
        self.tron_address_original = config.TRON_ADDRESS
        # Для порівняння використовуємо upper case
        self.tron_address = config.TRON_ADDRESS.upper()
        self.api_token = config.TRONSCAN_API_TOKEN
        self.channel_id = config.TELEGRAM_CHANNEL_ID
        self.processed_txns_file = "processed_transactions.json"
        self.processed_txns = self.load_processed_txns()
        self.usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
    
    def load_processed_txns(self):
        """Завантажує список оброблених транзакцій"""
        if os.path.exists(self.processed_txns_file):
            try:
                with open(self.processed_txns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get("txns", []))
            except Exception as e:
                print(f"⚠️  Помилка завантаження: {e}")
        return set()
    
    def save_processed_txns(self):
        """Зберігає список оброблених транзакцій"""
        try:
            data = {
                "txns": list(self.processed_txns),
                "last_update": datetime.now().isoformat()
            }
            with open(self.processed_txns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Помилка збереження: {e}")
    
    def get_transactions(self):
        """Отримує останні TRC20 трансфери з Tronscan API"""
        # Спробуємо різні варіанти headers
        headers_variants = [
            {"TRON-PRO-API-KEY": self.api_token},
            {"TRON-PRO-API-KEY": self.api_token, "Content-Type": "application/json"},
            {}  # Без API ключа (може працювати для публічних даних)
        ]
        
        # Спробуємо різні endpoints та параметри
        endpoints_to_try = [
            {
                "url": "https://apilist.tronscan.org/api/transfer",
                "params": {
                    "address": self.tron_address_original,
                    "start": 0,
                    "limit": 50
                }
            },
            {
                "url": f"https://apilist.tronscan.org/api/account/{self.tron_address_original}/transactions/trc20",
                "params": {
                    "start": 0,
                    "limit": 50
                }
            },
            {
                "url": "https://apilist.tronscan.org/api/transfer",
                "params": {
                    "address": self.tron_address_original,
                    "limit": 50
                }
            }
        ]
        
        for headers in headers_variants:
            for endpoint_config in endpoints_to_try:
                url = endpoint_config["url"]
                params = endpoint_config["params"]
                
                try:
                    print(f"📡 Запит до API: {url}")
                    print(f"📋 Параметри: {params}")
                    if headers:
                        print(f"🔑 Headers: {list(headers.keys())}")
                    response = requests.get(url, headers=headers, params=params, timeout=15)
            
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Діагностика структури відповіді
                        if isinstance(data, dict):
                            print(f"📊 Структура відповіді: {list(data.keys())}")
                        
                        # Отримуємо список трансферів
                        transfers = []
                        if isinstance(data, dict):
                            if "data" in data:
                                transfers = data["data"]
                            elif "transfers" in data:
                                transfers = data["transfers"]
                        elif isinstance(data, list):
                            transfers = data
                        
                        if transfers and isinstance(transfers, list):
                            print(f"✅ Отримано {len(transfers)} трансферів")
                            # Показуємо приклад першої транзакції
                            if len(transfers) > 0:
                                first = transfers[0]
                                print(f"🔍 Приклад: hash={first.get('hash', 'N/A')[:16]}..., to={first.get('toAddress', 'N/A')[:20]}...")
                            return transfers
                        else:
                            print("⚠️  Трансфери не знайдено або невірний формат")
                            continue  # Спробуємо наступний варіант
                    elif response.status_code == 400:
                        print(f"⚠️  Помилка 400 з параметрами: {params}")
                        print(f"Відповідь: {response.text[:300]}")
                        continue  # Спробуємо наступний варіант
                    else:
                        print(f"❌ Помилка API: {response.status_code}")
                        print(f"Відповідь: {response.text[:300]}")
                        continue  # Спробуємо наступний варіант
                except Exception as e:
                    print(f"❌ Помилка запиту: {e}")
                    continue  # Спробуємо наступний варіант
        
        # Якщо всі варіанти не спрацювали
        print("❌ Всі варіанти параметрів не спрацювали")
        return []
    
    def is_usdt(self, txn):
        """Перевіряє чи це USDT TRC20 транзакція"""
        # Перевірка contract address
        contract = (
            txn.get("contractAddress") or 
            txn.get("contract_address") or 
            txn.get("tokenContractAddress") or 
            ""
        )
        if contract and contract.upper() == self.usdt_contract.upper():
            return True
        
        # Перевірка по символу та назві
        symbol = (txn.get("tokenSymbol") or txn.get("token_symbol") or txn.get("symbol") or "").upper()
        name = (txn.get("tokenName") or txn.get("token_name") or txn.get("name") or "").upper()
        
        if "USDT" in symbol or "USDT" in name:
            return True
        
        return False
    
    def get_amount_usdt(self, txn):
        """Обчислює суму транзакції в USDT"""
        try:
            # Отримуємо суму в різних форматах
            amount_raw = (
                txn.get("amount") or 
                txn.get("quant") or 
                txn.get("value") or 
                txn.get("amount_str") or 
                0
            )
            
            # Конвертуємо в число
            try:
                if isinstance(amount_raw, str):
                    amount_raw = float(amount_raw)
                else:
                    amount_raw = float(amount_raw) if amount_raw else 0
            except:
                amount_raw = 0
            
            if amount_raw <= 0:
                return 0
            
            # USDT TRC20 має 6 десяткових знаків
            # amount_raw в найменших одиницях (1 USDT = 1,000,000)
            amount = amount_raw / 1000000
            
            return amount
        except Exception as e:
            print(f"⚠️  Помилка обчислення суми: {e}")
            return 0
    
    def process_transactions(self, transactions):
        """Обробляє транзакції та повертає нові"""
        new_txns = []
        
        print(f"\n🔍 Обробка {len(transactions)} транзакцій...")
        
        for i, txn in enumerate(transactions):
            try:
                # Отримуємо hash
                txn_hash = (
                    txn.get("hash") or 
                    txn.get("transactionHash") or 
                    txn.get("txID") or 
                    ""
                )
                
                if not txn_hash:
                    if i < 5:  # Логуємо тільки перші 5 для діагностики
                        print(f"  ⚠️  Транзакція без hash, ключі: {list(txn.keys())[:5]}")
                    continue
                
                # Перевіряємо чи вже оброблена
                if txn_hash in self.processed_txns:
                    continue
                
                # Отримуємо адресу отримувача
                to_addr = (
                    txn.get("toAddress") or 
                    txn.get("transferToAddress") or 
                    txn.get("to") or 
                    txn.get("to_address") or 
                    ""
                )
                
                if to_addr:
                    to_addr = to_addr.upper()
                else:
                    if i < 5:
                        print(f"  ⚠️  Транзакція {txn_hash[:16]}... без адреси отримувача")
                    continue
                
                # Перевіряємо чи на нашу адресу
                if to_addr != self.tron_address:
                    continue
                
                # Перевіряємо чи це USDT
                if not self.is_usdt(txn):
                    if i < 5:
                        symbol = txn.get("tokenSymbol") or txn.get("token_symbol") or "N/A"
                        contract = txn.get("contractAddress") or txn.get("contract_address") or "N/A"
                        print(f"  ⚠️  Не USDT: {txn_hash[:16]}... symbol={symbol}, contract={contract[:20]}...")
                    continue
                
                # Обчислюємо суму
                amount_usdt = self.get_amount_usdt(txn)
                
                # Перевіряємо суму >= 1 USDT
                if amount_usdt < 1.0:
                    print(f"  ⚠️  Пропущено: {txn_hash[:16]}... сума {amount_usdt:.2f} USDT < 1 USDT")
                    # Позначаємо як оброблену
                    self.processed_txns.add(txn_hash)
                    continue
                
                # Знайдено нову транзакцію!
                print(f"  ✅ Нова транзакція: {txn_hash[:16]}... сума {amount_usdt:.2f} USDT")
                new_txns.append(txn)
                self.processed_txns.add(txn_hash)
            except Exception as e:
                print(f"  ❌ Помилка обробки транзакції: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"📊 Знайдено {len(new_txns)} нових транзакцій >= 1 USDT\n")
        return new_txns
    
    def format_message(self, txn):
        """Форматує повідомлення про транзакцію"""
        try:
            # Отримуємо дані
            txn_hash = (
                txn.get("hash") or 
                txn.get("transactionHash") or 
                txn.get("txID") or 
                ""
            )
            
            amount_usdt = self.get_amount_usdt(txn)
            
            from_addr = (
                txn.get("fromAddress") or 
                txn.get("transferFromAddress") or 
                txn.get("from") or 
                txn.get("from_address") or 
                "Невідомо"
            )
            
            to_addr = (
                txn.get("toAddress") or 
                txn.get("transferToAddress") or 
                txn.get("to") or 
                txn.get("to_address") or 
                self.tron_address
            )
            
            timestamp = (
                txn.get("timestamp") or 
                txn.get("block_timestamp") or 
                txn.get("time") or 
                0
            )
            
            try:
                timestamp = float(timestamp)
                date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
            except:
                date_str = "Невідомо"
            
            # Формуємо повідомлення
            message = f"💰 <b>Нова оплата отримана!</b>\n\n"
            message += f"📊 <b>Сума:</b> {amount_usdt:.2f} USDT\n"
            message += f"📥 <b>Отримано на:</b> <code>{to_addr}</code>\n"
            message += f"📤 <b>Відправлено з:</b> <code>{from_addr}</code>\n"
            message += f"🕐 <b>Час:</b> {date_str}\n"
            
            if txn_hash:
                message += f"🔗 <a href='https://tronscan.org/#/transaction/{txn_hash}'>Переглянути транзакцію</a>"
            
            return message
        except Exception as e:
            print(f"⚠️  Помилка форматування: {e}")
            return None
    
    async def send_message(self, text):
        """Відправляє повідомлення в канал"""
        try:
            if not self.channel_id:
                print("⚠️  Channel ID не встановлено!")
                return False
            
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=text,
                parse_mode="HTML",
                disable_web_page_preview=False
            )
            return True
        except TelegramError as e:
            print(f"❌ Помилка відправки: {e}")
            return False
    
    async def check_payments(self):
        """Перевіряє нові платежі"""
        print(f"\n{'='*60}")
        print(f"🔍 Перевірка платежів - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        # Отримуємо транзакції
        transactions = self.get_transactions()
        
        if not transactions:
            print("⚠️  Транзакції не отримано")
            return
        
        # Обробляємо транзакції
        new_txns = self.process_transactions(transactions)
        
        if new_txns:
            print(f"✅ Відправка {len(new_txns)} повідомлень...\n")
            
            for txn in new_txns:
                message = self.format_message(txn)
                if message:
                    success = await self.send_message(message)
                    if success:
                        print(f"✅ Повідомлення відправлено")
                    await asyncio.sleep(1)
            
            # Зберігаємо оброблені транзакції
            self.save_processed_txns()
        else:
            print("ℹ️  Нових платежів не знайдено")
    
    def show_last_transaction(self):
        """Показує останню транзакцію для перевірки"""
        print("\n" + "="*60)
        print("🔍 ТЕСТОВА ПЕРЕВІРКА: Остання транзакція")
        print("="*60)
        
        transactions = self.get_transactions()
        
        if not transactions or len(transactions) == 0:
            print("⚠️  Транзакції не отримано")
            print("="*60 + "\n")
            return
        
        # Беремо першу (останню) транзакцію
        last_txn = transactions[0]
        
        txn_hash = (
            last_txn.get("hash") or 
            last_txn.get("transactionHash") or 
            last_txn.get("txID") or 
            "N/A"
        )
        
        to_addr = (
            last_txn.get("toAddress") or 
            last_txn.get("transferToAddress") or 
            last_txn.get("to") or 
            last_txn.get("to_address") or 
            "N/A"
        )
        
        from_addr = (
            last_txn.get("fromAddress") or 
            last_txn.get("transferFromAddress") or 
            last_txn.get("from") or 
            last_txn.get("from_address") or 
            "N/A"
        )
        
        amount_raw = (
            last_txn.get("amount") or 
            last_txn.get("quant") or 
            last_txn.get("value") or 
            last_txn.get("amount_str") or 
            0
        )
        
        token_symbol = (
            last_txn.get("tokenSymbol") or 
            last_txn.get("token_symbol") or 
            last_txn.get("symbol") or 
            "N/A"
        )
        
        token_name = (
            last_txn.get("tokenName") or 
            last_txn.get("token_name") or 
            last_txn.get("name") or 
            "N/A"
        )
        
        contract = (
            last_txn.get("contractAddress") or 
            last_txn.get("contract_address") or 
            last_txn.get("tokenContractAddress") or 
            "N/A"
        )
        
        timestamp = (
            last_txn.get("timestamp") or 
            last_txn.get("block_timestamp") or 
            last_txn.get("time") or 
            0
        )
        
        # Обчислюємо суму в USDT
        amount_usdt = self.get_amount_usdt(last_txn)
        is_usdt_txn = self.is_usdt(last_txn)
        
        # Форматуємо дату
        try:
            timestamp = float(timestamp)
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
        except:
            date_str = "N/A"
        
        print(f"📋 Hash: {txn_hash}")
        print(f"📥 To: {to_addr}")
        print(f"📤 From: {from_addr}")
        print(f"💰 Amount (raw): {amount_raw}")
        print(f"💰 Amount (USDT): {amount_usdt:.6f} USDT")
        print(f"🪙 Token: {token_name} ({token_symbol})")
        print(f"📄 Contract: {contract}")
        print(f"🕐 Timestamp: {timestamp}")
        print(f"📅 Date: {date_str}")
        print(f"✅ Is USDT: {is_usdt_txn}")
        print(f"✅ To our address: {to_addr.upper() == self.tron_address}")
        print(f"✅ Amount >= 1 USDT: {amount_usdt >= 1.0}")
        print(f"✅ Already processed: {txn_hash in self.processed_txns}")
        
        if txn_hash != "N/A":
            print(f"\n🔗 Посилання: https://tronscan.org/#/transaction/{txn_hash}")
        
        print("="*60 + "\n")
    
    async def start(self):
        """Запускає бота"""
        print("="*60)
        print("🚀 Бот запущено!")
        print("="*60)
        print(f"📍 Адреса: {self.tron_address}")
        print(f"⏱️  Інтервал: {config.CHECK_INTERVAL} сек")
        print(f"📝 Оброблено: {len(self.processed_txns)} транзакцій")
        print("="*60)
        
        # Перевірка бота
        try:
            bot_info = await self.bot.get_me()
            print(f"🤖 Бот: @{bot_info.username}\n")
        except Exception as e:
            print(f"❌ Помилка бота: {e}\n")
            return
        
        # Перевірка каналу
        if self.channel_id:
            try:
                chat = await self.bot.get_chat(chat_id=self.channel_id)
                print(f"📢 Канал: {chat.title}")
                print(f"✅ Доступ підтверджено\n")
            except Exception as e:
                print(f"⚠️  Помилка каналу: {e}\n")
        
        # ТЕСТОВА ПЕРЕВІРКА: показуємо останню транзакцію
        self.show_last_transaction()
        
        # Відправляємо повідомлення про запуск
        startup_msg = (
            f"✅ <b>Бот запущено!</b>\n\n"
            f"📍 <b>Адреса:</b> <code>{self.tron_address}</code>\n"
            f"⏱️  <b>Інтервал:</b> {config.CHECK_INTERVAL} сек\n"
            f"🕐 <b>Час:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🔗 <a href='https://tronscan.org/#/address/{self.tron_address}/transfers'>Переглянути транзакції</a>"
        )
        await self.send_message(startup_msg)
        
        # Основний цикл
        while True:
            try:
                await self.check_payments()
            except Exception as e:
                print(f"❌ Помилка: {e}")
                import traceback
                traceback.print_exc()
            
            await asyncio.sleep(config.CHECK_INTERVAL)

async def main():
    monitor = PaymentMonitor()
    await monitor.start()

if __name__ == "__main__":
    asyncio.run(main())
