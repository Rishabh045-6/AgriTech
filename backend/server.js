// server.js
const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// Database connection
const pool = new Pool({
  user: 'postgres',
  host: 'localhost',
  database: 'farmdb',
  password: 'Rishabh.0456@@', // ← REPLACE with your password
  port: 5432,
});

// Create table for farm plots
pool.query(`
  CREATE TABLE IF NOT EXISTS plots (
    id SERIAL PRIMARY KEY,
    farmer_id VARCHAR(100) NOT NULL,
    plot_geom GEOMETRY(POLYGON, 4326),
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
`).then(() => {
  console.log('✅ Plots table ready');
}).catch(err => {
  console.error('❌ Table error:', err);
});

// Save plot endpoint
app.post('/api/save-plot', async (req, res) => {
  try {
    const { farmerId, plotCoordinates } = req.body;
    
    if (!farmerId || !Array.isArray(plotCoordinates)) {
      return res.status(400).json({ error: 'Missing farmerId or plotCoordinates' });
    }

    // Ensure polygon is closed
    let coords = plotCoordinates;
    if (coords.length < 3) return res.status(400).json({ error: 'Need ≥3 points' });
    
    const first = coords[0];
    const last = coords[coords.length - 1];
    if (first[0] !== last[0] || first[1] !== last[1]) {
      coords = [...coords, first]; // Close polygon
    }

    // Convert to WKT: "POLYGON((lng1 lat1, lng2 lat2, ...))"
    const wkt = `POLYGON((${coords.map(pt => `${pt[1]} ${pt[0]}`).join(', ')}))`;

    // Save to PostGIS
    await pool.query(
      `INSERT INTO plots (farmer_id, plot_geom) 
       VALUES ($1, ST_GeomFromText($2, 4326))`,
      [farmerId, wkt]
    );

    res.json({ success: true, message: 'Plot saved!' });
  } catch (err) {
    console.error('Save error:', err);
    res.status(500).json({ error: 'Failed to save plot' });
  }
});

// Get plots endpoint (optional)
app.get('/api/plots/:farmerId', async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT id, ST_AsGeoJSON(plot_geom) AS geojson 
       FROM plots 
       WHERE farmer_id = $1`,
      [req.params.farmerId]
    );
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: 'Failed to fetch plots' });
  }
});

// Start server
const PORT = 3001;
app.listen(PORT, () => {
  console.log(`🚀 Backend running on http://localhost:${PORT}`);
});