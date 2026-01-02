FROM node:18-alpine

RUN apk add --no-cache python3 py3-pip

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY . .

RUN addgroup -S app && adduser -S app -G app
USER app

EXPOSE 3001
CMD ["node", "server.js"]
