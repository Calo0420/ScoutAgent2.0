#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# ScoutAgent 2.0 — Installer
# Everforth AI Infrastructure Scout
#
# Usage:
#   curl -sSL <raw-url>/install.sh | bash
#   OR: bash install.sh
# ─────────────────────────────────────────────────────────────────────────────
set -e

INSTALL_DIR="/opt/ScoutAgent2.0"
REPO_URL="https://github.com/calo004200-dev/Scouter2.0.git"
VENV="$INSTALL_DIR/.venv"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   Everforth Scout Agent 2.0 — Installer  ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# ── 1. Dependencies ───────────────────────────────────────────────────────────
echo "[1/6] Checking dependencies..."
apt-get update -qq
apt-get install -y -qq git python3 python3-venv python3-pip nmap curl 2>/dev/null
echo "      ✓ system packages ok"

# Docker check
if ! command -v docker &>/dev/null; then
  echo "      Installing Docker..."
  curl -fsSL https://get.docker.com | sh -q
fi
echo "      ✓ docker ok"

# ── 2. Clone / update repo ────────────────────────────────────────────────────
echo "[2/6] Fetching ScoutAgent..."
if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull -q
  echo "      ✓ updated existing install"
else
  git clone -q "$REPO_URL" "$INSTALL_DIR"
  echo "      ✓ cloned repo"
fi

# ── 3. Python venv ────────────────────────────────────────────────────────────
echo "[3/6] Setting up Python environment..."
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$INSTALL_DIR/requirements.txt"
echo "      ✓ venv ready"

# ── 4. .env config ────────────────────────────────────────────────────────────
echo "[4/6] Configuring environment..."
if [ ! -f "$INSTALL_DIR/.env" ]; then
  if [ -f "$(dirname "$0")/CREDENTIALS.md" ]; then
    # Extract .env block from CREDENTIALS.md if present
    echo "      Reading from CREDENTIALS.md..."
    sed -n '/^```env$/,/^```$/p' "$(dirname "$0")/CREDENTIALS.md" | grep -v '```' > "$INSTALL_DIR/.env"
  else
    cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
    echo ""
    echo "  ⚠  No .env file found. Edit $INSTALL_DIR/.env before running:"
    echo "     ANTHROPIC_API_KEY=sk-ant-..."
    echo "     TARGET_HOST=<client-server-ip>"
    echo ""
  fi
fi
echo "      ✓ .env ready"

# ── 5. Self-scan SSH key ──────────────────────────────────────────────────────
echo "[5/6] Setting up local scan key..."
mkdir -p /root/.ssh
if [ ! -f /root/.ssh/scout_local_key ]; then
  ssh-keygen -t ed25519 -f /root/.ssh/scout_local_key -N '' -q
  cat /root/.ssh/scout_local_key.pub >> /root/.ssh/authorized_keys
  chmod 600 /root/.ssh/authorized_keys
  # Accept localhost host key
  ssh -i /root/.ssh/scout_local_key -o StrictHostKeyChecking=accept-new root@localhost exit 2>/dev/null || true
fi
echo "      ✓ local scan key ready"

# ── 6. Start services ─────────────────────────────────────────────────────────
echo "[6/6] Starting services..."
mkdir -p "$INSTALL_DIR/reports"

# Hostile lab (demo misconfigs)
if [ -f "$INSTALL_DIR/hostile-lab/docker-compose.yml" ]; then
  docker compose -f "$INSTALL_DIR/hostile-lab/docker-compose.yml" up -d --quiet-pull 2>/dev/null
  echo "      ✓ hostile lab running (mongo, redis, telnet)"
fi

# UI server
pkill -f "uvicorn server:app" 2>/dev/null || true
sleep 1
cd "$INSTALL_DIR/ui"
nohup "$VENV/bin/uvicorn" server:app --host 0.0.0.0 --port 7070 \
  > "$INSTALL_DIR/ui/server.log" 2>&1 &
sleep 2

# Get local IP for display
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║   ✓  Scout Agent 2.0 is LIVE             ║"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  Dashboard : http://$LOCAL_IP:7070"
echo "  ║  Password  : see CREDENTIALS.md"
echo "  ╠══════════════════════════════════════════╣"
echo "  ║  To run a scan:                          ║"
echo "  ║  cd $INSTALL_DIR"
echo "  ║  export \$(grep -v '^#' .env | xargs)     ║"
echo "  ║  .venv/bin/python agent.py \\             ║"
echo "  ║    --client 'ClientName' \\               ║"
echo "  ║    --host localhost \\                    ║"
echo "  ║    --user root \\                         ║"
echo "  ║    --key /root/.ssh/scout_local_key \\    ║"
echo "  ║    --subnet \$(hostname -I | awk '{print \$1}' | sed 's/\.[0-9]*\$/.0\/24/')"
echo "  ╚══════════════════════════════════════════╝"
echo ""
