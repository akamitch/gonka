#!/bin/bash
export NODE_URL=http://node1.gonka.ai:8000

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка аргументов
if [ "$#" -lt 2 ]; then
    echo -e "${RED}Использование: $0 <файл_с_кошельками> <номер_proposal>${NC}"
    echo "Пример: $0 wallets.txt 22"
    exit 1
fi

WALLETS_FILE="$1"
PROPOSAL_ID="$2"
NODE_URL="${NODE_URL:-}" # Используем переменную окружения или зададим позже

# Проверка существования файла
if [ ! -f "$WALLETS_FILE" ]; then
    echo -e "${RED}Ошибка: файл $WALLETS_FILE не найден${NC}"
    exit 1
fi

# Проверка NODE_URL
if [ -z "$NODE_URL" ]; then
    echo -e "${YELLOW}Переменная NODE_URL не установлена${NC}"
    read -p "Введите NODE_URL (например, https://your-node.com): " NODE_URL
fi

# Запрос пароля один раз
echo -e "${YELLOW}Введите пароль для keyring:${NC}"
read -s PASSWORD
echo

# Счетчики
SUCCESS_COUNT=0
FAIL_COUNT=0
TOTAL_COUNT=0

echo -e "${GREEN}=== Начало голосования ===${NC}"
echo "Proposal ID: $PROPOSAL_ID"
echo "Node URL: $NODE_URL"
echo ""

# Чтение файла построчно
while IFS= read -r wallet || [ -n "$wallet" ]; do
    # Пропускаем пустые строки и комментарии
    [[ -z "$wallet" || "$wallet" =~ ^[[:space:]]*# ]] && continue
    
    # Убираем пробелы в начале и конце
    wallet=$(echo "$wallet" | xargs)
    
    TOTAL_COUNT=$((TOTAL_COUNT + 1))
    
    echo -e "${YELLOW}[$TOTAL_COUNT] Голосование от кошелька: $wallet${NC}"
    
    # Выполняем команду голосования с автоматической передачей пароля
    # после "$PROPOSAL_ID" менять голос
    if echo "$PASSWORD" | /home/mitch/Crypto/gonka.ai/inferenced tx gov vote "$PROPOSAL_ID" no \
        --from "$wallet" \
        --keyring-backend file \
        --unordered \
        --timeout-duration=60s \
        --gas=2000000 \
        --gas-adjustment=5.0 \
        --node "$NODE_URL/chain-rpc/" \
        --chain-id gonka-mainnet \
        --yes 2>&1; then
        
        echo -e "${GREEN}✓ Успешно: $wallet${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
    else
        echo -e "${RED}✗ Ошибка: $wallet${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    
    echo ""
    
    # Небольшая задержка между транзакциями
    sleep 5
    
done < "$WALLETS_FILE"

# Итоговая статистика
echo -e "${GREEN}=== Завершено ===${NC}"
echo "Всего кошельков: $TOTAL_COUNT"
echo -e "${GREEN}Успешно: $SUCCESS_COUNT${NC}"
echo -e "${RED}Ошибок: $FAIL_COUNT${NC}"
