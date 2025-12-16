#!/usr/bin/env python3
import subprocess
import csv
import sys
import yaml
import re
import os

# Адрес ноды
NODE_URL = "http://node2.gonka.ai:8000"

def validate_wallet(wallet):
    """
    Валидация адреса кошелька
    Возвращает (is_valid, error_message)
    """
    # Проверка префикса
    if not wallet.startswith("gonka1"):
        return False, "Неправильный префикс (должен начинаться с 'gonka1')"
    
    # Проверка длины (gonka1 + 38 символов = 44 символа)
    if len(wallet) != 44:
        return False, f"Неправильная длина ({len(wallet)} символов, должно быть 44)"
    
    # Проверка что содержит только допустимые символы (bech32)
    # bech32 использует: 0-9, a-z (без '1', 'b', 'i', 'o')
    if not re.match(r'^gonka1[023456789acdefghjklmnpqrstuvwxyz]{38}$', wallet):
        return False, "Содержит недопустимые символы"
    
    return True, None

def query_validator_info(wallet):
    """
    Запрос информации о валидаторе для кошелька
    Возвращает (jailed, status)
    """
    try:
        cmd = [
            "./inferenced",
            "query",
            "staking",
            "delegator-validators",
            wallet,
            "--node",
            f"{NODE_URL}/chain-rpc/"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"Ошибка при запросе для {wallet}: {result.stderr}", file=sys.stderr)
            return None, None
        
        # Парсинг YAML ответа
        data = yaml.safe_load(result.stdout)
        
        # Проверка на пустой ответ или отсутствие валидаторов
        if not data or 'validators' not in data:
            return None, None
        
        validators = data['validators']
        
        # Если validators = null или пустой список
        if validators is None or len(validators) == 0:
            return None, None
        
        validator = validators[0]
        
        jailed = validator.get('jailed', None)
        status = validator.get('status', None)
        
        # Преобразуем boolean в строку для CSV
        if jailed is not None:
            jailed = str(jailed).lower()
        
        return jailed, status
        
    except subprocess.TimeoutExpired:
        print(f"Таймаут при запросе для {wallet}", file=sys.stderr)
        return None, None
    except yaml.YAMLError as e:
        print(f"Ошибка парсинга YAML для {wallet}: {e}", file=sys.stderr)
        return None, None
    except Exception as e:
        print(f"Неожиданная ошибка для {wallet}: {e}", file=sys.stderr)
        return None, None

def main():
    if len(sys.argv) != 2:
        print("Использование: python script.py <файл_с_кошельками>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Формируем имя выходного файла
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}_results.csv"
    
    # Чтение кошельков из файла
    try:
        with open(input_file, 'r') as f:
            wallets = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Ошибка: файл '{input_file}' не найден")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")
        sys.exit(1)
    
    # Валидация всех кошельков
    valid_wallets = []
    has_errors = False
    
    for wallet in wallets:
        is_valid, error = validate_wallet(wallet)
        if not is_valid:
            print(f"ОШИБКА - Кошелек: {wallet} - {error}", file=sys.stderr)
            has_errors = True
        else:
            valid_wallets.append(wallet)
    
    if has_errors:
        print("\nОбнаружены ошибки валидации. Продолжить с валидными кошельками? (y/n): ", end='', file=sys.stderr)
        response = input().lower()
        if response != 'y':
            sys.exit(1)
    
    # Сбор результатов
    results = []
    
    # Вывод заголовка в stdout
    csv_writer_stdout = csv.writer(sys.stdout)
    csv_writer_stdout.writerow(['address', 'jailed', 'status'])
    
    # Запрос данных для каждого валидного кошелька
    for wallet in valid_wallets:
        print(f"Запрос данных для {wallet}...", file=sys.stderr)
        jailed, status = query_validator_info(wallet)
        
        # Подготовка данных для записи
        row = [
            wallet,
            jailed if jailed is not None else '',
            status if status is not None else ''
        ]
        
        # Запись в stdout
        csv_writer_stdout.writerow(row)
        
        # Сохранение для файла
        results.append(row)
    
    # Запись результатов в файл
    try:
        with open(output_file, 'w', newline='') as f:
            csv_writer_file = csv.writer(f)
            csv_writer_file.writerow(['address', 'jailed', 'status'])
            csv_writer_file.writerows(results)
        print(f"\nРезультаты сохранены в файл: {output_file}", file=sys.stderr)
    except Exception as e:
        print(f"Ошибка при записи в файл {output_file}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
