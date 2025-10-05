#!/bin/bash

# Exit on error
set -e

echo "🚀 Deploying ShowEasy Chatbot..."

# Pull latest code
echo "📥 Pulling latest code..."
git pull origin master

# Install dependencies with uv
echo "📦 Installing dependencies..."
uv sync

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