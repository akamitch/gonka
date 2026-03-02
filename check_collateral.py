#!/usr/bin/env python3

import subprocess
import sys
import os
import re

RED = "\033[91m"
RESET = "\033[0m"

def get_collateral(address, node_url):
    cmd = [
        "./inferenced", "query", "collateral", "show-collateral",
        address,
        "--node", f"{node_url}/chain-rpc/"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        # Parse amount from output like:
        # amount:
        #   amount: "1620000"
        #   denom: ngonka
        match = re.search(r'amount:\s*"(\d+)"', output)
        if match:
            return match.group(1)
        return "NOT_FOUND"
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR:{e}"

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <input_file> [NODE_URL]")
        sys.exit(1)

    input_file = sys.argv[1]
    node_url = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("NODE_URL", "http://node1.gonka.ai:8000")

    if not node_url:
        print("Error: NODE_URL not set. Pass as 2nd argument or set NODE_URL env var.")
        print("Default: http://node1.gonka.ai:8000")
        sys.exit(1)

    with open(input_file, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            address = parts[0]
            expected = parts[1]

            actual = get_collateral(address, node_url)

            output = f"{address} {expected} {actual}"
            if expected != actual:
                print(f"{RED}{output}{RESET}")
            else:
                print(output)

if __name__ == "__main__":
    main()