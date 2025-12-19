"""
Скрипт для перевірки конкретної транзакції
"""
import requests
import json
import config
import sys
import io
from datetime import datetime

# Виправлення кодування для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def check_transaction_by_hash(txn_hash):
    """Перевіряє транзакцію за хешем"""
    headers = {
        "TRON-PRO-API-KEY": config.TRONSCAN_API_TOKEN
    }
    
    # Спробуємо різні endpoints
    endpoints = [
        f"https://apilist.tronscan.org/api/transaction/{txn_hash}",
        f"https://apilist.tronscan.org/api/transaction-info?hash={txn_hash}",
        f"https://apilist.tronscan.org/api/transfer?hash={txn_hash}",
    ]
    
    for url in endpoints:
        try:
            print(f"\n📡 Запит до: {url}")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"📥 Статус: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 Дані отримано!")
                print(f"📄 Структура: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                print(f"\n📋 Повна відповідь:\n{json.dumps(data, indent=2, ensure_ascii=False)[:2000]}")
                return data
            else:
                print(f"❌ Помилка: {response.text[:200]}")
        except Exception as e:
            print(f"⚠️  Помилка: {e}")
            continue
    
    return None

def check_transfers_for_address(address):
    """Перевіряє останні трансфери для адреси"""
    headers = {
        "TRON-PRO-API-KEY": config.TRONSCAN_API_TOKEN
    }
    
    endpoints = [
        "https://apilist.tronscan.org/api/transfer",
        "https://apilist.tronscan.org/api/trc20/transfer",
    ]
    
    for url in endpoints:
        try:
            params = {
                "address": address,
                "start": 0,
                "limit": 20,
                "sort": "-timestamp"
            }
            
            print(f"\n📡 Запит до: {url}")
            print(f"📋 Параметри: {params}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"📥 Статус: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Спробуємо різні варіанти структури
                transfers = []
                if isinstance(data, dict):
                    if data.get("success") and "data" in data:
                        transfers = data["data"]
                    elif "data" in data:
                        transfers = data["data"]
                elif isinstance(data, list):
                    transfers = data
                
                    if transfers:
                        print(f"\n✅ Отримано {len(transfers)} трансферів")
                        
                        # Шукаємо нашу транзакцію
                        target_hash = "e4bf1708486593b44ad2df6fe870975de4d725be8ae1db401c6a6eddda748d8b"
                        found = False
                        for i, txn in enumerate(transfers):
                            txn_hash = (txn.get("hash") or txn.get("transactionHash") or txn.get("txID") or "")
                            if txn_hash.startswith(target_hash[:20]) or target_hash.startswith(txn_hash[:20]):
                                print(f"\n⭐ ЗНАЙДЕНО ШУКАНУ ТРАНЗАКЦІЮ на позиції {i+1}!")
                                print(f"📄 Повні дані транзакції:")
                                print(json.dumps(txn, indent=2, ensure_ascii=False))
                                found = True
                                break
                        
                        if not found:
                            print(f"\n⚠️  Транзакція не знайдена в перших {len(transfers)} результатах")
                            print(f"\n📋 Перші 10 трансферів для аналізу:")
                        else:
                            print(f"\n📋 Перші 5 трансферів для порівняння:")
                        
                        for i, txn in enumerate(transfers[:10], 1):
                            txn_hash = txn.get("hash") or txn.get("transactionHash") or txn.get("txID") or "N/A"
                            to_addr = txn.get("toAddress") or txn.get("transferToAddress") or txn.get("to") or "N/A"
                            token_name = txn.get("tokenName") or txn.get("token_name") or "N/A"
                            timestamp = txn.get("timestamp") or txn.get("block_timestamp") or 0
                            
                            print(f"\n  {i}. Hash: {txn_hash[:20]}...")
                            print(f"     To: {to_addr[:30]}...")
                            print(f"     Token: {token_name}")
                            print(f"     Timestamp: {timestamp}")
                            if timestamp:
                                dt = datetime.fromtimestamp(timestamp / 1000)
                                print(f"     Час: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                            
                            # Перевіряємо чи це наша транзакція
                            if txn_hash.startswith("e4bf1708486593b44ad2df6fe870975de4d725be8ae1db401c6a6eddda748d8b"):
                                print(f"     ⭐ ЦЕ ШУКАНА ТРАНЗАКЦІЯ!")
                                print(f"     📄 Повні дані:")
                                print(json.dumps(txn, indent=2, ensure_ascii=False))
                    
                    return transfers
                else:
                    print(f"⚠️  Трансфери не знайдено")
            else:
                print(f"❌ Помилка: {response.text[:200]}")
        except Exception as e:
            print(f"⚠️  Помилка: {e}")
            continue
    
    return None

if __name__ == "__main__":
    print("="*60)
    print("🔍 Перевірка транзакції")
    print("="*60)
    
    txn_hash = "e4bf1708486593b44ad2df6fe870975de4d725be8ae1db401c6a6eddda748d8b"
    address = config.TRON_ADDRESS
    
    print(f"\n📍 Адреса: {address}")
    print(f"🔗 Хеш транзакції: {txn_hash}")
    
    print("\n" + "="*60)
    print("1️⃣ Перевірка транзакції за хешем")
    print("="*60)
    txn_data = check_transaction_by_hash(txn_hash)
    
    print("\n" + "="*60)
    print("2️⃣ Перевірка останніх трансферів для адреси")
    print("="*60)
    transfers = check_transfers_for_address(address)
    
    print("\n" + "="*60)
    print("✅ Перевірка завершена")
    print("="*60)

