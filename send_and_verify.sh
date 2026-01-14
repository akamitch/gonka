#!/bin/bash

# Проверка аргументов
if [ $# -eq 0 ]; then
    echo "Использование: $0 <имя_файла>"
    echo "Пример: $0 2026.01.13_metal9.txt"
    exit 1
fi

FILENAME=$1
PAYMENTS_PATH="payments/${FILENAME}"
TX_PATH="tx/${FILENAME}"
ACCOUNT="freya"
PAUSE_SECONDS=120

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
git_gonka/mass_send_gonka.py "$PAYMENTS_PATH" "$ACCOUNT" > "$TX_PATH"

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
git_gonka/verify_transactions_short.sh "$TX_PATH"

# Проверка успешности выполнения
if [ $? -ne 0 ]; then
    echo "Ошибка при выполнении verify_transactions_short.sh"
    exit 1
fi

echo ""
echo "==================================================="
echo "Готово! Все операции выполнены успешно."
echo "==================================================="