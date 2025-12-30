FROM node:18-alpine

WORKDIR /app

# Install Python and system dependencies
RUN apk add --no-cache python3 py3-pip python3-dev g++ make

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 3001

CMD ["npm", "start"]