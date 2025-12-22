FARM PLOT MANAGEMENT APPLICATION
================================

This is a full-stack application for creating, saving, and viewing farm plot
polygons. The system consists of:

1) A Node.js + PostGIS backend (API & data storage)
2) A React Native mobile frontend (primary user app)
3) A Streamlit app (optional data visualization & admin tool)

--------------------------------------------------
FOLDER STRUCTURE
--------------------------------------------------

project-root/
|
|-- backend/
|   |-- server.js            (Node.js backend API)
|   |-- exports/             (Auto-generated CSV files)
|
|-- Frontend/
|   |-- (React Native mobile app)
|
|-- streamlit-app/
|   |-- streamlit_app.py     (Streamlit visualization app)
|   |-- requirements.txt
|
|-- README.txt              (This file)

NOTE:
- CSV files are saved in: backend/exports/

--------------------------------------------------
TECH STACK
--------------------------------------------------

Backend:
- Node.js
- Express
- PostgreSQL
- PostGIS

Frontend (Mobile App):
- React Native
- Fetch / Axios for API calls

Visualization (Optional):
- Python
- Streamlit

--------------------------------------------------
PREREQUISITES
--------------------------------------------------

Install the following before running the app:

1) Node.js (v18 or later)
2) npm or yarn
3) Python (3.9 or later)
4) PostgreSQL (v14 or later)
5) PostGIS extension enabled
6) Android Studio / Xcode (for React Native)

--------------------------------------------------
DATABASE SETUP
--------------------------------------------------

1) Create database:

   CREATE DATABASE farmdb;

2) Enable PostGIS:

   \c farmdb
   CREATE EXTENSION postgis;

The backend automatically creates required tables on startup.

--------------------------------------------------
BACKEND SETUP (NODE.JS)
--------------------------------------------------

1) Navigate to backend folder:

   cd backend

2) Install dependencies:

   npm install express pg cors

3) Update database credentials in server.js if required:

   user: postgres
   host: localhost
   database: farmdb
   password: YOUR_PASSWORD
   port: 5432

4) Start backend server:

   node server.js

Expected output:
   Plots table ready
   Server running on http://localhost:3001

--------------------------------------------------
FRONTEND SETUP (REACT NATIVE)
--------------------------------------------------

1) Navigate to frontend folder:

   cd Frontend

2) Install dependencies:

   npm install
   OR
   yarn install

3) IMPORTANT: Backend URL

   In the React Native app, API calls must point to:

   http://<YOUR_LOCAL_IP>:3001

   Example (Android Emulator):
   http://10.0.2.2:3001

   Example (Physical Device):
   http://192.168.1.5:3001

   DO NOT use localhost on a physical device.

4) Start Metro bundler:

   npm start
   OR
   yarn start

5) Run the app:

   Android:
   npm run android

   iOS:
   npm run ios

--------------------------------------------------
STREAMLIT APP (OPTIONAL)
--------------------------------------------------

The Streamlit app is optional and used for visualization/debugging.

1) Navigate to streamlit folder:

   cd streamlit-app

2) Install dependencies:

   pip install -r requirements.txt

3) Run Streamlit:

   streamlit run streamlit_app.py

--------------------------------------------------
IMPORTANT: FARMER ID RULES
--------------------------------------------------

- Farmer ID is REQUIRED
- Farmer ID is automatically normalized by backend:
  - Trimmed
  - Converted to lowercase

The SAME farmer ID must be used when saving and fetching plots.

Valid examples:
  ramesh
  farmer_123
  john-doe

--------------------------------------------------
API ENDPOINTS
--------------------------------------------------

1) Save Plot
   POST http://<IP>:3001/api/save-plot

   Body:
   {
     "farmerId": "ramesh",
     "plotCoordinates": [
       [28.6129, 77.2295],
       [28.6135, 77.2301],
       [28.6127, 77.2308]
     ]
   }

2) Get Latest Plot
   GET http://<IP>:3001/api/latest-plot?farmerId=ramesh

3) Get All Plots
   GET http://<IP>:3001/api/plot-data/ramesh

4) Download Plot Summary CSV
   GET http://<IP>:3001/api/plot-data/ramesh.csv

--------------------------------------------------
CSV OUTPUT LOCATION
--------------------------------------------------

All CSV files are automatically saved here:

backend/exports/

Example CSV formats:

Plot Coordinates CSV:
farmer_id,latitude,longitude
ramesh,28.6129,77.2295
ramesh,28.6135,77.2301
ramesh,28.6127,77.2308

Plot Summary CSV:
farmer_id,center_lat,center_lng,area_acres
ramesh,28.6130,77.2301,2.34

--------------------------------------------------
COMMON ISSUES
--------------------------------------------------

"No plot found":
- Ensure farmerId is passed in API call
- Ensure same farmerId was used when saving
- Backend server must be running

React Native cannot reach backend:
- Use local IP, not localhost
- Ensure backend is running
- Ensure phone/emulator is on same network

PostGIS errors:
- Ensure PostGIS extension is enabled
- Geometry SRID must be 4326

--------------------------------------------------
NOTES
--------------------------------------------------

- CSV auto-open works only in local development
- Do NOT use auto-open in production
- Streamlit is optional
- React Native app is the primary interface

--------------------------------------------------
QUICK START
--------------------------------------------------

1) Start backend:
   cd backend
   node server.js

2) Start React Native app:
   cd Frontend
   npm start
   npx react-native run-android

(Optional)
3) Start Streamlit:
   cd streamlit-app
   streamlit run streamlit_app.py

--------------------------------------------------
MAINTAINER
--------------------------------------------------

Maintained by Rishabh
