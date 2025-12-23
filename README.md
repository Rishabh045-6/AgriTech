# Agritech Mobile Application

## Backend Setup

### Environment Variables
Create `.env` file with:

DB_HOST=localhost
DB_PORT=5432
DB_NAME=agritech
DB_USER=postgres
DB_PASSWORD=your_password
SENTINEL_CLIENT_1_ID=your_client_id
SENTINEL_CLIENT_1_SECRET=your_client_secret
PORT=3001


### Installation
```bash
cd backend
npm install
npm start

### Docker Deployment
docker-compose up -d

###Frontend Setup
cd frontend
npm install
npx react-native run-android

####
API Endpoints
POST /api/run-model - Run crop analysis
POST /api/save-plot - Save plot coordinates
GET /api/plot-data/:farmerId - Get plot data