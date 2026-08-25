#!/usr/bin/env bash
set -u

SERIAL="${1:-}"

if ! command -v adb >/dev/null 2>&1; then
    echo "[!] adb not found"
    exit 1
fi

if [[ -z "$SERIAL" ]]; then
    SERIAL="$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')"
fi

if [[ -z "$SERIAL" ]]; then
    echo "[!] No authorized ADB device found."
    echo
    adb devices -l
    exit 1
fi

ADB=(adb -s "$SERIAL")

echo "=== DEVICE ==="
"${ADB[@]}" shell getprop ro.product.manufacturer
"${ADB[@]}" shell getprop ro.product.model
"${ADB[@]}" shell getprop ro.build.version.release
echo "Serial: $SERIAL"

echo
echo "=== USB/ADB ==="
adb devices -l

echo
echo "=== INTERFACES ==="
"${ADB[@]}" shell 'ip -br addr'

echo
echo "=== ROUTES ==="
"${ADB[@]}" shell 'ip route'

echo
echo "=== DNS ==="
"${ADB[@]}" shell 'getprop | grep -Ei "dns|net.dns|dhcp" || true'

echo
echo "=== WIFI STATE ==="
"${ADB[@]}" shell 'dumpsys wifi | grep -E "mWifiInfo|SSID:|BSSID:|Supplicant state|RSSI:|Link speed:|Frequency:" | tail -80'

echo
echo "=== CELLULAR ==="
"${ADB[@]}" shell 'dumpsys telephony.registry | grep -E "mServiceState|mSignalStrength|mDataConnectionState|mDataNetworkType" | tail -30' || true

echo
echo "=== NEIGHBORS ==="
"${ADB[@]}" shell 'ip neigh'

echo
echo "=== INTERNET: IP ==="
"${ADB[@]}" shell 'ping -c 4 -W 2 1.1.1.1'

echo
echo "=== INTERNET: DNS + HOST ==="
"${ADB[@]}" shell 'ping -c 4 -W 2 google.com'

echo
echo "=== DEFAULT NETWORK ==="
"${ADB[@]}" shell 'dumpsys connectivity | grep -E "NetworkAgentInfo|type:|VALIDATED|CAPABILITIES" | tail -80' || true

echo
echo "=== SUMMARY ==="
"${ADB[@]}" shell '
echo -n "Wi-Fi interface: "
ip -br addr show wlan0 2>/dev/null || true

echo -n "Cellular interface: "
ip -br addr show seth_lte0 2>/dev/null || true

echo -n "Default route: "
ip route | grep "^default" || true
'

echo
echo "[+] Diagnostic complete."
