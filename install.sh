#!/bin/bash

echo "🔄 Updating system packages..."
sudo apt update -y

echo "📦 Installing required dependencies..."
sudo apt install -y python3-tk python3-pip

echo "🐍 Installing Python packages..."
pip3 install --upgrade pip
pip3 install PyQt5

echo "⚙️ Setting execute permissions..."
chmod +x anonmode.sh tajir_anonmode_fullgui.py

echo "✅ Installation complete!"
echo "🚀 Launching Tajir AnonMode GUI..."
sleep 2
python3 tajir_anonmode_fullgui.py
