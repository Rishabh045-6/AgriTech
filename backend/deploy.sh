#!/bin/bash

# Production deployment script
echo "Deploying Agritech Backend..."

# Install dependencies
npm install

# Build the application
npm run build

# Start the application
npm start