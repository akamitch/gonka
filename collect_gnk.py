#!/usr/bin/env python3
"""
Сбор GNK с нескольких кошельков на один адрес.

Использование:
    ./collect_gnk.py wallets.txt gonka1...получатель [--dry-run] [--yes]

wallets.txt — по одному имени ключа на строку (пустые строки и # игнорируются).
"""

import argparse
import getpass
import json
import subprocess
import sys
import time
from decimal import Decimal

# ===================== НАСТРОЙКИ =====================
INFERENCED      = "inferenced"                                  # путь к бинарнику
KEYRING_BACKEND = "file"
CHAIN_ID        = "gonka-mainnet"
QUERY_NODE      = "https://node1.gonka.ai:8443/chain-rpc/"                # для балансов и проверки tx
TX_NODE         = "https://node1.gonka.ai:8443/chain-rpc/"      # для отправки
DENOM           = "ngonka"
NGONKA_PER_GNK  = 10**9

gnk_to_left     = Decimal("0.1")   # сколько GNK оставить на кошельке
FEES_NGONKA     = 0                # комиссия в ngonka (0 = не передавать --fees)
CONFIRM_TX      = True             # ждать попадания транзакции в блок
CONFIRM_TIMEOUT = 30               # секунд
# =====================================================

LEAVE_NGONKA = int(gnk_to_left * NGONKA_PER_GNK)


def gnk(n: int) -> str:
    return f"{Decimal(n) / NGONKA_PER_GNK:.9f}".rstrip("0").rstrip(".") + " GNK"


def run(args, password=None, timeout=60):
    """Запуск inferenced; пароль подаётся в stdin (несколько раз — на случай повторного запроса)."""
    stdin = (password + "\n") * 3 if password is not None else None
    p = subprocess.run([INFERENCED] + args, input=stdin, capture_output=True,
                       text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def get_address(name, password):
    rc, out, err = run(["keys", "show", name, "-a", "--keyring-backend", KEYRING_BACKEND], password)
    # адрес — последняя строка, начинающаяся с gonka1 (выше может быть приглашение ввести пароль)
    for line in reversed(out.splitlines()):
        if line.strip().startswith("gonka1"):
            return line.strip(), None
    return None, (err or out or f"rc={rc}").splitlines()[-1]


def get_balance(address):
    rc, out, err = run(["query", "bank", "balances", address, "--node", QUERY_NODE, "-o", "json"])
    if rc != 0:
        return None, (err or out).splitlines()[-1] if (err or out) else f"rc={rc}"
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return None, "не удалось разобрать JSON баланса"
    for c in data.get("balances", []):
        if c.get("denom") == DENOM:
            return int(c["amount"]), None
    return 0, None


def send(name, to_addr, amount, password):
    args = ["tx", "bank", "send", name, to_addr, f"{amount}{DENOM}",
            "--chain-id", CHAIN_ID, "--keyring-backend", KEYRING_BACKEND,
            "--node", TX_NODE, "--yes", "-o", "json"]
    if FEES_NGONKA:
        args += ["--fees", f"{FEES_NGONKA}{DENOM}"]
    rc, out, err = run(args, password, timeout=120)
    # JSON может идти после строки с приглашением пароля
    start = out.find("{")
    if start == -1:
        return None, (err or out or f"rc={rc}").splitlines()[-1]
    try:
        res = json.loads(out[start:])
    except json.JSONDecodeError:
        return None, "не удалось разобрать ответ tx"
    if res.get("code", 0) != 0:
        return None, f"code={res.get('code')}: {res.get('raw_log', '')}"
    return res.get("txhash"), None


def wait_tx(txhash):
    deadline = time.time() + CONFIRM_TIMEOUT
    while time.time() < deadline:
        time.sleep(3)
        rc, out, _ = run(["query", "tx", txhash, "--node", QUERY_NODE, "-o", "json"])
        if rc == 0 and out:
            try:
                res = json.loads(out)
            except json.JSONDecodeError:
                continue
            if res.get("code", 0) == 0:
                return True, f"блок {res.get('height')}"
            return False, f"code={res.get('code')}: {res.get('raw_log', '')}"
    return None, "не подтверждена за отведённое время (проверьте вручную)"


def main():
    ap = argparse.ArgumentParser(description="Перевод GNK с кошельков на один адрес")
    ap.add_argument("wallets_file")
    ap.add_argument("recipient")
    ap.add_argument("--dry-run", action="store_true", help="только показать, ничего не отправлять")
    ap.add_argument("--yes", action="store_true", help="не спрашивать подтверждение")
    a = ap.parse_args()

    if not a.recipient.startswith("gonka1"):
        sys.exit(f"Адрес получателя выглядит неверно: {a.recipient}")

    with open(a.wallets_file, encoding="utf-8") as f:
        names = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]
    if not names:
        sys.exit("Файл с кошельками пуст")

    password = getpass.getpass("Пароль keyring: ")

    # --- 1. Сбор адресов и балансов ---
    plan = []  # (name, address, balance, amount_to_send, error)
    print(f"\nОставляем на кошельках: {gnk(LEAVE_NGONKA)}"
          + (f", комиссия: {gnk(FEES_NGONKA)}" if FEES_NGONKA else "") + "\n")
    for i, name in enumerate(names):
        addr, err = get_address(name, password)
        if not addr:
            if i == 0 and "passphrase" in (err or "").lower():
                sys.exit(f"Ошибка пароля: {err}")
            plan.append((name, None, 0, 0, f"ключ: {err}"))
            print(f"  ✗ {name:<28} ключ не получен: {err}")
            continue
        bal, err = get_balance(addr)
        if bal is None:
            plan.append((name, addr, 0, 0, f"баланс: {err}"))
            print(f"  ✗ {name:<28} баланс не получен: {err}")
            continue
        amount = bal - LEAVE_NGONKA - FEES_NGONKA
        if amount <= 0:
            plan.append((name, addr, bal, 0, "нечего переводить"))
            print(f"  – {name:<28} {addr}  баланс {gnk(bal)} — нечего переводить")
        else:
            plan.append((name, addr, bal, amount, None))
            print(f"  • {name:<28} {addr}  баланс {gnk(bal)} → к отправке {gnk(amount)}")

    to_send = [p for p in plan if p[3] > 0]
    total_planned = sum(p[3] for p in to_send)
    print(f"\nК отправке: {len(to_send)} кошельков, всего {gnk(total_planned)} → {a.recipient}")

    if not to_send or a.dry_run:
        print("Dry-run: ничего не отправлено." if a.dry_run else "Нечего отправлять.")
        return
    if not a.yes and input("Отправить? [y/N]: ").strip().lower() not in ("y", "yes", "д", "да"):
        print("Отменено.")
        return

    # --- 2. Отправка ---
    print()
    ok, failed, unconfirmed, total_sent = [], [], [], 0
    for name, addr, bal, amount, _ in to_send:
        txhash, err = send(name, a.recipient, amount, password)
        if not txhash:
            failed.append((name, amount, err))
            print(f"  ✗ {name:<28} {gnk(amount):>18}  ОШИБКА: {err}")
            continue
        status, info = (True, "") if not CONFIRM_TX else wait_tx(txhash)
        if status is True:
            ok.append((name, amount, txhash))
            total_sent += amount
            print(f"  ✓ {name:<28} {gnk(amount):>18}  {txhash} {info}")
        elif status is None:
            unconfirmed.append((name, amount, txhash))
            print(f"  ? {name:<28} {gnk(amount):>18}  {txhash} {info}")
        else:
            failed.append((name, amount, info))
            print(f"  ✗ {name:<28} {gnk(amount):>18}  ОШИБКА в блоке: {info}")

    # --- 3. Сводка ---
    skipped = [p for p in plan if p[3] <= 0]
    print("\n================ ИТОГ ================")
    print(f"Получатель:        {a.recipient}")
    print(f"Всего кошельков:   {len(plan)}")
    print(f"Успешно:           {len(ok)}")
    print(f"Не подтверждено:   {len(unconfirmed)}" + (f" ({gnk(sum(x[1] for x in unconfirmed))})" if unconfirmed else ""))
    print(f"Ошибки:            {len(failed)}")
    print(f"Пропущено:         {len(skipped)}")
    print(f"ПЕРЕВЕДЕНО:        {gnk(total_sent)}")
    for name, amount, err in failed:
        print(f"  ✗ {name}: {gnk(amount)} — {err}")
    for name, _, _, _, err in skipped:
        print(f"  – {name}: {err}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\nПрервано.")