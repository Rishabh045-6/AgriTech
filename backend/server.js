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
const PORT = process.env.PORT || 3001;

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
  ssl: process.env.NODE_ENV === 'production'
    ? { rejectUnauthorized: false }
    : false,
});

/* ---------------------------------------------------
   INIT TABLES
--------------------------------------------------- */
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
      return res.status(400).json({ error: 'Missing fields' });
    }

    const { rows } = await pool.query(
      `SELECT plot_geom
       FROM plots
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [farmerId]
    );

    if (!rows.length) {
      return res.status(404).json({ error: 'No plot found' });
    }

    const coords = rows[0].plot_geom;

    const command = `python predict_crop_stage.py '${farmerId}' '${JSON.stringify(coords)}' '${cropType}'`;

    exec(command, (error, stdout, stderr) => {
      if (error) {
        console.error(stderr);
        return res.status(500).json({ error: 'Model failed' });
      }
      res.json(JSON.parse(stdout));
    });

  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Run model failed' });
  }
});

/* ---------------------------------------------------
   START SERVER
--------------------------------------------------- */
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Server running on port ${PORT}`);
});
