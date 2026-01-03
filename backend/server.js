require('dotenv').config();

const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const crypto = require('crypto');
const jwt = require('jsonwebtoken');
const { exec } = require('child_process');

const app = express();
const PORT = process.env.PORT || 8080;

app.set("trust proxy", 1);

/* ---------------------------------------------------
   MIDDLEWARE
--------------------------------------------------- */
app.use(helmet());
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

app.use(rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 500
}));

/* ---------------------------------------------------
   DATABASE (Railway-compatible)
--------------------------------------------------- */
const pool = new Pool({
  host: process.env.PGHOST,
  port: Number(process.env.PGPORT),
  database: process.env.PGDATABASE,
  user: process.env.PGUSER,
  password: process.env.PGPASSWORD,
  ssl: { rejectUnauthorized: false }
});

/* ---------------------------------------------------
   INIT TABLES
--------------------------------------------------- */

async function waitForDb(retries = 10, delay = 3000) {
  for (let i = 0; i < retries; i++) {
    try {
      await pool.query('SELECT 1');
      console.log('✅ Database connected');
      return;
    } catch (err) {
      console.error(`⏳ DB not ready (attempt ${i + 1}/${retries})`);
      await new Promise(res => setTimeout(res, delay));
    }
  }
  console.error('❌ Database never became ready');
  process.exit(1);
}


async function initDb() {
  try {
    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        farmer_id VARCHAR(100) UNIQUE NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
      );
    `);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS plots (
        id SERIAL PRIMARY KEY,
        farmer_id VARCHAR(100) NOT NULL,
        plot_geom JSONB NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
      );
    `);

    console.log('✅ Database initialized');
  } catch (err) {
    console.error('❌ Database init failed:', err);
    process.exit(1);
  }
}

initDb();

/* ---------------------------------------------------
   HEALTH CHECK (Railway REQUIRED)
--------------------------------------------------- */
app.get('/health', async (_req, res) => {
  try {
    await pool.query('SELECT 1');
    res.json({ status: 'ok' });
  } catch {
    res.status(500).json({ status: 'db-error' });
  }
});

/* ---------------------------------------------------
   LOGIN / REGISTER
--------------------------------------------------- */
app.post('/api/login', async (req, res) => {
  try {
    const { username } = req.body;
    if (!username || typeof username !== 'string') {
      return res.status(400).json({ error: 'Invalid username' });
    }

    const cleanUsername = username.trim().toLowerCase();
    let farmerId;

    const existing = await pool.query(
      'SELECT farmer_id FROM users WHERE username = $1',
      [cleanUsername]
    );

    if (existing.rows.length) {
      farmerId = existing.rows[0].farmer_id;
    } else {
      farmerId = `farmer_${Date.now()}_${crypto.randomBytes(4).toString('hex')}`;
      await pool.query(
        'INSERT INTO users (username, farmer_id) VALUES ($1, $2)',
        [cleanUsername, farmerId]
      );
    }

    const token = jwt.sign(
      { farmerId, username: cleanUsername },
      process.env.JWT_SECRET,
      { expiresIn: '24h' }
    );

    res.json({ success: true, farmerId, token });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Login failed' });
  }
});

/* ---------------------------------------------------
   SAVE PLOT (JSONB)
--------------------------------------------------- */
app.post('/api/save-plot', async (req, res) => {
  try {
    const { farmerId, plotCoordinates } = req.body;

    if (!farmerId || !Array.isArray(plotCoordinates) || plotCoordinates.length < 3) {
      return res.status(400).json({ error: 'Invalid input' });
    }

    await pool.query(
      `INSERT INTO plots (farmer_id, plot_geom)
       VALUES ($1, $2)`,
      [farmerId, JSON.stringify(plotCoordinates)]
    );

    res.json({ success: true });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to save plot' });
  }
});

/* ---------------------------------------------------
   GET LATEST PLOT
--------------------------------------------------- */
app.get('/api/latest-plot', async (req, res) => {
  try {
    const { farmerId } = req.query;

    const { rows } = await pool.query(
      `SELECT id, plot_geom, created_at
       FROM plots
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [farmerId]
    );

    if (!rows.length) return res.status(404).json({ error: 'No plot found' });

    res.json({
      plotId: rows[0].id,
      coordinates: rows[0].plot_geom,
      createdAt: rows[0].created_at
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch plot' });
  }
});

/* ---------------------------------------------------
   RUN MODEL
--------------------------------------------------- */
app.post('/api/run-model', async (req, res) => {
  try {
    const { farmerId, cropType } = req.body;

    if (!farmerId || !cropType) {
      return res.status(400).json({
        success: false,
        error: "Missing farmerId or cropType"
      });
    }

    // Fetch latest plot
    const { rows } = await pool.query(
      `SELECT ST_AsGeoJSON(plot_geom) AS geojson
       FROM plots
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [farmerId]
    );

    if (!rows.length) {
      return res.status(404).json({
        success: false,
        error: "No plot found for this farmer"
      });
    }

    const geojson = JSON.parse(rows[0].geojson);
    const coordinates = geojson.coordinates[0].map(([lng, lat]) => ({
      latitude: lat,
      longitude: lng
    }));

    if (!coordinates.length) {
      return res.status(400).json({
        success: false,
        error: "Plot has no coordinates"
      });
    }

    // 🔐 SAFE: Base64 encode coordinates
    const coordsB64 = Buffer
      .from(JSON.stringify(coordinates))
      .toString("base64");

    const safeFarmerId = farmerId.replace(/[^a-zA-Z0-9_]/g, "");
    const safeCropType = cropType.replace(/[^a-zA-Z0-9_]/g, "");

    const command = `python predict_crop_stage.py "${safeFarmerId}" "${safeCropType}" "${coordsB64}"`;

    console.log("🚀 Running model:", command);

    exec(command, { cwd: __dirname, maxBuffer: 1024 * 1024 * 10 }, (err, stdout, stderr) => {
      if (err) {
        console.error("❌ Python error:", stderr || err.message);
        return res.status(500).json({
          success: false,
          error: "Python model execution failed"
        });
      }

      try {
        const result = JSON.parse(stdout.trim());
        return res.json(result);
      } catch (e) {
        console.error("❌ Invalid JSON from Python:", stdout);
        return res.status(500).json({
          success: false,
          error: "Invalid response from model"
        });
      }
    });

  } catch (err) {
    console.error("❌ Backend error:", err);
    res.status(500).json({
      success: false,
      error: "Internal server error"
    });
  }
});


/* ---------------------------------------------------
   START SERVER
--------------------------------------------------- */
app.use((req, res, next) => {
  console.log(req.ip);
  next();
});


app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
