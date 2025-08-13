#!/bin/bash
sudo apt update
sudo apt install -y python3-tk python3-pip
pip3 install PyQt5
chmod +x anonmode.sh tajir_anonmode_fullgui.py
echo "✅ Installation complete. Run GUI with: python3 tajir_anonmode_fullgui.py"
