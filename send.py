#!/usr/bin/env python3

"""
Скрипт для отправки монет GONKA
Использование: ./send_gonka.py <имя_отправителя> <адрес_получателя> <сумма_в_GONKA>
"""

import sys
import os
import subprocess
from pathlib import Path

# Константы
GONKA_TO_NGONKA = 1_000_000_000  # 1 GONKA = 1 000 000 000 ngonka
CHAIN_ID = "gonka-mainnet"
KEYRING_BACKEND = "file"
NODE_URL = "http://net2.gonka.top:8000/chain-rpc/"


def print_usage():
    """Вывод справки по использованию"""
    print("Скрипт для отправки монет GONKA")
    print(f"Использование: {sys.argv[0]} <имя_отправителя> <адрес_получателя> <сумма_в_GONKA>")
    print("\nПримеры:")
    print(f"  {sys.argv[0]} clever-darwin gonka18j6w2kesdq38fv0wtuspjal8lk2q7h7zage7z4 1")
    print(f"  {sys.argv[0]} clever-darwin gonka18j6w2kesdq38fv0wtuspjal8lk2q7h7zage7z4 5.11")
    print(f"  {sys.argv[0]} my-wallet gonka1n6uaty84yezgfcymndq75nmza8y8krt9j0czjm 33.5")


def validate_amount(amount_str):
    """
    Валидация и конвертация суммы из GONKA в ngonka
    
    Args:
        amount_str: строка с суммой в GONKA (может быть с точкой)
    
    Returns:
        int: сумма в ngonka
    """
    try:
        amount_gonka = float(amount_str)
        
        if amount_gonka <= 0:
            print(f"Ошибка: сумма должна быть больше 0 (указано: {amount_str})")
            sys.exit(1)
        
        # Конвертируем в ngonka
        amount_ngonka = int(amount_gonka * GONKA_TO_NGONKA)
        
        if amount_ngonka == 0:
            print(f"Ошибка: сумма слишком мала (минимум 0.000000001 GONKA)")
            sys.exit(1)
        
        return amount_ngonka
        
    except ValueError:
        print(f"Ошибка: неверный формат суммы '{amount_str}'")
        print("Сумма должна быть числом, например: 1, 5.11, 33.5")
        sys.exit(1)


def validate_address(address):
    """
    Базовая валидация адреса GONKA
    
    Args:
        address: адрес кошелька
    
    Returns:
        bool: True если адрес похож на правильный
    """
    if not address.startswith("gonka1"):
        print(f"Предупреждение: адрес получателя не начинается с 'gonka1': {address}")
        response = input("Продолжить? (y/N): ")
        if response.lower() != 'y':
            print("Операция отменена")
            sys.exit(0)
    return True


def find_inferenced():
    """
    Поиск исполняемого файла inferenced
    
    Returns:
        str: путь к файлу inferenced
    """
    # Сначала пробуем стандартный путь
    default_path = Path.home() / "Crypto" / "gonka.ai" / "inferenced"
    
    if default_path.exists():
        return str(default_path)
    
    # Пробуем найти в PATH
    result = subprocess.run(['which', 'inferenced'], 
                          capture_output=True, 
                          text=True)
    
    if result.returncode == 0:
        return result.stdout.strip()
    
    print("Ошибка: не найден исполняемый файл 'inferenced'")
    print(f"Ожидаемый путь: {default_path}")
    print("Или убедитесь, что 'inferenced' доступен в PATH")
    sys.exit(1)


def send_gonka(sender, recipient, amount_ngonka, inferenced_path):
    """
    Отправка монет GONKA
    
    Args:
        sender: имя кошелька отправителя
        recipient: адрес получателя
        amount_ngonka: сумма в ngonka
        inferenced_path: путь к исполняемому файлу inferenced
    """
    amount_gonka = amount_ngonka / GONKA_TO_NGONKA
    
    print("\n" + "="*60)
    print("ОТПРАВКА МОНЕТ GONKA")
    print("="*60)
    print(f"От:          {sender}")
    print(f"Кому:        {recipient}")
    print(f"Сумма:       {amount_gonka} GONKA ({amount_ngonka} ngonka)")
    print(f"Chain ID:    {CHAIN_ID}")
    print(f"Node:        {NODE_URL}")
    print("="*60)
    
    # Формируем команду
    cmd = [
        inferenced_path,
        'tx', 'bank', 'send',
        sender,
        recipient,
        f"{amount_ngonka}ngonka",
        '--chain-id', CHAIN_ID,
        '--keyring-backend', KEYRING_BACKEND,
        '--node', NODE_URL
    ]
    
    print("\nВыполнение команды...")
    print(f"$ {' '.join(cmd)}\n")
    
    # Выполняем команду
    try:
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print("\n✓ Транзакция успешно отправлена!")
        else:
            print(f"\n✗ Ошибка при выполнении транзакции (код: {result.returncode})")
            sys.exit(result.returncode)
            
    except KeyboardInterrupt:
        print("\n\nОперация прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        sys.exit(1)


def main():
    """Главная функция"""
    # Проверка аргументов
    if len(sys.argv) != 4:
        print("Ошибка: неверное количество аргументов\n")
        print_usage()
        sys.exit(1)
    
    sender = sys.argv[1]
    recipient = sys.argv[2]
    amount_str = sys.argv[3]
    
    # Валидация
    validate_address(recipient)
    amount_ngonka = validate_amount(amount_str)
    inferenced_path = find_inferenced()
    
    # Отправка
    send_gonka(sender, recipient, amount_ngonka, inferenced_path)


if __name__ == "__main__":
    main()
