#!/bin/bash
# PROJECT CHAKRA - Oracle Cloud VPS Setup Script
# Run this on your Oracle Cloud Ubuntu server
# Oracle Cloud Free Tier: Always Free - AMD VM.Standard.E2.1.Micro (1 OCPU, 1GB RAM)

echo "========================================================"
echo "PROJECT CHAKRA - Oracle Cloud VPS Setup"
echo "========================================================"

# Update system
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Python 3.11
sudo apt-get install -y python3.11 python3.11-pip python3.11-venv

# Install git
sudo apt-get install -y git

# Install screen (to keep system running after logout)
sudo apt-get install -y screen

# Clone your repo
git clone https://github.com/lovidocmaster/project-chakra.git
cd project-chakra

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask flask-cors gunicorn python-dotenv requests
pip install oandapyV20 supabase numpy pandas yfinance
pip install anthropic scikit-learn tensorflow

# Create .env file
cat > .env << 'EOF'
OANDA_TOKEN=your_token_here
OANDA_ACCOUNT_ID=101-001-39217670-001
OANDA_BASE_URL=https://api-fxpractice.oanda.com
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
SUPABASE_URL=https://jvnaphbygmqjeyawkmnz.supabase.co
SUPABASE_KEY=your_key_here
ALPHA_VANTAGE=T7TQAX2SMD7RTNXN
ANTHROPIC_API_KEY=your_key_here
EOF

echo "Edit .env file with your credentials before starting"

# Create systemd service for auto-restart
sudo tee /etc/systemd/system/chakra.service > /dev/null << 'EOF'
[Unit]
Description=Project Chakra Trading System
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/project-chakra
Environment=PATH=/home/ubuntu/project-chakra/venv/bin
ExecStart=/home/ubuntu/project-chakra/venv/bin/python v15_chakra.py
Restart=always
RestartSec=10
StandardOutput=append:/home/ubuntu/chakra.log
StandardError=append:/home/ubuntu/chakra_error.log

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable chakra
sudo systemctl start chakra

echo ""
echo "========================================================"
echo "SETUP COMPLETE!"
echo "========================================================"
echo "Commands:"
echo "  sudo systemctl status chakra    - Check if running"
echo "  sudo systemctl stop chakra      - Stop trading"
echo "  sudo systemctl start chakra     - Start trading"
echo "  tail -f /home/ubuntu/chakra.log - View live logs"
echo "========================================================"
