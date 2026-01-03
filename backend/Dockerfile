FROM node:18-alpine

WORKDIR /app

# Copy ONLY backend package files
COPY backend/package.json backend/package-lock.json ./

# Install backend dependencies only
RUN npm ci --omit=dev

# Copy ONLY backend source code
COPY backend/. .

EXPOSE 8080

CMD ["node", "server.js"]
