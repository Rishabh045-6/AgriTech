#!/bin/bash

# Setup script for new deployments
echo "Setting up Agritech Backend..."

# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3 python3-pip postgresql postgresql-contrib

# Install Node.js dependencies
npm install

# Setup database
sudo -u postgres psql -c "CREATE DATABASE agritech;"
sudo -u postgres psql -c "CREATE USER agritech_user WITH PASSWORD 'your_secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE agritech TO agritech_user;"

echo "Setup complete!"