#!/bin/bash
# Validator keys backup for Gonka chain
# Backs up critical validator files with versioned archive
#
# Usage: ./backup_validator.sh
#        ./backup_validator.sh /custom/path/.inference
#
# Files backed up:
#   - priv_validator_key.json  (CRITICAL - validator identity)
#   - priv_validator_state.json (prevents double-signing)
#   - node_key.json (P2P identity)
#   - keyring-file/ (account keys)
#   - TMKMS files if present
#
# Restore:
#   cp ~/backup_validator/priv_validator_key.json /root/gonka/deploy/join/.inference/config/

CHAIN_HOME="${1:-/root/gonka/deploy/join/.inference}"
TMKMS_HOME="${TMKMS_HOME:-$HOME/.tmkms}"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backup_validator}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

[[ "$1" == "-h" || "$1" == "--help" ]] && { echo "Usage: $0 [CHAIN_HOME]"; exit 0; }

echo "Backup: $CHAIN_HOME -> $BACKUP_DIR"
mkdir -p "$BACKUP_DIR/archive"

# Copy file to backup dir and archive with timestamp
backup_file() {
    local src="$1" name="$2"
    cp "$src" "$BACKUP_DIR/$name" 2>/dev/null || return 1
    cp "$src" "$BACKUP_DIR/archive/${name%.*}_${TIMESTAMP}.${name##*.}" 2>/dev/null
}

# Validator key (try chain home first, then TMKMS)
backup_file "$CHAIN_HOME/config/priv_validator_key.json" "priv_validator_key.json" || \
backup_file "$TMKMS_HOME/secrets/priv_validator_key.json" "priv_validator_key.json" || \
echo "[ERR] priv_validator_key.json NOT FOUND - this is critical!"

# State file (prevents double-signing)
backup_file "$CHAIN_HOME/data/priv_validator_state.json" "priv_validator_state.json" || \
backup_file "$TMKMS_HOME/state/priv_validator_state.json" "priv_validator_state.json"

# Optional files
backup_file "$CHAIN_HOME/config/node_key.json" "node_key.json"
backup_file "$TMKMS_HOME/secrets/priv_validator_key.softsign" "priv_validator_key.softsign"
backup_file "$TMKMS_HOME/tmkms.toml" "tmkms.toml"
cp -r "$CHAIN_HOME/keyring-file" "$BACKUP_DIR/" 2>/dev/null

# Generate checksums for verification
cd "$BACKUP_DIR" && sha256sum *.json *.toml 2>/dev/null > checksums.sha256

echo "Done: $BACKUP_DIR"
echo "Archive versions: $(ls -1 "$BACKUP_DIR/archive" 2>/dev/null | wc -l)"
echo ""
echo "Add to cron (every 6 hours):"
echo "  0 */6 * * * $0 $CHAIN_HOME >> /var/log/backup_validator.log 2>&1"
