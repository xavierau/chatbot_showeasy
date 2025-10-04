#!/bin/bash

# Exit on error
set -e

echo "🔧 Setting up ShowEasy Chatbot..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3.11 -m venv .venv

# Activate virtual environment
echo "✨ Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -e .

# Create logs directory
mkdir -p logs

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Copy .env.example to .env and configure your environment variables"
echo "2. Run: pm2 start ecosystem.config.js"
echo "   Or run: ./deploy.sh"
