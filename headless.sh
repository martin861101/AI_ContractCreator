#!/bin/bash

# Setup script for HR Policy Generator on headless servers
# Run this script with sudo privileges

echo "🚀 Setting up HR Policy Generator for headless server..."

# Update package list
echo "📦 Updating package list..."
apt-get update -y

# Install Python and pip if not available
echo "🐍 Installing Python dependencies..."
apt-get install -y python3 python3-pip python3-venv

# Install Chromium and ChromeDriver
echo "🌐 Installing Chromium browser and driver..."
apt-get install -y chromium-browser chromium-chromedriver

# Install additional dependencies for Chromium
echo "🔧 Installing Chromium dependencies..."
apt-get install -y \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libnss3 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcb-dri3-0 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libxtst6 \
    wget \
    xvfb

# Install Python packages
echo "📚 Installing Python packages..."
pip3 install -r requirements.txt

# Verify installations
echo "✅ Verifying installations..."

# Check Chromium
if command -v chromium-browser &> /dev/null; then
    echo "✓ Chromium browser installed: $(chromium-browser --version)"
else
    echo "❌ Chromium browser not found"
fi

# Check ChromeDriver
if command -v chromedriver &> /dev/null; then
    echo "✓ ChromeDriver installed: $(chromedriver --version)"
else
    echo "❌ ChromeDriver not found"
fi

# Check Python packages
echo "✓ Checking Python packages..."
python3 -c "import streamlit, selenium, google.generativeai, requests, dotenv; print('All Python packages installed successfully')"

# Set up environment file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.template .env
    echo "⚠️  Please edit .env file and add your API keys!"
else
    echo "✓ .env file already exists"
fi

# Create startup script
cat > start_app.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting HR Policy Generator..."
echo "📍 Make sure your .env file contains valid API keys"
echo "🌐 The app will be available at: http://localhost:8501"
echo ""
streamlit run hr_policy_generator.py --server.port 8501 --server.address 0.0.0.0
EOF

chmod +x start_app.sh

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file and add your API keys:"
echo "   nano .env"
echo ""
echo "2. Start the application:"
echo "   ./start_app.sh"
echo ""
echo "3. Access the app at: http://your-server-ip:8501"
echo ""
echo "🔧 For manual testing of Chromium:"
echo "   chromium-browser --headless --no-sandbox --dump-dom https://www.google.com"