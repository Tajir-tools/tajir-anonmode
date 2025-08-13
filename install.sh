#!/bin/bash

# Install dependencies
sudo apt update
sudo apt install -y python3-tk
pip install PyQt5

# Run the GUI
python3 tajir_anonmode_fullgui.py
