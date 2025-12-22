// server.js
const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());

/* ---------------------------------------------------
   EXPORTS DIRECTORY
--------------------------------------------------- */
const EXPORTS_DIR = path.join(__dirname, 'exports');
if (!fs.existsSync(EXPORTS_DIR)) {
  fs.mkdirSync(EXPORTS_DIR, { recursive: true });
}

/* ---------------------------------------------------
   DATABASE
--------------------------------------------------- */
const pool = new Pool({
  user: 'postgres',
  host: 'localhost',
  database: 'farmdb',
  password: 'Rishabh.0456@@', // change if needed
  port: 5432,
});

/* ---------------------------------------------------
   CREATE TABLE
--------------------------------------------------- */
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
  console.error('❌ Table creation failed:', err);
});

/* ---------------------------------------------------
   HELPER
--------------------------------------------------- */
const normalizeFarmerId = (id) =>
  id?.toString().trim().toLowerCase();

/* ---------------------------------------------------
   SAVE PLOT
--------------------------------------------------- */
app.post('/api/save-plot', async (req, res) => {
  try {
    let { farmerId, plotCoordinates } = req.body;
    farmerId = normalizeFarmerId(farmerId);

    if (!farmerId || !Array.isArray(plotCoordinates) || plotCoordinates.length < 3) {
      return res.status(400).json({ error: 'Invalid input' });
    }

    // Keep original coordinates for CSV
    const originalCoords = [...plotCoordinates];

    // Close polygon ONLY for PostGIS
    let coords = [...plotCoordinates];
    const first = coords[0];
    const last = coords[coords.length - 1];
    if (first[0] !== last[0] || first[1] !== last[1]) {
      coords.push(first);
    }

    const wkt = `POLYGON((${coords
      .map(pt => `${pt[1]} ${pt[0]}`)
      .join(', ')}))`;

    await pool.query(
      `INSERT INTO plots (farmer_id, plot_geom)
       VALUES ($1, ST_GeomFromText($2, 4326))`,
      [farmerId, wkt]
    );

    /* ---------- CSV ---------- */
    const csv = `farmer_id,latitude,longitude
${originalCoords.map(pt =>
      `${farmerId},${pt[0]},${pt[1]}`
    ).join('\n')}`;

    const filename = `plot_${farmerId}_${Date.now()}.csv`;
    const filepath = path.join(EXPORTS_DIR, filename);
    fs.writeFileSync(filepath, csv);

    // Auto-open CSV (local dev only)
    if (process.platform === 'win32') exec(`start "" "${filepath}"`);
    else if (process.platform === 'darwin') exec(`open "${filepath}"`);
    else exec(`xdg-open "${filepath}"`);

    res.json({
      success: true,
      message: 'Plot saved successfully',
      farmerId
    });

  } catch (err) {
    console.error('❌ Save error:', err);
    res.status(500).json({ error: 'Failed to save plot' });
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
   CSV SUMMARY (LATEST PLOT)
--------------------------------------------------- */
app.get('/api/plot-data/:farmerId.csv', async (req, res) => {
  try {
    const farmerId = normalizeFarmerId(req.params.farmerId);

    const { rows } = await pool.query(
      `SELECT
        farmer_id,
        ST_Y(ST_Centroid(plot_geom)) AS center_lat,
        ST_X(ST_Centroid(plot_geom)) AS center_lng,
        ST_Area(plot_geom::geography) * 0.000247105 AS area_acres
       FROM plots
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [farmerId]
    );

    if (!rows.length) return res.status(404).send('Plot not found');

    const p = rows[0];
    const csv = `farmer_id,center_lat,center_lng,area_acres
${p.farmer_id},${p.center_lat},${p.center_lng},${p.area_acres}`;

    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename=plot_summary.csv');
    res.send(csv);

  } catch (err) {
    console.error('❌ CSV error:', err);
    res.status(500).send('CSV generation failed');
  }
});

/* ---------------------------------------------------
   START SERVER
--------------------------------------------------- */
const PORT = 3001;
app.listen(PORT, () => {
  console.log(`🚀 Server running on http://localhost:${PORT}`);
});
