FROM node:18-bookworm

# -------------------------
# Install system dependencies
# -------------------------
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Make python available as "python"
RUN ln -s /usr/bin/python3 /usr/bin/python

# -------------------------
# Set working directory
# -------------------------
WORKDIR /app

# -------------------------
# Install Node dependencies
# -------------------------
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# -------------------------
# Install Python dependencies
# -------------------------
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# -------------------------
# Copy app source
# -------------------------
COPY . .

# -------------------------
# Expose port (Koyeb uses this)
# -------------------------
EXPOSE 8080

# -------------------------
# Start server
# -------------------------
CMD ["node", "server.js"]
