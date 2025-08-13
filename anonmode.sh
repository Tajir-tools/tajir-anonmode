#!/bin/bash
# Anonymous Mode Auto Script for Kali Linux
# Interface: eth0

# Colors
GREEN="\e[32m"
RED="\e[31m"
NC="\e[0m"

echo -e "${GREEN}[*] Starting Anonymous Mode...${NC}"

# Step 1: MAC Address Spoof
echo -e "${GREEN}[+] Spoofing MAC Address for eth0...${NC}"
sudo ip link set eth0 down
sudo macchanger -r eth0
sudo ip link set eth0 up

# Step 2: Start Tor Service
echo -e "${GREEN}[+] Starting Tor service...${NC}"
sudo apt-get install -y tor proxychains4
sudo systemctl start tor
sudo systemctl enable tor

# Step 3: Configure ProxyChains
echo -e "${GREEN}[+] Configuring ProxyChains to use Tor...${NC}"
sudo sed -i 's/^#socks4\s\+127\.0\.0\.1\s\+9050/socks5 127.0.0.1 9050/' /etc/proxychains4.conf
sudo sed -i 's/^#dynamic_chain/dynamic_chain/' /etc/proxychains4.conf
sudo sed -i 's/^strict_chain/#strict_chain/' /etc/proxychains4.conf

# Step 4: Launch Privacy Tools
echo -e "${GREEN}[+] Launching Tor Browser & Hardened Firefox...${NC}"
proxychains4 firefox https://ipleak.net &
torbrowser-launcher &

# Step 5: Clear Logs & History
echo -e "${GREEN}[+] Clearing Bash history & temp files...${NC}"
history -c
shred -u ~/.bash_history
rm -rf /tmp/* /var/tmp/*

# Step 6: Finished
echo -e "${GREEN}[✓] Anonymous Mode Activated! You are now under the hood.${NC}"
