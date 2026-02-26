#!/bin/bash

# Проверка аргументов
if [ $# -lt 2 ]; then
    echo "Использование: $0 <имя_файла> <аккаунт>"
    echo "Пример: $0 2026.01.13_metal9.txt freya"
    exit 1
fi

FILENAME=$1
ACCOUNT=$2
PAYMENTS_PATH="/home/mitch/Crypto/gonka.ai/scripts/payments/${FILENAME}"
TX_PATH="/home/mitch/Crypto/gonka.ai/scripts/tx/${FILENAME}"
PAUSE_SECONDS=60

# Проверка существования входного файла
if [ ! -f "$PAYMENTS_PATH" ]; then
    echo "Ошибка: файл ${PAYMENTS_PATH} не найден!"
    exit 1
fi

# Создание директории tx если не существует
mkdir -p tx

echo "==================================================="
echo "Запуск отправки транзакций..."
echo "Входной файл: ${PAYMENTS_PATH}"
echo "Выходной файл: ${TX_PATH}"
echo "Аккаунт: ${ACCOUNT}"
echo "==================================================="

# Запуск первой команды
/home/mitch/Crypto/gonka.ai/scripts/git_gonka/mass_send_gonka.py "$PAYMENTS_PATH" "$ACCOUNT" > "$TX_PATH"

# Проверка успешности выполнения
if [ $? -ne 0 ]; then
    echo "Ошибка при выполнении mass_send_gonka.py"
    exit 1
fi

echo ""
echo "==================================================="
echo "Транзакции отправлены успешно!"
echo "Пауза ${PAUSE_SECONDS} секунд (2 минуты)..."
echo "==================================================="

# Пауза с обратным отсчетом
for ((i=$PAUSE_SECONDS; i>0; i--)); do
    printf "\rОсталось: %3d секунд" $i
    sleep 1
done
printf "\rПауза завершена!          \n"

echo ""
echo "==================================================="
echo "Запуск верификации транзакций..."
echo "==================================================="

# Запуск второй команды
/home/mitch/Crypto/gonka.ai/scripts/git_gonka/verify_transactions_short.sh "$TX_PATH"

# Проверка успешности выполнения
if [ $? -ne 0 ]; then
    echo "Ошибка при выполнении verify_transactions_short.sh"
    exit 1
fi

echo ""
echo "==================================================="
echo "Готово! Все операции выполнены успешно."
echo "==================================================="
