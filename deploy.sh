#!/bin/bash

# Exit on error
set -e

echo "🚀 Deploying ShowEasy Chatbot..."

# Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3.11 -m venv .venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

# Create logs directory if it doesn't exist
mkdir -p logs

# Reload PM2 app (creates if doesn't exist, restarts if exists)
echo "🔄 Reloading PM2 app..."
pm2 startOrReload ecosystem.config.js

# Save PM2 process list and resurrect on reboot
pm2 save

echo "✅ Deployment complete!"
echo "📊 Check status: pm2 status"
echo "📝 View logs: pm2 logs showeasy-chatbot"