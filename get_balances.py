#!/usr/bin/env python3
import subprocess
import sys

def get_balance(wallet_address, node_url="http://node2.gonka.ai:26657"):
    """Получает баланс кошелька в GONKA"""
    try:
        cmd = [
            "/home/mitch/Crypto/gonka.ai/inferenced", "query", "bank", "balances", 
            wallet_address, "--node", node_url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return None
        
        # Ищем строку с amount
        for line in result.stdout.split('\n'):
            if 'amount:' in line:
                # Извлекаем число из строки вида: - amount: "289148597685"
                amount_str = line.split('"')[1]
                amount_ngonka = int(amount_str)
                amount_gonka = amount_ngonka / 1_000_000_000
                return amount_gonka
        
        return 0.0
    
    except Exception as e:
        print(f"Ошибка при получении баланса {wallet_address}: {e}", file=sys.stderr)
        return None

def main():
    if len(sys.argv) < 2:
        print("Использование: python3 check_balances.py wallets.txt")
        sys.exit(1)
    
    wallet_file = sys.argv[1]
    
    try:
        with open(wallet_file, 'r') as f:
            wallets = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"Файл {wallet_file} не найден!")
        sys.exit(1)
    
    print(f"{'Кошелек':<50} {'Баланс (GONKA)':<15}")
    print("-" * 65)
    
    total_balance = 0.0
    successful_queries = 0
    
    for wallet in wallets:
        balance = get_balance(wallet)
        if balance is not None:
            print(f"{wallet:<50} {balance:>14.2f}")
            total_balance += balance
            successful_queries += 1
        else:
            print(f"{wallet:<50} {'ОШИБКА':>14}")
    
    print("=" * 65)
    print(f"{'ИТОГО:':<50} {total_balance:>14.2f}")
    print(f"\nОбработано кошельков: {successful_queries} из {len(wallets)}")

if __name__ == "__main__":
    main()