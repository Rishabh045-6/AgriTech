# backend/Dockerfile
FROM node:18-alpine

# Install Python and other dependencies for Python scripts
RUN apk add --no-cache python3 py3-pip

WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Create non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001
USER nextjs

# Expose port
EXPOSE 3001

# Start the application
CMD ["npm", "start"]