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

/* ---------------------------------------------------
   TRUST PROXY (REQUIRED for Railway/Koyeb)
--------------------------------------------------- */
app.set('trust proxy', 1);

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
   DATABASE (PostGIS)
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
   WAIT FOR DB
--------------------------------------------------- */
async function waitForDb(retries = 10, delay = 3000) {
  for (let i = 0; i < retries; i++) {
    try {
      await pool.query('SELECT 1');
      console.log('✅ Database connected');
      return;
    } catch {
      console.log(`⏳ Waiting for DB (${i + 1}/${retries})`);
      await new Promise(r => setTimeout(r, delay));
    }
  }
  console.error('❌ Database not reachable');
  process.exit(1);
}

/* ---------------------------------------------------
   INIT DATABASE (PostGIS) - FIXED: Handle existing schema
--------------------------------------------------- */
async function initDb() {
  try {
    await pool.query(`CREATE EXTENSION IF NOT EXISTS postgis;`);

    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(100) UNIQUE NOT NULL,
        farmer_id VARCHAR(100) UNIQUE NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
      );
    `);

    // ✅ FIXED: Check if plots table exists and handle schema changes
    const tableExists = await pool.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_name = 'plots'
      );
    `);

    if (tableExists.rows[0].exists) {
      // Check if coordinates column exists
      const columnExists = await pool.query(`
        SELECT EXISTS (
          SELECT FROM information_schema.columns 
          WHERE table_name = 'plots' AND column_name = 'coordinates'
        );
      `);

      if (!columnExists.rows[0].exists) {
        // Drop old plots table and create new one with JSONB
        await pool.query('DROP TABLE plots;');
      }
    }

    // Create plots table with JSONB column
    await pool.query(`
      CREATE TABLE IF NOT EXISTS plots (
        id SERIAL PRIMARY KEY,
        farmer_id VARCHAR(100) NOT NULL,
        coordinates JSONB NOT NULL,  -- ✅ JSONB for coordinates
        created_at TIMESTAMPTZ DEFAULT NOW()
      );
    `);

    console.log('✅ Database initialized with JSONB coordinates');
  } catch (err) {
    console.error('❌ DB init failed:', err);
    process.exit(1);
  }
}

(async () => {
  await waitForDb();
  await initDb();
})();

/* ---------------------------------------------------
   HEALTH CHECK
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
   SAVE PLOT (JSONB ONLY)
--------------------------------------------------- */
app.post('/api/save-plot', async (req, res) => {
  try {
    const { farmerId, plotCoordinates } = req.body;

    if (!farmerId || !Array.isArray(plotCoordinates) || plotCoordinates.length < 3) {
      return res.status(400).json({ error: 'Invalid plot coordinates' });
    }

    await pool.query(
      `INSERT INTO plots (farmer_id, coordinates)
       VALUES ($1, $2::jsonb)`,
      [farmerId, JSON.stringify(plotCoordinates)]
    );

    res.json({ success: true });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to save plot' });
  }
});

/* ---------------------------------------------------
   GET LATEST PLOT (JSONB)
--------------------------------------------------- */
app.get('/api/latest-plot', async (req, res) => {
  try {
    const { farmerId } = req.query;

    const { rows } = await pool.query(
      `SELECT
         id,
         coordinates,
         created_at
       FROM plots
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [farmerId]
    );

    if (!rows.length) return res.status(404).json({ error: 'No plot found' });

    res.json({
      plotId: rows[0].id,
      coordinates: rows[0].coordinates,
      createdAt: rows[0].created_at
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch plot' });
  }
});

/* ---------------------------------------------------
   RUN MODEL (JSONB ONLY)
--------------------------------------------------- */
app.post('/api/run-model', async (req, res) => {
  try {
    const { farmerId, cropType } = req.body;

    if (!farmerId || !cropType) {
      return res.status(400).json({
        success: false,
        error: 'Missing farmerId or cropType'
      });
    }

    // 1️⃣ Fetch latest plot (JSONB)
    const { rows } = await pool.query(
      `
      SELECT coordinates
      FROM plots
      WHERE farmer_id = $1
      ORDER BY created_at DESC
      LIMIT 1
      `,
      [farmerId]
    );

    if (!rows.length) {
      return res.status(404).json({
        success: false,
        error: 'No plot found for this farmer'
      });
    }

    const coordinates = rows[0].coordinates;

    // 2️⃣ Validate coordinates
    if (
      !Array.isArray(coordinates) ||
      coordinates.length < 3 ||
      !coordinates.every(
        p =>
          typeof p.latitude === 'number' &&
          typeof p.longitude === 'number'
      )
    ) {
      return res.status(400).json({
        success: false,
        error: 'Invalid plot coordinates format'
      });
    }

    // 3️⃣ Encode coordinates safely (BASE64)
    const coordsBase64 = Buffer
      .from(JSON.stringify(coordinates))
      .toString('base64');

    const safeFarmerId = farmerId.replace(/[^a-zA-Z0-9_]/g, '');
    const safeCropType = cropType.replace(/[^a-zA-Z0-9_]/g, '');

    const command = `python predict_crop_stage.py "${safeFarmerId}" "${safeCropType}" "${coordsBase64}"`;

    console.log('🚀 Running model:', command);

    // 4️⃣ Execute Python safely
    exec(
      command,
      {
        cwd: __dirname,
        maxBuffer: 1024 * 1024 * 20 // 20MB buffer for large JSON
      },
      (err, stdout, stderr) => {
        if (err) {
          console.error('❌ Python execution error:', stderr || err.message);
          return res.status(500).json({
            success: false,
            error: 'Python model execution failed'
          });
        }

        try {
          const output = stdout.trim();
          const result = JSON.parse(output);
          return res.json(result);
        } catch (parseErr) {
          console.error('❌ Invalid JSON from Python:', stdout);
          return res.status(500).json({
            success: false,
            error: 'Invalid response from model'
          });
        }
      }
    );

  } catch (err) {
    console.error('❌ Backend error:', err);
    res.status(500).json({
      success: false,
      error: 'Internal server error'
    });
  }
});

/* ---------------------------------------------------
   START SERVER
--------------------------------------------------- */
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Server running on port ${PORT}`);
});