#!/usr/bin/env python3
import subprocess
import sys
import re
from decimal import Decimal, InvalidOperation
import getpass
import json
import time

def validate_gonka_address(address):
    """Проверка формата адреса Gonka (Cosmos SDK)"""
    pattern = r'^gonka1[a-z0-9]{38,42}$'
    return bool(re.match(pattern, address))

def validate_amount(amount_str):
    """Проверка и конвертация суммы"""
    try:
        amount = Decimal(amount_str)
        if amount <= 0:
            return None, "сумма должна быть больше 0"
        return amount, None
    except (InvalidOperation, ValueError):
        return None, "неверный формат суммы"

def gonka_to_ngonka(amount):
    """Конвертация gonka в ngonka (1 gonka = 1,000,000,000 ngonka)"""
    return int(amount * Decimal('1000000000'))

def extract_txhash(output):
    """Извлечение txhash из вывода команды"""
    try:
        data = json.loads(output)
        if 'txhash' in data:
            return data['txhash'], data.get('code', 0), data.get('raw_log', '')
    except:
        pass
    
    # Ищем txhash в тексте
    match = re.search(r'txhash:\s*([A-F0-9]{64})', output, re.IGNORECASE)
    if match:
        return match.group(1), 0, ''
    
    return None, -1, 'не удалось извлечь txhash'

def send_gonka(address, amount_gonka, sender, password, chain_id='gonka-mainnet', 
               node='http://tower.gonka.top:26657', keyring_backend='file'):
    """Отправка монет Gonka"""
    
    # Валидация адреса
    if not validate_gonka_address(address):
        return False, "неверный формат адреса", None
    
    # Валидация суммы
    amount_decimal, error = validate_amount(str(amount_gonka))
    if error:
        return False, error, None
    
    # Конвертация в ngonka
    amount_ngonka = gonka_to_ngonka(amount_decimal)
    
    # Формирование команды
    cmd = [
        '/home/mitch/Crypto/gonka.ai/inferenced', 'tx', 'bank', 'send',
        sender,
        address,
        f'{amount_ngonka}ngonka',
        '--chain-id', chain_id,
        '--keyring-backend', keyring_backend,
        '--node', node,
        '--yes'
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            input=password + '\n',
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if result.returncode == 0:
            txhash, code, raw_log = extract_txhash(result.stdout)
            
            # Проверяем код ответа из JSON
            if code == 0:
                return True, None, txhash
            else:
                # Извлекаем краткое сообщение об ошибке
                error_msg = raw_log.split(':')[0] if raw_log else f"код ошибки {code}"
                return False, error_msg[:100], txhash
        else:
            error_msg = result.stderr.strip().split('\n')[0] if result.stderr else "неизвестная ошибка"
            return False, error_msg[:100], None
    except subprocess.TimeoutExpired:
        return False, "таймаут выполнения", None
    except Exception as e:
        return False, str(e)[:100], None

def process_file(filename, sender, password, delay=6):
    """Обработка файла с транзакциями"""
    success_count = 0
    fail_count = 0
    
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Файл {filename} не найден")
        return
    except Exception as e:
        print(f"Ошибка чтения файла: {e}")
        return
    
    #print(f"Отправитель: {sender}")
    #print(f"Задержка между транзакциями: {delay} сек")
    #print(f"Обработка транзакций из {filename}\n")
    
    first_tx = True
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        # Пропуск пустых строк и комментариев
        if not line or line.startswith('#') or line.startswith('*'):
            continue
        
        # Парсинг строки
        parts = line.split()
        if len(parts) != 2:
            print(f"{line} Error: неверный формат (ожидается: адрес сумма)")
            fail_count += 1
            continue
        
        address, amount_str = parts
        
        # Задержка между транзакциями (кроме первой)
        if not first_tx:
            #print(f"Ожидание {delay} сек...")
            time.sleep(delay)
        first_tx = False
        
        # Отправка
        success, error, txhash = send_gonka(address, amount_str, sender, password)
        
        if success:
            txhash_str = f" txhash: {txhash}" if txhash else ""
            print(f"{address} {amount_str} ok{txhash_str}")
            success_count += 1
        else:
            txhash_str = f" txhash: {txhash}" if txhash else ""
            print(f"{address} {amount_str} Error: {error}{txhash_str}")
            fail_count += 1
    
    #print(f"\nИтого: успешно {success_count}, ошибок {fail_count}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Использование: python send_gonka.py <файл> <sender> [пароль] [задержка_сек]")
        print("\nПример:")
        print("python send_gonka.py transactions.txt full2")
        print("python send_gonka.py transactions.txt full2 mypass 10")
        sys.exit(1)
    
    filename = sys.argv[1]
    sender = sys.argv[2]
    
    if len(sys.argv) >= 4:
        password = sys.argv[3]
    else:
        password = getpass.getpass(f"Введите пароль для кошелька {sender}: ")
    
    # Задержка между транзакциями (по умолчанию 10 секунд)
    delay = int(sys.argv[4]) if len(sys.argv) >= 5 else 10
    
    process_file(filename, sender, password, delay)
