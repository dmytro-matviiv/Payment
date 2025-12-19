import asyncio
import time
import requests
import json
import os
from datetime import datetime, timezone, timedelta
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
        self.processed_txns, saved_start_time = self.load_processed_txns()
        self.usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        
        # Встановлюємо час запуску бота (timestamp в мілісекундах)
        if saved_start_time:
            self.bot_start_time = saved_start_time
            print(f"⏰ Бот був запущений: {self.format_timestamp(saved_start_time)}")
        else:
            # Перший запуск - встановлюємо поточний час
            self.bot_start_time = int(time.time() * 1000)
            print(f"⏰ Перший запуск бота: {self.format_timestamp(self.bot_start_time)}")
            print(f"📝 Всі транзакції до цього моменту будуть ігноруватися")
    
    def format_timestamp(self, timestamp_ms):
        """Форматує timestamp в UTC+2 (Київський час)"""
        try:
            timestamp = float(timestamp_ms)
            # Конвертуємо timestamp в UTC+2 (Київський час)
            utc_time = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
            # Додаємо 2 години для UTC+2 (Україна)
            ukraine_tz = timezone(timedelta(hours=2))
            local_time = utc_time.astimezone(ukraine_tz)
            return local_time.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return "Невідомо"
    
    def load_processed_txns(self):
        """Завантажує список оброблених транзакцій"""
        if os.path.exists(self.processed_txns_file):
            try:
                with open(self.processed_txns_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data.get("txns", [])), data.get("bot_start_time")
            except Exception as e:
                print(f"⚠️  Помилка завантаження: {e}")
        return set(), None
    
    def save_processed_txns(self):
        """Зберігає список оброблених транзакцій"""
        try:
            data = {
                "txns": list(self.processed_txns),
                "last_update": datetime.now().isoformat(),
                "bot_start_time": self.bot_start_time
            }
            with open(self.processed_txns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Помилка збереження: {e}")
    
    def get_transactions_trongrid(self):
        """Альтернативний метод через TronGrid API"""
        # Спробуємо спочатку з фільтром по USDT, потім без фільтра
        variants = [
            {"contract_address": self.usdt_contract, "name": "з фільтром USDT"},
            {"name": "без фільтра (всі TRC20)"}
        ]
        
        for variant in variants:
            try:
                url = f"https://api.trongrid.io/v1/accounts/{self.tron_address_original}/transactions/trc20"
                params = {
                    "limit": 50,
                    "only_confirmed": True
                }
                if "contract_address" in variant:
                    params["contract_address"] = variant["contract_address"]
                
                print(f"\n📡 TronGrid API ({variant['name']}): {url}")
                print(f"📋 Параметри: {params}")
                
                response = requests.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"📊 TronGrid відповідь: тип={type(data)}, ключі={list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                    
                    if "data" in data and isinstance(data["data"], list):
                        transfers = data["data"]
                        print(f"📊 TronGrid: знайдено {len(transfers)} транзакцій")
                        
                        if len(transfers) > 0:
                            print(f"✅ TronGrid: Отримано {len(transfers)} транзакцій")
                            # Показуємо приклад
                            first = transfers[0]
                            print(f"🔍 Приклад: transaction_id={first.get('transaction_id', 'N/A')[:32]}...")
                            print(f"   to={first.get('to', 'N/A')}")
                            print(f"   token={first.get('token_info', {}).get('symbol', 'N/A')}")
                            
                            # Конвертуємо формат TronGrid в формат, який очікує наш код
                            converted = []
                            for tx in transfers:
                                token_info = tx.get("token_info", {})
                                converted.append({
                                    "hash": tx.get("transaction_id", ""),
                                    "transactionHash": tx.get("transaction_id", ""),
                                    "toAddress": tx.get("to", ""),
                                    "fromAddress": tx.get("from", ""),
                                    "amount": tx.get("value", "0"),
                                    "timestamp": tx.get("block_timestamp", 0),
                                    "contractAddress": token_info.get("address", ""),
                                    "contract_address": token_info.get("address", ""),
                                    "tokenSymbol": token_info.get("symbol", ""),
                                    "token_symbol": token_info.get("symbol", ""),
                                    "tokenName": token_info.get("name", ""),
                                    "token_name": token_info.get("name", "")
                                })
                            return converted
                        else:
                            print("⚠️  TronGrid: порожній список транзакцій")
                else:
                    print(f"⚠️  TronGrid API помилка: {response.status_code}")
                    print(f"Відповідь: {response.text[:300]}")
            except Exception as e:
                print(f"⚠️  TronGrid API помилка ({variant['name']}): {e}")
                import traceback
                traceback.print_exc()
        
        return None
    
    def get_transactions(self):
        """Отримує останні TRC20 трансфери з Tronscan API"""
        print(f"\n🔍 Пошук транзакцій для адреси: {self.tron_address_original}")
        
        # Спочатку спробуємо TronGrid API
        trongrid_result = self.get_transactions_trongrid()
        if trongrid_result:
            return trongrid_result
        
        # Спробуємо різні варіанти headers (згідно з документацією Tronscan API)
        headers_variants = [
            {"TRON-PRO-API-KEY": self.api_token} if self.api_token else {},
            {"TRON-PRO-API-KEY": self.api_token, "Content-Type": "application/json"} if self.api_token else {},
            {}  # Без API ключа
        ]
        
        # Endpoints згідно з офіційною документацією Tronscan API
        # https://docs.tronscan.org/api-endpoints/transactions-and-transfers
        endpoints_to_try = [
            # Варіант 1: Get trc20&721 transfers list - з фільтром по USDT та toAddress
            {
                "url": "https://apilist.tronscanapi.com/api/transfer",
                "params": {
                    "toAddress": self.tron_address_original,
                    "contract_address": self.usdt_contract,
                    "start": 0,
                    "limit": 50,
                    "confirm": "true"  # Тільки підтверджені транзакції
                },
                "name": "TRC20 transfers (toAddress + USDT contract)"
            },
            # Варіант 2: Get trc20&721 transfers list - з relatedAddress та USDT
            {
                "url": "https://apilist.tronscanapi.com/api/transfer",
                "params": {
                    "relatedAddress": self.tron_address_original,
                    "contract_address": self.usdt_contract,
                    "start": 0,
                    "limit": 50,
                    "confirm": "true"
                },
                "name": "TRC20 transfers (relatedAddress + USDT contract)"
            },
            # Варіант 3: Get trc20&721 transfers list - тільки toAddress (всі TRC20)
            {
                "url": "https://apilist.tronscanapi.com/api/transfer",
                "params": {
                    "toAddress": self.tron_address_original,
                    "start": 0,
                    "limit": 50,
                    "confirm": "true"
                },
                "name": "TRC20 transfers (toAddress, всі токени)"
            },
            # Варіант 4: Get account's transaction datas - з фільтром USDT
            {
                "url": f"https://apilist.tronscanapi.com/api/account/{self.tron_address_original}/transactions/trc20",
                "params": {
                    "address": self.tron_address_original,
                    "trc20Id": self.usdt_contract,
                    "direction": 2,  # 2 = transfer-in (вхідні)
                    "start": 0,
                    "limit": 50,
                    "reverse": "true"  # Сортування за часом створення
                },
                "name": "Account TRC20 transactions (USDT, transfer-in)"
            },
            # Варіант 5: Get account's transaction datas - всі TRC20
            {
                "url": f"https://apilist.tronscanapi.com/api/account/{self.tron_address_original}/transactions/trc20",
                "params": {
                    "address": self.tron_address_original,
                    "direction": 2,  # 2 = transfer-in
                    "start": 0,
                    "limit": 50,
                    "reverse": "true"
                },
                "name": "Account TRC20 transactions (всі токени, transfer-in)"
            },
            # Варіант 6: Get trc20&721 transfers list - relatedAddress (всі TRC20)
            {
                "url": "https://apilist.tronscanapi.com/api/transfer",
                "params": {
                    "relatedAddress": self.tron_address_original,
                    "start": 0,
                    "limit": 50,
                    "confirm": "true"
                },
                "name": "TRC20 transfers (relatedAddress, всі токени)"
            }
        ]
        
        attempt = 0
        for headers in headers_variants:
            for endpoint_config in endpoints_to_try:
                attempt += 1
                url = endpoint_config["url"]
                params = endpoint_config["params"]
                endpoint_name = endpoint_config.get("name", "Unknown")
                
                try:
                    print(f"\n📡 Спроба {attempt}: {endpoint_name}")
                    print(f"🔗 URL: {url}")
                    print(f"📋 Параметри: {params}")
                    if headers:
                        print(f"🔑 Headers: {list(headers.keys())}")
                    
                    response = requests.get(url, headers=headers, params=params, timeout=15)
                    print(f"📊 Статус відповіді: {response.status_code}")
            
                    if response.status_code == 200:
                        try:
                            data = response.json()
                        except json.JSONDecodeError as e:
                            print(f"❌ Помилка парсингу JSON: {e}")
                            print(f"Відповідь (перші 500 символів): {response.text[:500]}")
                            continue
                        
                        # Детальна діагностика структури відповіді
                        print(f"📊 Тип відповіді: {type(data)}")
                        if isinstance(data, dict):
                            print(f"📊 Ключі в відповіді: {list(data.keys())}")
                            # Показуємо перші 800 символів JSON для діагностики
                            json_str = json.dumps(data, indent=2, ensure_ascii=False)
                            print(f"📄 Приклад даних: {json_str[:800]}...")
                        elif isinstance(data, list):
                            print(f"📊 Отримано список з {len(data)} елементів")
                            if len(data) > 0:
                                print(f"📄 Приклад першого елемента: {json.dumps(data[0], indent=2, ensure_ascii=False)[:400]}...")
                        
                        # Отримуємо список трансферів згідно з документацією Tronscan API
                        transfers = []
                        if isinstance(data, dict):
                            # Згідно з документацією, endpoint /api/transfer повертає {"data": [...]}
                            # А endpoint /api/account/{address}/transactions/trc20 також повертає {"data": [...]}
                            if "data" in data:
                                transfers = data["data"]
                                if isinstance(transfers, list):
                                    print(f"✅ Знайдено ключ 'data' з {len(transfers)} елементів")
                                else:
                                    print(f"⚠️  Ключ 'data' не є списком (тип: {type(transfers)})")
                            else:
                                print(f"⚠️  Не знайдено ключа 'data'. Всі ключі: {list(data.keys())}")
                                # Спробуємо знайти будь-який список в словнику
                                for key, value in data.items():
                                    if isinstance(value, list) and len(value) > 0:
                                        # Перевіримо чи це виглядає як список транзакцій
                                        first_item = value[0] if value else {}
                                        if isinstance(first_item, dict):
                                            # Перевіряємо наявність полів транзакції
                                            tx_fields = ['hash', 'transactionHash', 'toAddress', 'fromAddress', 'to', 'from', 'transaction_id']
                                            if any(k in first_item for k in tx_fields):
                                                transfers = value
                                                print(f"✅ Знайдено список транзакцій в ключі '{key}' з {len(transfers)} елементів")
                                                break
                        elif isinstance(data, list):
                            transfers = data
                            print(f"✅ Відповідь є списком з {len(transfers)} елементів")
                        
                        if transfers and isinstance(transfers, list) and len(transfers) > 0:
                            print(f"✅ УСПІХ! Отримано {len(transfers)} трансферів з {endpoint_name}")
                            # Показуємо приклад першої транзакції
                            first = transfers[0]
                            print(f"🔍 Приклад першої транзакції:")
                            print(f"   Hash: {first.get('hash', first.get('transactionHash', first.get('transaction_id', 'N/A')))[:32]}...")
                            print(f"   To: {first.get('toAddress', first.get('to', 'N/A'))}")
                            print(f"   From: {first.get('fromAddress', first.get('from', 'N/A'))}")
                            print(f"   Amount: {first.get('amount', first.get('value', 'N/A'))}")
                            print(f"   Token: {first.get('tokenInfo', {}).get('symbol', first.get('tokenSymbol', 'N/A'))}")
                            return transfers
                        else:
                            if isinstance(transfers, list) and len(transfers) == 0:
                                print(f"⚠️  Отримано порожній список трансферів з {endpoint_name}")
                            else:
                                print(f"⚠️  Трансфери не знайдено або невірний формат (тип: {type(transfers)})")
                            continue  # Спробуємо наступний варіант
                    elif response.status_code == 400:
                        print(f"⚠️  Помилка 400 (Bad Request) - перевірте параметри")
                        print(f"Відповідь: {response.text[:500]}")
                        continue
                    elif response.status_code == 401:
                        print(f"⚠️  Помилка 401 (Unauthorized) - можливо невірний API ключ")
                        print(f"Відповідь: {response.text[:500]}")
                        continue
                    elif response.status_code == 404:
                        print(f"⚠️  Помилка 404 (Not Found) - endpoint не знайдено")
                        continue
                    else:
                        print(f"❌ Помилка API: {response.status_code}")
                        print(f"Відповідь: {response.text[:500]}")
                        continue
                except requests.exceptions.Timeout:
                    print(f"❌ Таймаут запиту до {endpoint_name}")
                    continue
                except requests.exceptions.RequestException as e:
                    print(f"❌ Помилка мережі: {e}")
                    continue
                except Exception as e:
                    print(f"❌ Несподівана помилка: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        # Якщо всі варіанти не спрацювали
        print(f"\n❌ Всі {attempt} спроб не спрацювали")
        print(f"💡 Перевірте:")
        print(f"   1. Чи правильна адреса: {self.tron_address_original}")
        print(f"   2. Чи є транзакції на цій адресі (перевірте на tronscan.org)")
        print(f"   3. Чи правильний API ключ (якщо використовується)")
        return []
    
    def is_usdt(self, txn):
        """Перевіряє чи це USDT TRC20 транзакція"""
        # Перевірка contract address (різні формати)
        contract = (
            txn.get("contractAddress") or 
            txn.get("contract_address") or 
            txn.get("tokenContractAddress") or 
            ""
        )
        
        # Перевірка через tokenInfo (формат Tronscan API)
        token_info = txn.get("tokenInfo") or txn.get("token_info") or {}
        if isinstance(token_info, dict):
            contract_from_info = token_info.get("address") or token_info.get("contractAddress") or ""
            if contract_from_info:
                contract = contract or contract_from_info
        
        if contract and contract.upper() == self.usdt_contract.upper():
            return True
        
        # Перевірка по символу та назві
        symbol = (
            txn.get("tokenSymbol") or 
            txn.get("token_symbol") or 
            txn.get("symbol") or 
            ""
        )
        
        # Перевірка символу в tokenInfo
        if isinstance(token_info, dict):
            symbol = symbol or token_info.get("symbol") or token_info.get("tokenAbbr") or ""
        
        name = (
            txn.get("tokenName") or 
            txn.get("token_name") or 
            txn.get("name") or 
            ""
        )
        
        # Перевірка назви в tokenInfo
        if isinstance(token_info, dict):
            name = name or token_info.get("name") or token_info.get("tokenName") or ""
        
        symbol = symbol.upper()
        name = name.upper()
        
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
        old_txns_count = 0
        
        print(f"\n🔍 Обробка {len(transactions)} транзакцій...")
        
        for i, txn in enumerate(transactions):
            try:
                # Отримуємо hash (різні формати)
                txn_hash = (
                    txn.get("hash") or 
                    txn.get("transactionHash") or 
                    txn.get("transaction_id") or 
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
                
                # Перевіряємо timestamp транзакції - ігноруємо старі транзакції
                txn_timestamp = (
                    txn.get("timestamp") or 
                    txn.get("block_timestamp") or 
                    txn.get("time") or 
                    0
                )
                
                try:
                    txn_timestamp = float(txn_timestamp)
                    # Якщо транзакція старіша за час запуску бота - ігноруємо її
                    if txn_timestamp > 0 and txn_timestamp < self.bot_start_time:
                        # Автоматично додаємо стару транзакцію в processed_txns
                        self.processed_txns.add(txn_hash)
                        old_txns_count += 1
                        if old_txns_count <= 3:  # Логуємо перші 3 для інформації
                            txn_date = self.format_timestamp(txn_timestamp)
                            print(f"  ⏭️  Ігноруємо стару транзакцію: {txn_hash[:16]}... ({txn_date})")
                        continue
                except (ValueError, TypeError):
                    # Якщо не вдалося отримати timestamp, продовжуємо обробку
                    pass
                
                # Отримуємо адресу отримувача (різні формати)
                to_addr = (
                    txn.get("toAddress") or 
                    txn.get("transferToAddress") or 
                    txn.get("to") or 
                    txn.get("to_address") or 
                    ""
                )
                
                # Для Tronscan API може бути toAddressList
                if not to_addr and "toAddressList" in txn:
                    to_address_list = txn.get("toAddressList", [])
                    if isinstance(to_address_list, list) and len(to_address_list) > 0:
                        to_addr = to_address_list[0]
                
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
        
        if old_txns_count > 0:
            print(f"⏭️  Проігноровано {old_txns_count} старих транзакцій (до запуску бота)")
        print(f"📊 Знайдено {len(new_txns)} нових транзакцій >= 1 USDT\n")
        return new_txns
    
    def format_message(self, txn):
        """Форматує повідомлення про транзакцію"""
        try:
            # Отримуємо дані (підтримка різних форматів)
            txn_hash = (
                txn.get("hash") or 
                txn.get("transactionHash") or 
                txn.get("transaction_id") or 
                txn.get("txID") or 
                ""
            )
            
            amount_usdt = self.get_amount_usdt(txn)
            
            from_addr = (
                txn.get("fromAddress") or 
                txn.get("transferFromAddress") or 
                txn.get("from") or 
                txn.get("from_address") or 
                txn.get("ownerAddress") or  # Формат Tronscan API
                "Невідомо"
            )
            
            to_addr = (
                txn.get("toAddress") or 
                txn.get("transferToAddress") or 
                txn.get("to") or 
                txn.get("to_address") or 
                ""
            )
            
            # Для Tronscan API може бути toAddressList
            if not to_addr and "toAddressList" in txn:
                to_address_list = txn.get("toAddressList", [])
                if isinstance(to_address_list, list) and len(to_address_list) > 0:
                    to_addr = to_address_list[0]
            
            if not to_addr:
                to_addr = self.tron_address
            
            timestamp = (
                txn.get("timestamp") or 
                txn.get("block_timestamp") or 
                txn.get("time") or 
                0
            )
            
            date_str = self.format_timestamp(timestamp)
            
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
        date_str = self.format_timestamp(timestamp)
        
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
        
        # При першому запуску автоматично додаємо всі існуючі транзакції в processed_txns
        # Перевіряємо чи це перший запуск (файл не існує або bot_start_time щойно встановлений)
        is_first_run = not os.path.exists(self.processed_txns_file) or len(self.processed_txns) == 0
        
        if is_first_run:
            print("🔄 Перший запуск: обробка існуючих транзакцій...")
            print("   (Всі транзакції до цього моменту будуть ігноруватися)\n")
            
            # Отримуємо всі транзакції
            existing_transactions = self.get_transactions()
            if existing_transactions:
                print(f"📥 Знайдено {len(existing_transactions)} існуючих транзакцій")
                added_count = 0
                # Обробляємо їх, щоб додати в processed_txns (але не відправляємо повідомлення)
                for txn in existing_transactions:
                    txn_hash = (
                        txn.get("hash") or 
                        txn.get("transactionHash") or 
                        txn.get("transaction_id") or 
                        txn.get("txID") or 
                        ""
                    )
                    if txn_hash:
                        self.processed_txns.add(txn_hash)
                        added_count += 1
                
                # Зберігаємо оброблені транзакції та bot_start_time
                self.save_processed_txns()
                print(f"✅ Додано {added_count} існуючих транзакцій в список оброблених")
                print(f"💾 Збережено час запуску бота для майбутніх перевірок\n")
        
        # ТЕСТОВА ПЕРЕВІРКА: показуємо останню транзакцію
        self.show_last_transaction()
        
        # Відправляємо повідомлення про запуск
        startup_msg = (
            f"✅ <b>Бот запущено!</b>\n\n"
            f"📍 <b>Адреса:</b> <code>{self.tron_address}</code>\n"
            f"⏱️  <b>Інтервал:</b> {config.CHECK_INTERVAL} сек\n"
            f"🕐 <b>Час:</b> {datetime.now(timezone(timedelta(hours=2))).strftime('%Y-%m-%d %H:%M:%S')}\n"
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
