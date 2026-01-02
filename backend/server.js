require('dotenv').config(); // Add this at the top

const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');


// Use environment variables
const app = express();
const helmet = require('helmet');
const PORT = process.env.PORT || 3001;
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"]
    }
  }
}));

// Security middleware
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Rate limiting
const rateLimit = require('express-rate-limit');
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 500, // Limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
  standardHeaders: true,
  legacyHeaders: false,
});

app.use(limiter);
/* ---------------------------------------------------
   DATABASE
--------------------------------------------------- */
// Database connection using environment variables
const pool = new Pool({
  host: process.env.PGHOST,
  port: Number(process.env.PGPORT),
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  ssl: process.env.NODE_ENV === 'production'
    ? { rejectUnauthorized: false }
    : false,
});

// Security headers
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  next();
});

/* ---------------------------------------------------
   CREATE TABLES
--------------------------------------------------- */
// Create users table
pool.query(`
  CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    farmer_id VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
`).then(() => {
  console.log('✅ Users table ready');
}).catch(err => {
  console.error('❌ Users table creation failed:', err);
});

// Create plots table
pool.query(`
  CREATE TABLE IF NOT EXISTS plots (
    id SERIAL PRIMARY KEY,
    farmer_id VARCHAR(100) NOT NULL,
    plot_geom GEOMETRY(POLYGON, 4326) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
`).then(() => {
  console.log('✅ Plots table ready');
}).catch(err => {
  console.error('❌ Plots table creation failed:', err);
});

/* ---------------------------------------------------
   LOGIN/REGISTER ENDPOINT
--------------------------------------------------- */
const { v4: uuidv4 } = require('uuid'); // Add this import

app.post('/api/login', async (req, res) => {
  try {
    const { username } = req.body;

    // Input validation
    if (!username || typeof username !== 'string' || username.length > 100) {
      return res.status(400).json({ 
        error: 'Invalid username',
        success: false 
      });
    }

    // Sanitize input
    const sanitizedUsername = username.trim().toLowerCase();
    
    // Check if user already exists
    const existingUser = await pool.query(
      'SELECT farmer_id FROM users WHERE username = $1',
      [sanitizedUsername]
    );

    const jwt = require('jsonwebtoken');
    const JWT_SECRET = process.env.JWT_SECRET || 'your_very_long_secret_key_here';


    let farmerId;

    if (existingUser.rows.length > 0) {
      // User exists, return their existing farmer_id
      farmerId = existingUser.rows[0].farmer_id;
      returnedUsername = existingUser.rows[0].username;
      console.log(`Existing user logged in: ${returnedUsername} with ID: ${farmerId}`);
    } else {
      // Create new user with UNIQUE farmer_id
      const timestamp = Date.now();
      const randomString = require('crypto').randomBytes(4).toString('hex');
      farmerId = `farmer_${timestamp}${randomString}`;
      
      await pool.query(
        'INSERT INTO users (username, farmer_id) VALUES ($1, $2)',
        [sanitizedUsername, farmerId]
      );
      returnedUsername = sanitizedUsername;
      console.log(`New user created: ${returnedUsername} with ID: ${farmerId}`);
    }

    const token = jwt.sign(
      { 
        userId: farmerId, 
        username: sanitizedUsername,
        exp: Math.floor(Date.now() / 1000) + (24 * 60 * 60) // 24 hours
      },
      JWT_SECRET
    );
    res.json({
      success: true,
      farmerId: farmerId,
      username: username,
      token: token
    });
  
  } catch (err) {
    console.error('Login error:', err);
    res.status(500).json({ error: 'Failed to process login' });
  }
});

/* ---------------------------------------------------
   GET USER BY FARMER ID
--------------------------------------------------- */
app.get('/api/user/:farmerId', async (req, res) => {
  try {
    const { farmerId } = req.params;

    const result = await pool.query(
      'SELECT username, farmer_id, created_at FROM users WHERE farmer_id = $1',
      [farmerId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'User not found' });
    }

    res.json({
      success: true,
      user: result.rows[0]
    });

  } catch (err) {
    console.error('Get user error:', err);
    res.status(500).json({ error: 'Failed to get user' });
  }
});

/* ---------------------------------------------------
   HELPER
--------------------------------------------------- */
const normalizeFarmerId = (id) =>
  id?.toString().trim().toLowerCase();

/* ---------------------------------------------------
   SAVE PLOT (NO CSV)
--------------------------------------------------- */
app.post('/api/save-plot', async (req, res) => {
  try {
    const { farmerId, plotCoordinates, cropType } = req.body;

    console.log('💾 SAVING PLOT FOR FARMER:', farmerId); // ✅ DEBUG LOG

    if (!farmerId || !Array.isArray(plotCoordinates) || plotCoordinates.length < 3) {
      return res.status(400).json({ error: 'Invalid input' });
    }

    // Close polygon ONLY for PostGIS (not CSV)
    let coordsForPostGIS = plotCoordinates;
    const first = coordsForPostGIS[0];
    const last = coordsForPostGIS[coordsForPostGIS.length - 1];
    if (first[0] !== last[0] || first[1] !== last[1]) {
      coordsForPostGIS = [...coordsForPostGIS, first];
    }

    const wkt = `POLYGON((${coordsForPostGIS.map(pt => `${pt[1]} ${pt[0]}`).join(', ')}))`;

    await pool.query(
      `INSERT INTO plots (farmer_id, plot_geom) 
       VALUES ($1, ST_GeomFromText($2, 4326))`,
      [farmerId, wkt]
    );

    // ✅ NO CSV FILE CREATION OR OPENING
    res.json({ success: true, message: 'Plot saved!', farmerId: farmerId });
  } catch (err) {
    console.error('Backend error:', err);
    res.status(500).json({ error: 'Failed to save plot' });
  }
});

/* ---------------------------------------------------
   ANALYZE CROP (SIMULATED)
--------------------------------------------------- */
app.post('/api/analyze-crop', async (req, res) => {
  try {
    const { farmerId, cropType } = req.body;

    // ✅ Get plot coordinates
    const { rows } = await pool.query(
      `SELECT 
        ST_AsGeoJSON(plot_geom) AS plot_geojson
       FROM plots 
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [farmerId]
    );

    if (rows.length === 0) {
      return res.status(404).json({ error: 'No plot found for this farmer' });
    }

    const coords = JSON.parse(rows[0].plot_geojson).coordinates[0].map(coord => ({
      latitude: coord[1],
      longitude: coord[0]
    }));

    // ✅ Fetch satellite data (simplified for demo)
    // In production, use your data_fetcher.py logic
    const mockData = {
      window_features: [[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.1]],
      window_df: [
        { date: '2025-03-30', NDVI: 0.32 },
        { date: '2025-04-01', NDVI: 0.31 },
        { date: '2025-04-03', NDVI: 0.30 },
        { date: '2025-04-06', NDVI: 0.40 },
        { date: '2025-04-10', NDVI: 0.45 },
        { date: '2025-04-15', NDVI: 0.48 },
        { date: '2025-04-20', NDVI: 0.49 },
        { date: '2025-04-25', NDVI: 0.50 },
      ]
    };

    // ✅ Run model (simulated for now)
    const stageNames = ["Vegetative", "Reproductive", "Ripening"];
    const probabilities = [0.2, 0.8, 0.0]; // Simulate "Reproductive" stage
    const predictedStage = 1; // Reproductive

    // ✅ Return results to app
    res.json({
      success: true,
      cropType: cropType,
      stage: stageNames[predictedStage],
      probability: probabilities[predictedStage],
      ndviTrend: mockData.window_df.map(row => ({ date: row.date, ndvi: row.NDVI })),
      recommendations: [
        "Critical stage - monitor closely for stress",
        "Check for flowering and grain formation",
        "Avoid water stress during grain filling"
      ]
    });

  } catch (err) {
    console.error('Analysis error:', err);
    res.status(500).json({ error: 'Failed to analyze crop' });
  }
});

app.get('/health', async (req, res) => {
  try {
    await pool.query('SELECT 1');
    res.status(200).json({ status: 'ok' });
  } catch {
    res.status(500).json({ status: 'db-error' });
  }
});


/* ---------------------------------------------------
   GET LATEST PLOT
--------------------------------------------------- */
app.get('/api/latest-plot', async (req, res) => {
  try {
    const farmerId = normalizeFarmerId(req.query.farmerId);

    const { rows } = await pool.query(
      `SELECT
        id,
        farmer_id,
        ST_AsGeoJSON(plot_geom) AS geojson,
        ST_Area(plot_geom::geography) AS area_sqm,
        created_at
       FROM plots
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [farmerId]
    );

    if (!rows.length) {
      return res.status(404).json({ error: 'No plot found' });
    }

    const p = rows[0];
    const areaAcres = +(p.area_sqm * 0.000247105).toFixed(2);

    res.json({
      plotId: p.id,
      farmerId: p.farmer_id,
      areaAcres,
      coordinates: JSON.parse(p.geojson).coordinates[0].map(c => ({
        latitude: c[1],
        longitude: c[0]
      })),
      createdAt: p.created_at
    });

  } catch (err) {
    console.error('❌ Fetch error:', err);
    res.status(500).json({ error: 'Failed to fetch plot' });
  }
});

/* ---------------------------------------------------
   GET ALL PLOTS FOR FARMER
--------------------------------------------------- */
app.get('/api/plot-data/:farmerId', async (req, res) => {
  try {
    const farmerId = normalizeFarmerId(req.params.farmerId);

    const { rows } = await pool.query(
      `SELECT
        id,
        farmer_id,
        ST_AsGeoJSON(plot_geom) AS geojson,
        ST_Area(plot_geom::geography) AS area_sqm,
        created_at
       FROM plots
       WHERE farmer_id = $1
       ORDER BY created_at DESC`,
      [farmerId]
    );

    if (!rows.length) {
      return res.status(404).json({ error: 'No plots found' });
    }

    res.json(rows.map(p => ({
      plotId: p.id,
      farmerId: p.farmer_id,
      areaAcres: +(p.area_sqm * 0.000247105).toFixed(2),
      coordinates: JSON.parse(p.geojson).coordinates[0].map(c => ({
        latitude: c[1],
        longitude: c[0]
      })),
      createdAt: p.created_at
    })));

  } catch (err) {
    console.error('❌ Fetch error:', err);
    res.status(500).json({ error: 'Failed to fetch plots' });
  }
});

/* ---------------------------------------------------
   RUN MODEL (NEW - COMPLETE INTEGRATION)
--------------------------------------------------- */
app.post('/api/run-model', async (req, res) => {
  try {
    const { farmerId, cropType } = req.body;

    // Validate inputs
    if (!farmerId || !cropType ) {
      return res.status(400).json({ 
        error: 'Missing required fields',
        success: false
      });
    }

    if (typeof farmerId !== 'string' || typeof cropType !== 'string') {
      return res.status(400).json({ 
        error: 'Invalid field types',
        success: false
      });
    }

    // Sanitize inputs
    const sanitizedFarmerId = farmerId.trim();
    const sanitizedCropType = cropType.trim().toLowerCase();

    // Validate crop type
    const allowedCrops = ['rice', 'wheat', 'maize', 'chickpea', 'pigeon_pea', 'beans', 'lentils'];
    if (!allowedCrops.includes(sanitizedCropType)) {
      return res.status(400).json({ 
        error: 'Invalid crop type',
        success: false
      });
    }
    // Escape special characters to prevent command injection
    const escapedFarmerId = sanitizedFarmerId.replace(/[^a-zA-Z0-9_]/g, '');
    const escapedCropType = sanitizedCropType.replace(/[^a-zA-Z0-9_]/g, '');
    const escapedCoordinates = JSON.stringify(coordinates).replace(/[^a-zA-Z0-9_,\[\]:\{\}\-\.]/g, '');


    console.log('🤖 Running model for:', { farmerId, cropType });

    // Get plot coordinates from database
    const { rows } = await pool.query(
      `SELECT 
        ST_AsGeoJSON(plot_geom) AS plot_geojson
       FROM plots 
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [farmerId]
    );

    if (rows.length === 0) {
      return res.status(404).json({ error: 'No plot found for this farmer' });
    }

    const coordinates = JSON.parse(rows[0].plot_geojson).coordinates[0].map(coord => ({
      latitude: coord[1],
      longitude: coord[0]
    }));

    // ✅ ENCODE coordinates properly to avoid shell splitting
    const { exec } = require('child_process');
    const pythonScript = 'predict_crop_stage.py';

    const command = `python "${pythonScript}" "${escapedFarmerId}" "${escapedCoordinates}"  "${escapedCropType}" `;

    console.log('EXECUTING COMMAND:', command); // Debug log

    exec(command, { cwd: __dirname }, (error, stdout, stderr) => {
      console.log('PYTHON STDOUT:', stdout);
      console.log('PYTHON STDERR:', stderr);
      console.log('PYTHON ERROR:', error);

      if (error) {
        console.error('Python script error:', error);
        return res.status(500).json({
          error: `Python script failed: ${error.message}`,
          success: false
        });
      }

      if (stderr) {
        console.error('Python script stderr:', stderr);
      }

      if (!stdout || stdout.trim() === '') {
        return res.status(500).json({
          error: 'Python script returned no output',
          success: false
        });
      }

      try {
        const result = JSON.parse(stdout.trim());

        if (result.success) {
          // Ensure window_df is properly formatted
          if (result.window_df) {
            // Clean any problematic data
            result.window_df = result.window_df.map(row => {
              const cleanedRow = {};
              for (const [key, value] of Object.entries(row)) {
                if (value === null || value === undefined) {
                  cleanedRow[key] = null;
                } else if (typeof value === 'number' && !isNaN(value)) {
                  cleanedRow[key] = value;
                } else if (typeof value === 'string') {
                  cleanedRow[key] = value;
                } else if (typeof value === 'boolean') {
                  cleanedRow[key] = value;
                } else {
                  cleanedRow[key] = value;
                }
              }
              return cleanedRow;
            });
          }

          res.json(result);
        } else {
          res.status(500).json({
            error: result.error || 'Model prediction failed',
            success: false
          });
        }
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        console.error('Raw output:', stdout);
        res.status(500).json({
          error: `Invalid JSON response from Python script: ${parseError.message}`,
          success: false
        });
      }
    });

  } catch (err) {
    console.error('Model error:', err);
    res.status(500).json({ error: 'Failed to run model' });
  }
});

/* ---------------------------------------------------
   START SERVER
--------------------------------------------------- */
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Server running on http://0.0.0.0:${PORT}`);
});

module.exports = app; // For testing purposes