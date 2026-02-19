require('dotenv').config();

const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const crypto = require('crypto');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(
  cors({
    origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
    credentials: true,
  })
);
app.use(express.json({ limit: '10mb' }));

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: Number(process.env.DB_PORT) || 5432,
  database: process.env.DB_NAME || 'agritech',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || '',
});

pool.on('error', (err) => {
  console.error('❌ Database connection error:', err);
});

async function testConnection() {
  await pool.query('SELECT 1');
  console.log('✅ Database connected successfully');
}

async function initTables() {
  await pool.query(`CREATE EXTENSION IF NOT EXISTS postgis;`);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS users (
      id BIGSERIAL PRIMARY KEY,
      username VARCHAR(100) NOT NULL UNIQUE,
      farmer_id VARCHAR(100) NOT NULL UNIQUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `);

  await pool.query(`
    CREATE TABLE IF NOT EXISTS plots (
      id BIGSERIAL PRIMARY KEY,
      farmer_id VARCHAR(100) NOT NULL,
      plot_geom geometry(POLYGON, 4326) NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      CONSTRAINT fk_plots_farmer
        FOREIGN KEY (farmer_id)
        REFERENCES users (farmer_id)
        ON DELETE CASCADE,
      CONSTRAINT chk_plot_valid
        CHECK (ST_IsValid(plot_geom)),
      CONSTRAINT chk_plot_not_empty
        CHECK (NOT ST_IsEmpty(plot_geom))
    );
  `);

  await pool.query(`CREATE INDEX IF NOT EXISTS idx_plots_geom_gist ON plots USING GIST (plot_geom);`);
  await pool.query(`CREATE INDEX IF NOT EXISTS idx_plots_farmer_created ON plots (farmer_id, created_at DESC);`);

  console.log('✅ Database tables ready');
}

// --- helpers ---
function normalizeUsername(username) {
  return String(username).trim().toLowerCase();
}

function isValidLatLng(lat, lng) {
  return (
    Number.isFinite(lat) &&
    Number.isFinite(lng) &&
    lat >= -90 &&
    lat <= 90 &&
    lng >= -180 &&
    lng <= 180
  );
}

function toLonLatArray(plotCoordinates) {
  // Supports:
  // 1) [lng, lat]
  // 2) { longitude, latitude }
  // 3) { lng, lat }
  return plotCoordinates.map((c) => {
    if (Array.isArray(c)) {
      const lng = Number(c[0]);
      const lat = Number(c[1]);
      return [lng, lat];
    }
    const lng = Number(c.longitude ?? c.lng);
    const lat = Number(c.latitude ?? c.lat);
    return [lng, lat];
  });
}

function closeRingIfNeeded(lonLat) {
  const first = lonLat[0];
  const last = lonLat[lonLat.length - 1];
  if (!first || !last) return lonLat;

  const same =
    first[0] === last[0] &&
    first[1] === last[1];

  if (same) return lonLat;
  return [...lonLat, first];
}

function lonLatToWktPolygon(lonLat) {
  const parts = lonLat.map(([lng, lat]) => `${lng} ${lat}`);
  return `POLYGON((${parts.join(', ')}))`;
}

// ---------- endpoints ----------

// Login
app.post('/api/login', async (req, res) => {
  try {
    const { username } = req.body;

    if (!username || typeof username !== 'string' || username.length > 100) {
      return res.status(400).json({ success: false, error: 'Invalid username' });
    }

    const sanitizedUsername = normalizeUsername(username);

    const existing = await pool.query(
      'SELECT farmer_id FROM users WHERE username = $1',
      [sanitizedUsername]
    );

    let farmerId;
    if (existing.rows.length) {
      farmerId = existing.rows[0].farmer_id;
    } else {
      const randomString = crypto.randomBytes(4).toString('hex');
      farmerId = `farmer_${Date.now()}_${randomString}`;

      await pool.query(
        'INSERT INTO users (username, farmer_id) VALUES ($1, $2)',
        [sanitizedUsername, farmerId]
      );
    }

    res.json({ success: true, farmerId, username: sanitizedUsername });
  } catch (err) {
    console.error('❌ Login error:', err);
    res.status(500).json({ success: false, error: 'Failed to process login' });
  }
});

// Save plot
app.post('/api/save-plot', async (req, res) => {
  try {
    const { farmerId, plotCoordinates } = req.body;

    if (!farmerId || typeof farmerId !== 'string') {
      return res.status(400).json({ success: false, error: 'Invalid farmerId' });
    }
    if (!Array.isArray(plotCoordinates) || plotCoordinates.length < 3) {
      return res.status(400).json({ success: false, error: 'plotCoordinates must have at least 3 points' });
    }

    // Ensure farmer exists (FK will fail anyway, but this gives a cleaner error)
    const u = await pool.query('SELECT 1 FROM users WHERE farmer_id = $1', [farmerId.trim()]);
    if (!u.rows.length) {
      return res.status(404).json({ success: false, error: 'Farmer not found. Please login first.' });
    }

    const lonLat = toLonLatArray(plotCoordinates);

    // validate coords
    for (const [lng, lat] of lonLat) {
      if (!isValidLatLng(lat, lng)) {
        return res.status(400).json({
          success: false,
          error: `Invalid coordinate detected: lat=${lat}, lng=${lng}`,
        });
      }
    }

    const ring = closeRingIfNeeded(lonLat);
    const wkt = lonLatToWktPolygon(ring);

    const insert = await pool.query(
      `INSERT INTO plots (farmer_id, plot_geom)
       VALUES ($1, ST_GeomFromText($2, 4326))
       RETURNING id, created_at`,
      [farmerId.trim(), wkt]
    );

    res.json({
      success: true,
      message: 'Plot saved!',
      plotId: insert.rows[0].id,
      farmerId: farmerId.trim(),
      createdAt: insert.rows[0].created_at,
    });
  } catch (err) {
    console.error('❌ Save plot error:', err);
    res.status(500).json({ success: false, error: err.message || 'Failed to save plot' });
  }
});

// Latest plot (includes area + coordinates)
app.get('/api/latest-plot', async (req, res) => {
  try {
    const farmerId = String(req.query.farmerId || '').trim();
    if (!farmerId) return res.status(400).json({ success: false, error: 'farmerId is required' });

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

    if (!rows.length) return res.status(404).json({ success: false, error: 'No plot found' });

    const p = rows[0];
    const geo = JSON.parse(p.geojson);
    const coords = geo.coordinates?.[0] || [];

    res.json({
      success: true,
      plotId: p.id,
      farmerId: p.farmer_id,
      areaSqm: Number(p.area_sqm),
      areaAcres: +(Number(p.area_sqm) * 0.000247105).toFixed(2),
      coordinates: coords.map(([lng, lat]) => ({ latitude: lat, longitude: lng })),
      createdAt: p.created_at,
    });
  } catch (err) {
    console.error('❌ Get latest plot error:', err);
    res.status(500).json({ success: false, error: 'Failed to fetch plot' });
  }
});

// Run model (FIXED GeoJSON + aliasing)
app.post('/api/run-model', async (req, res) => {
  try {
    const { farmerId, cropType } = req.body;

    if (!farmerId || !cropType) {
      return res.status(400).json({ success: false, error: 'farmerId and cropType are required' });
    }

    const { rows } = await pool.query(
      `SELECT ST_AsGeoJSON(plot_geom) AS geojson
       FROM plots
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [String(farmerId).trim()]
    );

    if (!rows.length) {
      return res.status(404).json({ success: false, error: 'No plot found for this farmer' });
    }

    const geojson = JSON.parse(rows[0].geojson);
    const coordinates = (geojson.coordinates?.[0] || []).map(([lng, lat]) => ({
      latitude: lat,
      longitude: lng,
    }));

    const pythonProcess = spawn(
      'python',
      [
        'predict_crop_stage.py',
        String(farmerId).trim(),
        String(cropType).trim().toLowerCase(),
        JSON.stringify(coordinates),
      ],
      { cwd: __dirname, stdio: ['pipe', 'pipe', 'pipe'] }
    );

    let output = '';
    let errorOutput = '';

    pythonProcess.stdout.on('data', (d) => (output += d.toString()));
    pythonProcess.stderr.on('data', (d) => {
      errorOutput += d.toString();
      console.error('🐍 Python stderr:', d.toString());
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        return res.status(500).json({
          success: false,
          error: `Python model failed with code ${code}`,
          details: errorOutput,
        });
      }
      try {
        const result = JSON.parse(output.trim());
        return res.json(result);
      } catch {
        return res.status(500).json({
          success: false,
          error: 'Invalid JSON response from Python model',
          raw: output,
        });
      }
    });

    pythonProcess.on('error', (err) => {
      console.error('❌ Python process error:', err);
      res.status(500).json({ success: false, error: 'Failed to start Python process' });
    });
  } catch (err) {
    console.error('❌ Run model error:', err);
    res.status(500).json({ success: false, error: 'Failed to run model' });
  }
});

// Recommendations endpoint kept (unchanged logic, cleaned a bit)
app.post('/api/generate-recommendations', async (req, res) => {
  const { plotId, farmerId, plotFeatures } = req.body;

  if (!plotId || !plotFeatures) {
    return res.status(400).json({ error: 'plotId and plotFeatures are required' });
  }

  const inputData = {
    plot_id: plotId,
    farmer_id: farmerId || null,
    current_crop: plotFeatures.current_crop || null,
    last_updated: plotFeatures.last_updated || null,
    features_data: plotFeatures,
  };

  const pythonScriptPath = path.join(__dirname, 'decision_engine.py');
  const pythonProcess = spawn('python', [pythonScriptPath, JSON.stringify(inputData)]);

  let outputData = '';
  let errorOutput = '';

  pythonProcess.stdout.on('data', (d) => (outputData += d.toString()));
  pythonProcess.stderr.on('data', (d) => (errorOutput += d.toString()));

  pythonProcess.on('close', (code) => {
    if (code !== 0) {
      return res.status(500).json({ error: `Python script failed with code ${code}`, details: errorOutput });
    }
    try {
      const result = JSON.parse(outputData.trim());
      return res.json(result);
    } catch (e) {
      return res.status(500).json({ error: 'Failed to parse recommendation output', raw: outputData });
    }
  });
});

// Start
(async () => {
  try {
    await testConnection();
    await initTables();
    app.listen(PORT, '0.0.0.0', () => {
      console.log(`🚀 Server running on http://localhost:${PORT}`);
    });
  } catch (err) {
    console.error('❌ Startup failed:', err);
    process.exit(1);
  }
})();
