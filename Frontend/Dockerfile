# frontend/Dockerfile
FROM node:18-alpine

WORKDIR /app

# Install React Native dependencies
RUN apk add --no-cache openjdk11 git

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Expose port for Metro bundler
EXPOSE 8081

# Start Metro bundler
CMD ["npx", "react-native", "start", "--reset-cache"]