#!/bin/bash

# Проверка аргументов
if [ $# -eq 0 ]; then
    echo "Usage: $0 <wallets_file> [output_file.csv]"
    echo ""
    echo "Example:"
    echo "  $0 wallets.txt balances.csv"
    echo "  $0 wallets.txt  # outputs to stdout"
    echo ""
    echo "Input file format (one address per line):"
    echo "  gonka18j6w2kesdq38fv0wtuspjal8lk2q7h7zage7z4"
    echo "  gonka1another2address3here4..."
    exit 1
fi

INPUT_FILE="$1"
OUTPUT_FILE="${2:-}"
NODE="http://net2.gonka.top:8000"
DENOM="ngonka"

# Проверка существования файла
if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: File '$INPUT_FILE' not found!"
    exit 1
fi

# Функция для получения баланса
get_balance() {
    local address=$1
    
    # Получаем spendable balance
    local spendable=$(curl -s "$NODE/chain-api/cosmos/bank/v1beta1/balances/$address" 2>/dev/null | \
        jq -r ".balances[]? | select(.denom==\"$DENOM\") | .amount" 2>/dev/null)
    
    # Получаем vesting balance
    local vesting=$(curl -s "$NODE/chain-api/productscience/inference/streamvesting/total_vesting/$address" 2>/dev/null | \
        jq -r ".total_amount[]? | select(.denom==\"$DENOM\") | .amount" 2>/dev/null)
    
    # Если пустые, устанавливаем 0
    [ -z "$spendable" ] || [ "$spendable" == "null" ] && spendable=0
    [ -z "$vesting" ] || [ "$vesting" == "null" ] && vesting=0
    
    # Конвертируем в GONKA
    local spendable_gonka=$(echo "scale=4; $spendable / 1000000000" | bc 2>/dev/null || echo "0")
    local vesting_gonka=$(echo "scale=4; $vesting / 1000000000" | bc 2>/dev/null || echo "0")
    
    echo "$vesting_gonka,$spendable_gonka"
}

# Подготовка вывода
if [ -n "$OUTPUT_FILE" ]; then
    # Записываем в файл
    exec > "$OUTPUT_FILE"
fi

# CSV заголовок
echo "Wallet,Vesting Balance,Spendable Balance"

# Подсчет строк для прогресса
total_lines=$(wc -l < "$INPUT_FILE")
current_line=0

# Обработка каждого адреса
while IFS= read -r address || [ -n "$address" ]; do
    # Пропускаем пустые строки и комментарии
    [[ -z "$address" ]] && continue
    [[ "$address" =~ ^[[:space:]]*# ]] && continue
    
    # Убираем пробелы
    address=$(echo "$address" | tr -d '[:space:]')
    
    # Валидация адреса (должен начинаться с gonka1)
    if [[ ! "$address" =~ ^gonka1[a-z0-9]{38,}$ ]]; then
        echo "$address,ERROR,ERROR" >&2
        continue
    fi
    
    # Показываем прогресс в stderr (если вывод идет в файл)
    if [ -n "$OUTPUT_FILE" ]; then
        current_line=$((current_line + 1))
        echo -ne "Processing: $current_line/$total_lines - $address\r" >&2
    fi
    
    # Получаем балансы
    balances=$(get_balance "$address")
    
    # Выводим результат
    echo "$address,$balances"
    
    # Небольшая пауза чтобы не перегружать API
    sleep 0.1
    
done < "$INPUT_FILE"

# Очищаем строку прогресса
if [ -n "$OUTPUT_FILE" ]; then
    echo -ne "\nDone! Results saved to: $OUTPUT_FILE\n" >&2
fi
