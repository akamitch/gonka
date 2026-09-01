#!/bin/bash

HOSTS_FILE="hosts.txt"
OUTPUT_FILE="results.txt"
MAX_PARALLEL=10

> $OUTPUT_FILE

check_host() {
    NAME=$1
    HOST=$2

    echo "Проверка $NAME ($HOST)..."

    RESULT=$(ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 $HOST "curl -s http://localhost:9200/admin/v1/setup/report | jq -r '.checks[] | select(.id == \"active_in_epoch\") | if .status == \"PASS\" then .details.weight else \"not in epoch\" end'" < /dev/null 2>/dev/null)

    if [ -z "$RESULT" ]; then
        RESULT="ERROR"
    fi

    echo "$NAME:$RESULT" >> $OUTPUT_FILE
    echo "$NAME:$RESULT"
}

COUNT=0
while IFS=: read -r NAME HOST; do
    check_host "$NAME" "$HOST" &

    COUNT=$((COUNT + 1))
    if [ $((COUNT % MAX_PARALLEL)) -eq 0 ]; then
        wait
    fi
done < $HOSTS_FILE

wait

echo "Готово!"
