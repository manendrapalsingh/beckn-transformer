#!/bin/bash
# Installation script for Schema Transformer

set -e

echo "🚀 Setting up Schema Transformer..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip, setuptools, wheel
echo "⬆️  Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel

# Try to install with pre-built wheels first
echo "📥 Installing dependencies (trying pre-built wheels first)..."
if pip install --only-binary :all: -r requirements.txt 2>/dev/null; then
    echo "✅ Installed using pre-built wheels"
else
    echo "⚠️  Pre-built wheels not available, trying standard installation..."
    pip install -r requirements.txt || {
        echo "❌ Installation failed. This might be due to Python 3.14 compatibility issues."
        echo "💡 Suggestions:"
        echo "   1. Use Python 3.12 or 3.13 for better compatibility"
        echo "   2. Or install packages individually:"
        echo "      pip install fastapi uvicorn[standard] pydantic requests python-dotenv"
        exit 1
    }
fi

echo "✅ Installation complete!"
echo ""
echo "To activate the virtual environment in the future, run:"
echo "  source venv/bin/activate"
echo ""
echo "To start the server, run:"
echo "  python -m src.main"

