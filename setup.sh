#!/bin/bash

# Wake-up Call Service Setup Script
set -e

echo "🚀 Setting up Wake-up Call Service..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️  Creating environment file..."
    cp env.example .env
    echo "📝 Please edit .env file with your actual configuration values"
fi

# Check if PostgreSQL is available
if ! command -v psql &> /dev/null || ! pg_isready -h localhost -p 5432 &> /dev/null; then
    echo "⚠️  PostgreSQL is not running. For local development, consider using Docker:"
    echo "   docker-compose up -d db redis"
    echo "   Then run this script again or use: docker-compose up --build"
    echo ""
    echo "Alternatively, install and start PostgreSQL manually."
    exit 0
fi

# Run migrations
echo "🗄️  Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "👤 Creating superuser account..."
python manage.py createsuperuser --noinput --username admin --email admin@example.com || echo "Admin user may already exist"

# Seed demo data
echo "🌱 Seeding demo data..."
python manage.py seed_data --count 30

echo "✅ Setup completed!"
echo ""
echo "To start the application:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Set up your .env file with real configuration"
echo "3. Start Redis server: redis-server"
echo "4. Start Celery worker: celery -A wakeupcall worker -l info"
echo "5. Start Celery beat: celery -A wakeupcall beat -l info"
echo "6. Start Django server: python manage.py runserver"
echo ""
echo "Or use Docker: docker-compose up --build"
echo ""
echo "Default admin account: admin / admin123"
