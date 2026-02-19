require('dotenv').config();

const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3001;

// Security middleware
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true
}));
app.use(express.json({ limit: '10mb' }));

// Database connection
const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: Number(process.env.DB_PORT) || 5432,
  database: process.env.DB_NAME || 'agritech',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || '',
});

// Test database connection
pool.on('error', (err) => {
  console.error('❌ Database connection error:', err);
});

async function testConnection() {
  try {
    await pool.query('SELECT 1');
    console.log('✅ Database connected successfully');
  } catch (err) {
    console.error('❌ Database connection failed:', err);
    process.exit(1);
  }
}

testConnection();

// Create tables
async function initTables() {
  try {
    // Enable PostGIS
    await pool.query(`CREATE EXTENSION IF NOT EXISTS postgis;`);
    
    // Create users table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) NOT NULL,
        farmer_id VARCHAR(100) UNIQUE NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
      );
    `);

    // Create plots table
    await pool.query(`
      CREATE TABLE IF NOT EXISTS plots (
        id SERIAL PRIMARY KEY,
        farmer_id VARCHAR(100) NOT NULL,
        plot_geom GEOMETRY(POLYGON, 4326) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
      );
    `);

    console.log('✅ Database tables ready');
  } catch (err) {
    console.error('❌ Table creation failed:', err);
    process.exit(1);
  }
}

initTables();

// UUID generator
const { v4: uuidv4 } = require('uuid');

// Login endpoint
app.post('/api/login', async (req, res) => {
  try {
    const { username } = req.body;

    if (!username || typeof username !== 'string' || username.length > 100) {
      return res.status(400).json({
        success: false,
        error: 'Invalid username'
      });
    }

    const sanitizedUsername = username.trim().toLowerCase();

    // Check if user exists
    const existingUser = await pool.query(
      'SELECT farmer_id FROM users WHERE username = $1',
      [sanitizedUsername]
    );

    let farmerId;

    if (existingUser.rows.length > 0) {
      farmerId = existingUser.rows[0].farmer_id;
      console.log(`✅ Returning existing user: ${sanitizedUsername}`);
    } else {
      // Create new user
      const randomString = crypto.randomBytes(4).toString('hex');
      farmerId = `farmer_${Date.now()}_${randomString}`;

      await pool.query(
        'INSERT INTO users (username, farmer_id) VALUES ($1, $2)',
        [sanitizedUsername, farmerId]
      );

      console.log(`✅ Created new user: ${sanitizedUsername}`);
    }

    res.json({
      success: true,
      farmerId: farmerId,
      username: sanitizedUsername
    });

  } catch (err) {
    console.error('❌ Login error:', err);
    res.status(500).json({
      success: false,
      error: 'Failed to process login'
    });
  }
});

// Save plot endpoint
app.post('/api/save-plot', async (req, res) => {
  try {
    const { farmerId, plotCoordinates, cropType } = req.body;

    console.log('💾 Saving plot for farmer:', farmerId);

    if (!farmerId || !Array.isArray(plotCoordinates) || plotCoordinates.length < 3) {
      return res.status(400).json({ error: 'Invalid input' });
    }

    // Convert coordinates to WKT format
    const coords = plotCoordinates.map(coord => {
      // Handle both {longitude, latitude} and [lon, lat] formats
      if (Array.isArray(coord)) {
        return `${coord[0]} ${coord[1]}`;
      } else {
        return `${coord.longitude} ${coord.latitude}`;
      }
    });

    // Close polygon if not already closed
    const first = coords[0];
    const last = coords[coords.length - 1];
    if (first !== last) {
      coords.push(first);
    }

    const wkt = `POLYGON((${coords.join(', ')}))`;

    await pool.query(
      `INSERT INTO plots (farmer_id, plot_geom) 
       VALUES ($1, ST_GeomFromText($2, 4326))`,
      [farmerId, wkt]
    );

    res.json({ success: true, message: 'Plot saved!', farmerId: farmerId });

  } catch (err) {
    console.error('❌ Save plot error:', err);
    res.status(500).json({ error: 'Failed to save plot' });
  }
});

// Run model endpoint
app.post('/api/run-model', async (req, res) => {
  try {
    const { farmerId, cropType } = req.body;

    if (!farmerId || !cropType) {
      return res.status(400).json({
        success: false,
        error: 'farmerId and cropType are required'
      });
    }

    // Fetch plot coordinates from database
    const { rows } = await pool.query(
      `SELECT ST_AsGeoSON(plot_geom) AS plot_geojson
       FROM plots
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [farmerId.trim()]
    );

    if (!rows.length) {
      return res.status(404).json({
        success: false,
        error: 'No plot found for this farmer'
      });
    }

    // Convert GeoJSON to coordinates
    const geojson = JSON.parse(rows[0].plot_geojson);
    const coordinates = geojson.coordinates[0].map(coord => ({
      latitude: coord[1],
      longitude: coord[0]
    }));

    console.log("🤖 Running Python model for:", { farmerId, cropType });

    // Spawn Python process
    const pythonProcess = spawn('python', [
      'predict_crop_stage.py',
      farmerId.trim(),
      cropType.trim().toLowerCase(),
      JSON.stringify(coordinates)
    ], {
      cwd: __dirname,
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let output = '';
    let errorOutput = '';

    pythonProcess.stdout.on('data', (data) => {
      output += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
      errorOutput += data.toString();
      console.error('🐍 Python stderr:', data.toString());
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        console.error('❌ Python process exited with code:', code);
        console.error('❌ Python stderr:', errorOutput);
        return res.status(500).json({
          success: false,
          error: `Python model execution failed with code ${code}`
        });
      }

      try {
        const result = JSON.parse(output.trim());
        res.json(result);
      } catch (parseError) {
        console.error('❌ Failed to parse Python output:', output);
        res.status(500).json({
          success: false,
          error: 'Invalid JSON response from Python model'
        });
      }
    });

    pythonProcess.on('error', (err) => {
      console.error('❌ Python process error:', err);
      res.status(500).json({
        success: false,
        error: 'Failed to start Python process'
      });
    });

  } catch (err) {
    console.error('❌ Run model error:', err);
    res.status(500).json({
      success: false,
      error: 'Failed to run model'
    });
  }
});

app.post('/api/generate-recommendations', async (req, res) => {
  
  const { plotId, farmerId, plotFeatures } = req.body; // Receive plot data and farmerId from frontend

  if (!plotId || !plotFeatures) { // farmerId might be optional initially
    return res.status(400).json({ error: 'plotId and plotFeatures are required' });
  }

  // Prepare data to send to Python script (as JSON string)
  const inputData = {
    plot_id: plotId,
    farmer_id: farmerId, // Pass farmerId if available
    current_crop: plotFeatures.current_crop || null,
    last_updated: plotFeatures.last_updated || null,
    // ... other fields like current_crop, last_updated if needed by decision_engine...
    features_data: plotFeatures // Pass the features data object
  };

  const pythonScriptPath = path.join(__dirname, 'decision_engine.py'); // Path to your Python script

  console.log(`Calling Python script: python ${pythonScriptPath} with data:`, JSON.stringify(inputData, null, 2));

  const pythonProcess = spawn('python', [pythonScriptPath, JSON.stringify(inputData)]); // Pass data as argument

  let outputData = '';
  let errorOutput = '';

  pythonProcess.stdout.on('data', (data) => {
    outputData += data.toString();
  });

  pythonProcess.stderr.on('data', (data) => {
    errorOutput += data.toString();
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python script exited with code ${code}`);
    console.log(`Python stdout: ${outputData}`);
    console.log(`Python stderr: ${errorOutput}`);

    if (code !== 0) {
      console.error('Python script error:', errorOutput);
      return res.status(500).json({ error: `Python script failed with code ${code}`, details: errorOutput });
    }

    try {
      const result = JSON.parse(outputData.trim());
      if (result.error) {
        console.error('Error from Python logic:', result.error);
        return res.status(500).json(result); // Return error from Python logic
      }
      console.log('Recommendations generated successfully:', result.plot_id);
      res.json(result); // Send recommendations back to frontend
    } catch (parseErr) {
      console.error('Error parsing Python output:', parseErr);
      console.error('Raw output was:', outputData);
      res.status(500).json({ error: 'Failed to parse recommendation output from Python script' });
    }
  });
});

// Get latest plot
app.get('/api/latest-plot', async (req, res) => {
  try {
    const { farmerId } = req.query;

    if (!farmerId) {
      return res.status(400).json({ error: 'farmerId is required' });
    }

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
      coordinates: JSON.parse(p.geojson).coordinates[0].map(coord => ({
        latitude: coord[1],
        longitude: coord[0]
      })),
      createdAt: p.created_at
    });

  } catch (err) {
    console.error('❌ Get latest plot error:', err);
    res.status(500).json({ error: 'Failed to fetch plot' });
  }
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
});

console.log('✅ Server started successfully!');