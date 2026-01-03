FROM node:18-bookworm

# -------------------------
# System dependencies (Python + geo + build)
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

# Make `python` command available
RUN ln -s /usr/bin/python3 /usr/bin/python

# -------------------------
# App directory
# -------------------------
WORKDIR /app

# -------------------------
# Node backend dependencies ONLY
# (CRITICAL: backend path)
# -------------------------
COPY backend/package.json backend/package-lock.json ./
RUN npm ci --omit=dev

# -------------------------
# Python dependencies
# -------------------------
COPY backend/requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt


# -------------------------
# Backend source code
# -------------------------
COPY backend/. .

# -------------------------
# Expose port
# -------------------------
EXPOSE 8080

# -------------------------
# Start server
# -------------------------
CMD ["node", "server.js"]
