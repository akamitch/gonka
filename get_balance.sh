#!/bin/bash

# Скрипт для проверки баланса кошелька GONKA
# Использование: ./check_gonka_balance.sh <адрес_кошелька>

# Проверка наличия параметра
if [ -z "$1" ]; then
    echo "Ошибка: не указан адрес кошелька"
    echo "Использование: $0 <адрес_кошелька>"
    echo "Пример: $0 gonka1n6uaty84yezgfcymndq75nmza8y8krt9j0czjm"
    exit 1
fi

# Адрес кошелька из параметра
WALLET_ADDRESS="$1"

# Путь к исполняемому файлу
INFERENCED="$HOME/Crypto/gonka.ai/inferenced"

# Проверка существования исполняемого файла
if [ ! -f "$INFERENCED" ]; then
    echo "Ошибка: не найден файл $INFERENCED"
    exit 1
fi

# Выполнение запроса баланса
echo "Запрос баланса для адреса: $WALLET_ADDRESS"
echo "---"

$INFERENCED query bank balances "$WALLET_ADDRESS" --node http://net2.gonka.top:8000/chain-rpc/ | \
    grep amount | \
    awk '{gsub(/"/, "", $3); printf "%.1f GONKA\n", $3/1000000000}'

# Проверка успешности выполнения
if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo "Ошибка при выполнении запроса"
    exit 1
fi
