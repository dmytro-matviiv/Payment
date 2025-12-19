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
        self.tron_address = config.TRON_ADDRESS
        self.api_token = config.TRONSCAN_API_TOKEN
        self.channel_id = config.TELEGRAM_CHANNEL_ID
        self.processed_txns_file = "processed_transactions.json"
        self.processed_txns = self.load_processed_txns()  # Для уникнення дублікатів
        # USDT TRC20 contract address
        self.usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        # Встановлюємо timestamp на поточний час при запуску, щоб не обробляти старі транзакції
        self.last_checked_timestamp = int(time.time() * 1000)  # в мілісекундах
        self.is_first_run = True  # Прапорець першого запуску
    
    def load_processed_txns(self):
        """Завантажує список оброблених транзакцій з файлу"""
        if os.path.exists(self.processed_txns_file):
            try:
                with open(self.processed_txns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get("txns", []))
            except Exception as e:
                print(f"⚠️  Помилка завантаження оброблених транзакцій: {e}")
        return set()
    
    def save_processed_txns(self):
        """Зберігає список оброблених транзакцій у файл"""
        try:
            data = {
                "txns": list(self.processed_txns),
                "last_update": datetime.now().isoformat()
            }
            with open(self.processed_txns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Помилка збереження оброблених транзакцій: {e}")
        
    def get_recent_transactions(self):
        """Отримує останні трансфери токенів з Tronscan API"""
        # Спробуємо різні endpoints для transfers
        # Використовуємо endpoint для TRC20 токенів, який краще працює з USDT
        endpoints = [
            "https://apilist.tronscan.org/api/transfer?trc20=true",  # Спеціально для TRC20
            "https://apilist.tronscan.org/api/transfer",
            "https://apilist.tronscan.org/api/trc20/transfer",
            "https://apilist.tronscan.org/api/transfer/trc20"
        ]
        
        headers = {
            "TRON-PRO-API-KEY": self.api_token
        }
        
        for url in endpoints:
            try:
                # Для TRC20 endpoint використовуємо інші параметри
                if "trc20" in url.lower():
                    params = {
                        "address": self.tron_address,
                        "start": 0,
                        "limit": 100,  # Збільшуємо limit для TRC20
                        "sort": "-timestamp",
                        "trc20": "true"
                    }
                else:
                    params = {
                        "address": self.tron_address,
                        "start": 0,
                        "limit": 100,  # Збільшуємо limit
                        "sort": "-timestamp"
                    }
                
                print(f"📡 Запит до API: {url}")
                print(f"📋 Параметри: {params}")
                
                response = requests.get(url, headers=headers, params=params, timeout=10)
                
                print(f"📥 Статус відповіді: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"📊 Структура відповіді: keys = {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                    
                    # Спробуємо різні варіанти структури відповіді
                    transfers = []
                    if isinstance(data, dict):
                        if data.get("success") and "data" in data:
                            transfers = data["data"]
                        elif "data" in data:
                            transfers = data["data"]
                        elif "transfers" in data:
                            transfers = data["transfers"]
                        elif isinstance(data.get("data"), list):
                            transfers = data["data"]
                    elif isinstance(data, list):
                        transfers = data
                    
                    if isinstance(transfers, list) and len(transfers) > 0:
                        print(f"✅ Отримано трансферів: {len(transfers)}")
                        
                        # Логуємо перший трансфер для діагностики
                        print(f"🔍 Приклад першого трансферу (ключі): {list(transfers[0].keys()) if isinstance(transfers[0], dict) else 'not a dict'}")
                        first_transfer = transfers[0]
                        print(f"   Hash: {first_transfer.get('hash') or first_transfer.get('transactionHash') or first_transfer.get('txID') or 'N/A'}")
                        print(f"   To: {first_transfer.get('toAddress') or first_transfer.get('transferToAddress') or first_transfer.get('to') or first_transfer.get('to_address') or 'N/A'}")
                        print(f"   From: {first_transfer.get('fromAddress') or first_transfer.get('transferFromAddress') or first_transfer.get('from') or first_transfer.get('from_address') or 'N/A'}")
                        print(f"   Amount: {first_transfer.get('amount') or first_transfer.get('quant') or first_transfer.get('value') or first_transfer.get('amount_str') or 'N/A'}")
                        print(f"   Token: {first_transfer.get('tokenName') or first_transfer.get('token_name') or first_transfer.get('name') or first_transfer.get('token') or 'N/A'}")
                        print(f"   Symbol: {first_transfer.get('tokenSymbol') or first_transfer.get('token_symbol') or first_transfer.get('symbol') or 'N/A'}")
                        print(f"   Contract: {first_transfer.get('contractAddress') or first_transfer.get('contract_address') or first_transfer.get('tokenContractAddress') or 'N/A'}")
                        print(f"   Timestamp: {first_transfer.get('timestamp') or first_transfer.get('block_timestamp') or first_transfer.get('time') or 'N/A'}")
                        
                        return transfers
                    else:
                        print(f"⚠️  Endpoint {url} повернув порожній список, спробуємо наступний...")
                        continue
                else:
                    print(f"⚠️  Endpoint {url} повернув статус {response.status_code}, спробуємо наступний...")
                    print(f"📄 Відповідь: {response.text[:200]}")
                    continue
            except Exception as e:
                print(f"⚠️  Помилка при запиті до {url}: {e}")
                continue
        
        print(f"❌ Всі endpoints не спрацювали")
        return []
    
    def format_startup_message(self):
        """Форматує повідомлення про запуск бота"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"✅ <b>Бот успішно запущено!</b>\n\n"
            message += f"🤖 <b>Моніторинг активний</b>\n"
            message += f"📍 <b>Адреса:</b> <code>{self.tron_address}</code>\n"
            message += f"⏱️  <b>Інтервал перевірки:</b> {config.CHECK_INTERVAL} сек\n"
            message += f"🕐 <b>Час запуску:</b> {current_time}\n"
            message += f"🔗 <a href='https://tronscan.org/#/address/{self.tron_address}'>Переглянути адресу</a>"
            return message
        except Exception as e:
            print(f"Помилка форматування повідомлення про запуск: {e}")
            return None
    
    def convert_to_usdt(self, amount, token_name, token_symbol=None):
        """Конвертує суму в USDT"""
        try:
            token_name_upper = (token_name or "").upper()
            token_symbol_upper = (token_symbol or "").upper()
            
            # Якщо це вже USDT
            if "USDT" in token_name_upper or "USDT" in token_symbol_upper:
                return amount, "USDT"
            
            # Якщо це TRX, конвертуємо в USDT (приблизний курс 1 TRX ≈ 0.1 USDT)
            # Використовуємо API для отримання актуального курсу
            if token_name_upper == "TRX" or token_name_upper == "TRON":
                usdt_amount = self.convert_trx_to_usdt(amount)
                return usdt_amount, "USDT"
            
            # Для інших токенів спробуємо конвертувати через TRX
            # Якщо не вдалося визначити курс, показуємо як є
            # Для більшості випадків це будуть TRX транзакції
            return amount, token_name
            
        except Exception as e:
            print(f"Помилка конвертації в USDT: {e}")
            return amount, token_name or "USDT"
    
    def convert_trx_to_usdt(self, trx_amount):
        """Конвертує TRX в USDT за актуальним курсом"""
        try:
            # Отримуємо курс TRX/USDT з CoinGecko API (безкоштовний)
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "tron",
                "vs_currencies": "usdt"
            }
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if "tron" in data and "usdt" in data["tron"]:
                    rate = data["tron"]["usdt"]
                    return trx_amount * rate
            
            # Якщо API не працює, використовуємо приблизний курс
            # 1 TRX ≈ 0.1 USDT (буде оновлюватися)
            approximate_rate = 0.1
            return trx_amount * approximate_rate
            
        except Exception as e:
            print(f"Помилка отримання курсу TRX/USDT: {e}, використовую приблизний курс")
            # Приблизний курс як fallback
            return trx_amount * 0.1
    
    def format_transaction_message(self, txn):
        """Форматує повідомлення про транзакцію"""
        try:
            # Отримуємо деталі транзакції - спробуємо різні варіанти назв полів
            amount_raw = (txn.get("amount") or 
                         txn.get("quant") or 
                         txn.get("value") or 
                         txn.get("amount_str") or
                         0)
            
            # Конвертуємо в число якщо потрібно
            try:
                if isinstance(amount_raw, str):
                    amount_raw = float(amount_raw)
                else:
                    amount_raw = float(amount_raw) if amount_raw else 0
            except (ValueError, TypeError):
                amount_raw = 0
            
            token_name = (txn.get("tokenName") or 
                         txn.get("token_name") or 
                         txn.get("name") or 
                         "TRX")
            token_name = token_name or "TRX"
            
            token_symbol = (txn.get("tokenSymbol") or 
                           txn.get("token_symbol") or 
                           txn.get("symbol") or 
                           "")
            token_symbol = token_symbol or ""
            
            # Визначаємо чи це USDT токен (TRC20)
            # USDT TRC20 має contract address або можна визначити по назві
            is_usdt = False
            if "USDT" in (token_name or "").upper() or "USDT" in (token_symbol or "").upper():
                is_usdt = True
                # USDT TRC20 має 6 десяткових знаків
                if amount_raw > 0:
                    amount = amount_raw / 1000000  # 1 USDT = 1,000,000 (6 zeros)
                else:
                    amount = 0
            else:
                # Для TRX та інших токенів конвертуємо з sun (1 TRX = 1,000,000 sun)
                if amount_raw > 0:
                    amount = amount_raw / 1000000
                else:
                    amount = 0
            
            # Конвертуємо все в USDT
            usdt_amount, display_currency = self.convert_to_usdt(amount, token_name, token_symbol)
            
            from_address = (txn.get("fromAddress") or 
                          txn.get("transferFromAddress") or 
                          txn.get("from") or 
                          txn.get("ownerAddress") or 
                          "Невідомо")
            from_address = from_address or "Невідомо"
            
            to_address = (txn.get("toAddress") or 
                         txn.get("transferToAddress") or 
                         txn.get("to") or 
                         "Невідомо")
            to_address = to_address or "Невідомо"
            
            txn_hash = (txn.get("hash") or 
                       txn.get("transactionHash") or 
                       txn.get("txID") or 
                       "")
            txn_hash = txn_hash or ""
            
            # Отримуємо timestamp та конвертуємо в число
            timestamp = (txn.get("timestamp") or 
                        txn.get("block_timestamp") or 
                        txn.get("time") or 
                        0)
            try:
                timestamp = float(timestamp) if timestamp else 0
            except (ValueError, TypeError):
                timestamp = 0
            
            # Форматуємо дату
            if timestamp > 0:
                date_str = datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")
            else:
                date_str = "Невідомо"
            
            # Формуємо повідомлення
            message = f"💰 <b>Нова оплата отримана!</b>\n\n"
            
            # Завжди показуємо суму в USDT
            if display_currency == "USDT":
                message += f"📊 <b>Сума:</b> {usdt_amount:.2f} USDT\n"
                # Додаємо інформацію про оригінальну валюту якщо це не було USDT
                if not is_usdt:
                    message += f"   <i>({amount:.6f} {token_name})</i>\n"
            else:
                # Якщо не вдалося конвертувати, показуємо оригінальну валюту
                message += f"📊 <b>Сума:</b> {amount:.6f} {token_name}\n"
                message += f"   <i>(Конвертація в USDT недоступна)</i>\n"
            
            message += f"📥 <b>Отримано на адресу:</b> <code>{to_address}</code>\n"
            message += f"📤 <b>Відправлено з адреси:</b> <code>{from_address}</code>\n"
            message += f"🕐 <b>Час:</b> {date_str}\n"
            if txn_hash:
                message += f"🔗 <b>Транзакція:</b> <a href='https://tronscan.org/#/transaction/{txn_hash}'>Переглянути</a>"
            
            return message
        except Exception as e:
            print(f"Помилка форматування повідомлення: {e}")
            return None
    
    async def send_notification(self, message):
        """Відправляє повідомлення в телеграм канал"""
        try:
            if not self.channel_id:
                print("⚠️  Channel ID не встановлено!")
                print("   Встановіть TELEGRAM_CHANNEL_ID в .env файлі або config.py")
                print("   Можна використати username каналу (наприклад: @your_channel)")
                print("   Або запустіть get_channel_id.py для отримання числового ID")
                return False
            
            await self.bot.send_message(
                chat_id=self.channel_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=False
            )
            return True
        except TelegramError as e:
            error_msg = str(e).lower()
            print(f"❌ Помилка відправки повідомлення: {e}")
            
            if "chat not found" in error_msg:
                print("   Перевірте правильність Channel ID та права бота в каналі")
            elif "not a member" in error_msg or "bot is not a member" in error_msg:
                print("\n" + "="*60)
                print("⚠️  БОТ НЕ ДОДАНО В КАНАЛ!")
                print("="*60)
                print("Щоб виправити це:")
                print("1. Відкрийте ваш Telegram канал")
                print("2. Перейдіть в Налаштування каналу → Адміністратори")
                print("3. Натисніть 'Додати адміністратора'")
                print("4. Знайдіть та додайте бота: @DP_payment_bot")
                print("5. Надайте боту права на 'Надсилання повідомлень'")
                print("6. Перезапустіть бота")
                print("="*60 + "\n")
            elif "forbidden" in error_msg:
                print("   Перевірте права бота в каналі (має бути адміністратором)")
            return False
    
    def get_transaction_amount_usdt(self, txn):
        """Обчислює суму транзакції в USDT"""
        try:
            # Отримуємо суму
            amount_raw = (txn.get("amount") or 
                         txn.get("quant") or 
                         txn.get("value") or 
                         txn.get("amount_str") or
                         0)
            
            # Конвертуємо в число
            try:
                if isinstance(amount_raw, str):
                    amount_raw = float(amount_raw)
                else:
                    amount_raw = float(amount_raw) if amount_raw else 0
            except (ValueError, TypeError):
                amount_raw = 0
            
            token_name = (txn.get("tokenName") or 
                         txn.get("token_name") or 
                         txn.get("name") or 
                         "TRX")
            token_name = token_name or "TRX"
            
            token_symbol = (txn.get("tokenSymbol") or 
                           txn.get("token_symbol") or 
                           txn.get("symbol") or 
                           "")
            token_symbol = token_symbol or ""
            
            # Визначаємо чи це USDT
            is_usdt = False
            if "USDT" in (token_name or "").upper() or "USDT" in (token_symbol or "").upper():
                is_usdt = True
                # USDT TRC20 має 6 десяткових знаків
                if amount_raw > 0:
                    amount = amount_raw / 1000000  # 1 USDT = 1,000,000 (6 zeros)
                else:
                    amount = 0
            else:
                # Для TRX та інших токенів конвертуємо з sun (1 TRX = 1,000,000 sun)
                if amount_raw > 0:
                    amount = amount_raw / 1000000
                else:
                    amount = 0
            
            # Конвертуємо все в USDT
            usdt_amount, _ = self.convert_to_usdt(amount, token_name, token_symbol)
            return usdt_amount
        except Exception as e:
            print(f"⚠️  Помилка обчислення суми: {e}")
            return 0
    
    def is_usdt_transaction(self, txn):
        """Перевіряє чи це USDT (TRC20) транзакція"""
        try:
            # Перевіряємо contract address (різні варіанти назв полів)
            contract_address = (txn.get("contractAddress") or 
                              txn.get("contract_address") or 
                              txn.get("tokenContractAddress") or 
                              txn.get("token_contract_address") or
                              txn.get("contract") or
                              txn.get("tokenContract") or
                              "")
            
            if contract_address:
                # Перевіряємо чи це USDT contract address
                if contract_address.upper() == self.usdt_contract.upper():
                    return True
                # Також перевіряємо чи в contract address є USDT contract
                if self.usdt_contract.upper() in contract_address.upper():
                    return True
            
            # Перевіряємо tokenType - має бути trc20 для USDT
            token_type = (txn.get("tokenType") or 
                         txn.get("token_type") or 
                         txn.get("tokenType2") or 
                         "").lower()
            
            # Перевіряємо по назві та символу токена
            token_name = (txn.get("tokenName") or 
                         txn.get("token_name") or 
                         txn.get("name") or 
                         txn.get("token") or
                         "").upper()
            
            token_symbol = (txn.get("tokenSymbol") or 
                           txn.get("token_symbol") or 
                           txn.get("symbol") or 
                           "").upper()
            
            # Якщо це TRC20 токен і в назві або символі є USDT
            if token_type == "trc20" and ("USDT" in token_name or "USDT" in token_symbol):
                return True
            
            # Також перевіряємо без tokenType якщо є USDT в назві/символі
            if "USDT" in token_name or "USDT" in token_symbol:
                return True
            
            # Додаткова перевірка: якщо tokenInfo містить contract address
            token_info = txn.get("tokenInfo") or txn.get("token_info") or {}
            if isinstance(token_info, dict):
                token_contract = (token_info.get("contractAddress") or 
                                token_info.get("contract_address") or 
                                token_info.get("address") or "")
                if token_contract and token_contract.upper() == self.usdt_contract.upper():
                    return True
            
            return False
        except Exception as e:
            print(f"⚠️  Помилка перевірки USDT: {e}")
            return False
    
    def process_transactions(self, transactions):
        """Обробляє транзакції та відправляє повідомлення про нові"""
        new_transactions = []
        
        print(f"🔍 Обробка {len(transactions)} трансферів...")
        print(f"⏰ Остання перевірка: {datetime.fromtimestamp(self.last_checked_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')}")
        
        for txn in transactions:
            # Спробуємо різні варіанти назв полів для hash
            txn_hash = (txn.get("hash") or 
                       txn.get("transactionHash") or 
                       txn.get("txID") or 
                       "")
            
            # Спробуємо різні варіанти назв полів для timestamp
            txn_timestamp = (txn.get("timestamp") or 
                           txn.get("block_timestamp") or 
                           txn.get("time") or 
                           0)
            
            # Конвертуємо timestamp в число
            try:
                txn_timestamp = float(txn_timestamp) if txn_timestamp else 0
            except (ValueError, TypeError):
                txn_timestamp = 0
            
            # Спробуємо різні варіанти назв полів для адреси отримувача
            to_address = (txn.get("toAddress") or 
                         txn.get("transferToAddress") or 
                         txn.get("to") or 
                         txn.get("to_address") or
                         "")
            
            from_address = (txn.get("fromAddress") or 
                          txn.get("transferFromAddress") or 
                          txn.get("from") or 
                          txn.get("from_address") or
                          "")
            
            # Перевіряємо чи це нова транзакція (не в списку оброблених)
            if txn_hash and txn_hash not in self.processed_txns:
                # Перевіряємо чи це вхідна транзакція (оплата) на нашу адресу
                if to_address and to_address.upper() == self.tron_address.upper():
                    # Перевіряємо чи це USDT (TRC20)
                    if self.is_usdt_transaction(txn):
                        # Перевіряємо timestamp - обробляємо тільки транзакції не старіші за 7 днів
                        # (щоб не обробляти дуже старі транзакції при першому запуску)
                        current_time_ms = int(time.time() * 1000)
                        seven_days_ago_ms = current_time_ms - (7 * 24 * 60 * 60 * 1000)
                        
                        if txn_timestamp > 0 and txn_timestamp < seven_days_ago_ms:
                            print(f"  ⏰ Трансфер занадто старий (пропускаємо): hash={txn_hash[:10]}..., timestamp={txn_timestamp}")
                            continue
                        
                        # Перевіряємо суму - тільки транзакції >= 1 USDT
                        usdt_amount = self.get_transaction_amount_usdt(txn)
                        if usdt_amount < 1.0:
                            print(f"  ⚠️  Трансфер менше 1 USDT (пропускаємо): hash={txn_hash[:10]}..., сума={usdt_amount:.2f} USDT")
                            # Все одно позначаємо як оброблену, щоб не перевіряти знову
                            self.processed_txns.add(txn_hash)
                            continue
                        
                        print(f"  ✅ Знайдено новий USDT трансфер >= 1 USDT: hash={txn_hash[:10]}..., to={to_address[:10]}..., сума={usdt_amount:.2f} USDT, timestamp={txn_timestamp}")
                        print(f"     Час транзакції: {datetime.fromtimestamp(txn_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S') if txn_timestamp > 0 else 'N/A'}")
                        new_transactions.append(txn)
                        self.processed_txns.add(txn_hash)
                    else:
                        # Діагностика: чому не USDT
                        token_name = (txn.get("tokenName") or txn.get("token_name") or txn.get("name") or "N/A")
                        token_symbol = (txn.get("tokenSymbol") or txn.get("token_symbol") or txn.get("symbol") or "N/A")
                        contract_addr = (txn.get("contractAddress") or txn.get("contract_address") or txn.get("tokenContractAddress") or "N/A")
                        print(f"  ⚠️  Трансфер не USDT (пропускаємо): hash={txn_hash[:10]}..., token={token_name}/{token_symbol}, contract={contract_addr[:20] if contract_addr != 'N/A' else 'N/A'}...")
                else:
                    # Діагностика для транзакцій не на нашу адресу (тільки для USDT)
                    if self.is_usdt_transaction(txn):
                        print(f"  ⚠️  USDT трансфер не на нашу адресу: hash={txn_hash[:10]}..., to={to_address[:20] if to_address else 'N/A'}..., наша={self.tron_address[:20]}...")
            else:
                # Вже оброблено - не виводимо, щоб не спамити
                pass
        
        print(f"📊 Підсумок: знайдено {len(new_transactions)} нових USDT платежів")
        return new_transactions
    
    async def check_payments(self):
        """Основна функція перевірки платежів"""
        print(f"\n{'='*60}")
        print(f"🔍 Перевірка платежів... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        transfers = self.get_recent_transactions()
        
        if not transfers:
            print("⚠️  Трансфери не знайдено або помилка API")
            return
        
        if not isinstance(transfers, list):
            print(f"⚠️  Отримано не список трансферів: {type(transfers)}")
            return
        
        print(f"📥 Отримано {len(transfers)} трансферів з API")
        
        new_transactions = self.process_transactions(transfers)
        
        if new_transactions:
            print(f"✅ Знайдено {len(new_transactions)} нових платежів")
            
            for txn in new_transactions:
                message = self.format_transaction_message(txn)
                if message:
                    success = await self.send_notification(message)
                    if success:
                        print(f"✅ Повідомлення відправлено для транзакції {txn.get('hash', '')[:10]}...")
                    await asyncio.sleep(1)  # Невелика затримка між повідомленнями
            
            # Зберігаємо оброблені транзакції
            self.save_processed_txns()
        else:
            print("ℹ️  Нових платежів не знайдено")
        
        # Оновлюємо час останньої перевірки після кожної перевірки
        self.last_checked_timestamp = int(time.time() * 1000)
    
    async def start_monitoring(self):
        """Запускає моніторинг"""
        print("="*60)
        print("🚀 Бот запущено! Моніторинг платежів активовано.")
        print("="*60)
        print(f"📍 Адреса для моніторингу: {self.tron_address}")
        print(f"⏱️  Інтервал перевірки: {config.CHECK_INTERVAL} секунд")
        print(f"📝 Оброблено транзакцій: {len(self.processed_txns)}")
        
        # Отримуємо інформацію про бота
        try:
            bot_info = await self.bot.get_me()
            print(f"🤖 Бот: @{bot_info.username}")
        except Exception as e:
            print(f"❌ Помилка отримання інформації про бота: {e}")
            print("   Перевірте правильність TELEGRAM_BOT_TOKEN")
            return
        
        # Перевірка налаштувань
        if not self.channel_id:
            print("\n⚠️  УВАГА: TELEGRAM_CHANNEL_ID не встановлено!")
            print("   Бот не зможе відправляти повідомлення.")
            print("   Встановіть Channel ID в .env файлі або config.py")
            print("   Запустіть: python get_channel_id.py")
        else:
            print(f"📢 Канал: {self.channel_id}")
            # Перевіряємо доступ до каналу
            try:
                chat = await self.bot.get_chat(chat_id=self.channel_id)
                print(f"✅ Доступ до каналу підтверджено: {chat.title}")
                
                # Перевіряємо чи бот є адміністратором
                try:
                    member = await self.bot.get_chat_member(chat_id=self.channel_id, user_id=(await self.bot.get_me()).id)
                    if member.status in ['administrator', 'creator']:
                        print(f"✅ Бот є адміністратором каналу")
                    else:
                        print(f"⚠️  Бот не є адміністратором каналу!")
                        print("   Додайте бота як адміністратора в налаштуваннях каналу")
                except Exception as e:
                    print(f"⚠️  Не вдалося перевірити права бота: {e}")
                    print("   Переконайтеся, що бот додано в канал як адміністратор")
                    
            except TelegramError as e:
                error_msg = str(e).lower()
                print(f"⚠️  Не вдалося отримати доступ до каналу: {e}")
                if "not found" in error_msg or "chat not found" in error_msg:
                    print("   Перевірте правильність Channel ID")
                elif "not a member" in error_msg:
                    print("\n" + "="*60)
                    print("⚠️  БОТ НЕ ДОДАНО В КАНАЛ!")
                    print("="*60)
                    print("Інструкції:")
                    print("1. Відкрийте ваш Telegram канал")
                    print("2. Налаштування каналу → Адміністратори")
                    print("3. Додайте бота @DP_payment_bot як адміністратора")
                    print("4. Надайте права на 'Надсилання повідомлень'")
                    print("5. Перезапустіть бота")
                    print("="*60 + "\n")
                else:
                    print("   Перевірте правильність Channel ID та права бота")
        
        print("="*60 + "\n")
        
        # Відправляємо повідомлення про запуск бота в канал
        if self.channel_id:
            try:
                startup_message = self.format_startup_message()
                if startup_message:
                    success = await self.send_notification(startup_message)
                    if success:
                        print("✅ Повідомлення про запуск відправлено в канал\n")
                    else:
                        print("⚠️  Не вдалося відправити повідомлення про запуск\n")
            except Exception as e:
                print(f"⚠️  Помилка відправки повідомлення про запуск: {e}\n")
        
        # Після відправки повідомлення про запуск, позначаємо що перший запуск завершено
        self.is_first_run = False
        
        # Невелика затримка перед першою перевіркою, щоб не обробляти старі транзакції
        await asyncio.sleep(2)
        
        while True:
            try:
                await self.check_payments()
            except Exception as e:
                print(f"❌ Помилка в циклі моніторингу: {e}")
            
            await asyncio.sleep(config.CHECK_INTERVAL)
    
    async def set_channel_command(self, channel_id):
        """Встановлює ID каналу"""
        self.channel_id = channel_id
        config.TELEGRAM_CHANNEL_ID = channel_id
        print(f"✅ Channel ID встановлено: {channel_id}")

async def main():
    monitor = PaymentMonitor()
    await monitor.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())

