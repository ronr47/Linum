#!/usr/bin/env bash
set -uo pipefail

echo "============================================================"
echo "    🔍 LINUM DEEP NETWORK & GITHUB REPAIR ENGINE            "
echo "============================================================"

# [1/5] Test DNS Resolution
echo "[1/5] Testing DNS resolution for github.com..."
if getent ahostsv4 github.com &>/dev/null; then
    echo "      [✔] IPv4 DNS resolved: $(getent ahostsv4 github.com | head -n 1 | awk '{print $1}')"
else
    echo "      [!] DNS resolution failed. Applying reliable fallback nameservers (Cloudflare/Google)..."
    echo -e "nameserver 1.1.1.1\nnameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null
fi

# [2/5] Test TCP Transport (HTTPS Port 443 & SSH Port 22)
echo "[2/5] Probing transport layer endpoints..."
if timeout 4 bash -c "</dev/tcp/github.com/443" &>/dev/null; then
    echo "      [✔] HTTPS port 443 is reachable."
else
    echo "      [!] Port 443 blocked or timing out."
fi

SSH_BLOCKED=false
if timeout 4 bash -c "</dev/tcp/ssh.github.com/443" &>/dev/null; then
    echo "      [✔] Alternate SSH over 443 (ssh.github.com) is reachable."
else
    SSH_BLOCKED=true
    echo "      [!] Standard SSH port 22 / 443 degraded."
fi

# [3/5] Configure SSH Over HTTPS Port 443 (Firewall Bypass)
echo "[3/5] Enforcing SSH bypass configuration in ~/.ssh/config..."
mkdir -p ~/.ssh
chmod 700 ~/.ssh

cat << 'SSH_CFG' > ~/.ssh/config
Host github.com
    Hostname ssh.github.com
    Port 443
    User git
    StrictHostKeyChecking accept-new
    TCPKeepAlive yes
    ServerAliveInterval 15
    ServerAliveCountMax 3
SSH_CFG
chmod 600 ~/.ssh/config
echo "      [✔] GitHub SSH mapped to fallback port 443."

# [4/5] Fix Git Buffer and Force IPv4
echo "[4/5] Tuning Git network & IPv4 stack..."
git config --global http.postBuffer 524288000
git config --global http.lowSpeedLimit 1000
git config --global http.lowSpeedTime 60
git config --global core.compression 0

# Disable broken system-wide IPv6 route preferences if IPv6 is unreachable
if ! ping -6 -c 1 -W 2 2606:4700:4700::1111 &>/dev/null; then
    echo "      [i] IPv6 route unreachable; forcing IPv4 preference in sysctl..."
    sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1 > /dev/null 2>&1 || true
fi

# [5/5] Final Handshake Verification
echo "[5/5] Performing live GitHub connectivity handshake..."
echo "--- HTTPS Probing ---"
curl -Is --connect-timeout 5 https://github.com | head -n 1 || echo "      [!] HTTPS curl failed."

echo "--- SSH Authentication Probing ---"
ssh -T -o ConnectTimeout=5 git@github.com 2>&1 || true

echo "============================================================"
echo "      DIAGNOSTIC & HOT-REPAIR SEQUENCE COMPLETE             "
echo "============================================================"
