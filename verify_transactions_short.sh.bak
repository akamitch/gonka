#!/bin/bash

# Скрипт для проверки транзакций в блокчейне gonka.ai
# Использование: ./verify_transactions.sh <файл_с_транзакциями>

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка аргументов
if [ $# -eq 0 ]; then
    echo "Использование: $0 <файл_с_транзакциями>"
    echo "Формат файла: адрес сумма статус txhash: хеш"
    exit 1
fi

INPUT_FILE=$1
NODE="http://net2.gonka.top:8000/chain-rpc/"
INFERENCED="/home/mitch/Crypto/gonka.ai/inferenced"

# Проверка существования файла
if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}Ошибка: файл $INPUT_FILE не найден${NC}"
    exit 1
fi

# Проверка наличия inferenced
if [ ! -f "$INFERENCED" ]; then
    echo -e "${RED}Ошибка: inferenced не найден в текущей директории${NC}"
    exit 1
fi

echo "Проверка транзакций в gonka.ai"
echo "======================================"

# Функция для получения информации о транзакции
get_tx_info() {
    local txhash=$1
    $INFERENCED query tx "$txhash" --node "$NODE" --output json 2>/dev/null
}

# Функция для извлечения суммы из транзакции
extract_amount() {
    local tx_json=$1
    
    # Извлекаем сумму напрямую из сообщения
    local amount_raw=$(echo "$tx_json" | jq -r '.tx.body.messages[0].amount[0].amount // empty')
    
    if [ -n "$amount_raw" ]; then
        # Конвертируем и форматируем с ведущим нулем
        echo "$amount_raw" | awk '{
            val = $1/1000000000;
            if (val < 1 && val > 0) {
                printf "0%.2f", val;
            } else {
                printf "%.2f", val;
            }
        }'
    else
        echo "0.00"
    fi
}

# Функция для извлечения адреса получателя
get_recipient() {
    local tx_json=$1
    echo "$tx_json" | jq -r '.tx.body.messages[0].to_address // empty'
}

# Функция для извлечения адреса отправителя
get_sender() {
    local tx_json=$1
    echo "$tx_json" | jq -r '.tx.body.messages[0].from_address // empty'
}

# Счетчики
total=0
success=0
failed=0
mismatch=0

# Обработка файла
while IFS= read -r line; do
    # Пропускаем пустые строки
    [ -z "$line" ] && continue
    
    # Парсинг строки
    address=$(echo "$line" | awk '{print $1}')
    expected_amount=$(echo "$line" | awk '{print $2}')
    status=$(echo "$line" | awk '{print $3}')
    txhash=$(echo "$line" | awk '{print $5}')
    
    total=$((total + 1))
    
    # Сокращенный хеш для вывода
    txhash_short=$(echo "$txhash" | cut -c1-10)
    
    # Получаем данные транзакции
    tx_data=$(get_tx_info "$txhash")
    
    if [ -z "$tx_data" ]; then
        echo -e "#$total Tx: ${txhash_short}... ${RED}ОШИБКА: Транзакция не найдена${NC}"
        failed=$((failed + 1))
        continue
    fi
    
    # Проверяем статус транзакции
    tx_code=$(echo "$tx_data" | jq -r '.code // 0')
    
    if [ "$tx_code" != "0" ]; then
        echo -e "#$total Tx: ${txhash_short}... ${RED}ОШИБКА: code=$tx_code${NC}"
        failed=$((failed + 1))
        continue
    fi
    
    # Извлекаем реальную сумму и адреса
    actual_amount=$(extract_amount "$tx_data")
    recipient=$(get_recipient "$tx_data")
    
    # Проверка соответствия получателя
    if [ "$recipient" != "$address" ]; then
        echo -e "#$total Tx: ${txhash_short}... ${RED}ОШИБКА: Адрес получателя не совпадает${NC}"
        failed=$((failed + 1))
        continue
    fi
    
    # Проверка что сумма была извлечена
    if [ -z "$actual_amount" ] || [ "$actual_amount" == "0.00" ]; then
        echo -e "#$total Tx: ${txhash_short}... ${RED}ОШИБКА: Не удалось извлечь сумму${NC}"
        failed=$((failed + 1))
        continue
    fi
    
    # Сравнение сумм
    expected_int=$(echo "$expected_amount * 100" | bc | cut -d. -f1)
    actual_int=$(echo "$actual_amount * 100" | bc | cut -d. -f1)
    
    if [ "$expected_int" == "$actual_int" ]; then
        echo -e "#$total Tx: ${txhash_short}... $actual_amount GONKA ${GREEN}OK: Суммы совпадают${NC}"
        success=$((success + 1))
    else
        echo -e "#$total Tx: ${txhash_short}... $actual_amount GONKA ${YELLOW}ОШИБКА: Ожидалось $expected_amount GONKA${NC}"
        mismatch=$((mismatch + 1))
    fi
    
done < "$INPUT_FILE"

# Итоговая статистика
echo ""
echo "======================================"
echo "Всего: $total | Успешно: $success | Не совпадают: $mismatch | Ошибки: $failed"
echo "======================================"
