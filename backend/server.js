// server.js
const express = require('express');
const { Pool } = require('pg');
const cors = require('cors');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

// Create exports directory
const EXPORTS_DIR = path.join(__dirname, 'exports');
if (!fs.existsSync(EXPORTS_DIR)) {
  fs.mkdirSync(EXPORTS_DIR, { recursive: true });
}

const app = express();
app.use(cors());
app.use(express.json());

// Database connection
const pool = new Pool({
  user: 'postgres',
  host: 'localhost',
  database: 'farmdb',
  password: 'Rishabh.0456@@', // replace if needed
  port: 5432,
});

// Create table
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

/* ---------------------------------------------------
   SAVE PLOT (with CSV auto-open)
--------------------------------------------------- */
app.post('/api/save-plot', async (req, res) => {
  try {
    const { farmerId, plotCoordinates } = req.body;
    
    if (!farmerId || !Array.isArray(plotCoordinates) || plotCoordinates.length < 3) {
      return res.status(400).json({ error: 'Invalid input' });
    }

    // Save original coordinates for CSV (no duplication)
    const originalCoords = [...plotCoordinates];

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

    // ✅ GENERATE CSV WITH ORIGINAL COORDINATES (no duplicate)
    const csv = `latitude,longitude\n${originalCoords.map(pt => `${pt[0]},${pt[1]}`).join('\n')}`;
    const filename = `plot_${farmerId}_${Date.now()}.csv`;
    const filepath = path.join(EXPORTS_DIR, filename);
    
    fs.writeFileSync(filepath, csv);
    
    // ✅ AUTO-OPEN CSV ON PC
    if (process.platform === 'win32') {
      exec(`start "" "${filepath}"`); // Windows
    } else if (process.platform === 'darwin') {
      exec(`open "${filepath}"`); // macOS
    } else {
      exec(`xdg-open "${filepath}"`); // Linux
    }

    res.json({ success: true, message: 'Plot saved!', farmerId: farmerId });
  } catch (err) {
    console.error('Backend error:', err);
    res.status(500).json({ error: 'Failed to save plot' });
  }
});

/* ---------------------------------------------------
   GET LATEST PLOT FOR FARMER
--------------------------------------------------- */
app.get('/api/latest-plot', async (req, res) => {
  try {
    const { farmerId } = req.query;
    
    const { rows } = await pool.query(
      `SELECT 
        id,
        farmer_id,
        ST_AsGeoJSON(plot_geom) AS plot_geojson,
        ST_Area(plot_geom::geography) AS area_sqm,
        created_at
       FROM plots 
       WHERE farmer_id = $1
       ORDER BY created_at DESC
       LIMIT 1`,
      [farmerId]
    );

    if (rows.length === 0) {
      return res.status(404).json({ error: 'No plots found for this farmer' });
    }

    const plot = rows[0];
    const area_acres = parseFloat((plot.area_sqm * 0.000247105).toFixed(2));

    const response = {
      plotId: plot.id,
      farmerId: plot.farmer_id,
      areaAcres: area_acres,
      coordinates: JSON.parse(plot.plot_geojson).coordinates[0].map(coord => ({
        latitude: coord[1],
        longitude: coord[0]
      })),
      createdAt: plot.created_at
    };

    res.json(response);
  } catch (err) {
    console.error('Fetch error:', err);
    res.status(500).json({ error: 'Failed to fetch plot' });
  }
});

/* ---------------------------------------------------
   GET ALL PLOTS FOR FARMER
--------------------------------------------------- */
app.get('/api/plot-data/:farmerId', async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT 
        id,
        farmer_id,
        ST_AsGeoJSON(plot_geom) AS plot_geojson,
        ST_Area(plot_geom::geography) AS area_sqm,
        created_at
       FROM plots 
       WHERE farmer_id = $1
       ORDER BY created_at DESC`,
      [req.params.farmerId]
    );

    if (rows.length === 0) {
      return res.status(404).json({ error: 'No plots found for this farmer' });
    }

    const plots = rows.map(plot => ({
      plotId: plot.id,
      farmerId: plot.farmer_id,
      areaAcres: parseFloat((plot.area_sqm * 0.000247105).toFixed(2)),
      coordinates: JSON.parse(plot.plot_geojson).coordinates[0].map(coord => ({
        latitude: coord[1],
        longitude: coord[0]
      })),
      createdAt: plot.created_at
    }));

    res.json(plots);
  } catch (err) {
    console.error('Fetch error:', err);
    res.status(500).json({ error: 'Failed to fetch plots' });
  }
});

/* ---------------------------------------------------
   GET PLOT SUMMARY CSV
--------------------------------------------------- */
app.get('/api/plot-data/:farmerId.csv', async (req, res) => {
  try {
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
      [req.params.farmerId]
    );

    if (rows.length === 0) {
      return res.status(404).send('Plot not found');
    }

    const p = rows[0];
    const csv = `farmerId,centerLat,centerLng,areaAcres
${p.farmer_id},${p.center_lat},${p.center_lng},${p.area_acres}`;

    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename=plot_summary.csv');
    res.send(csv);
  } catch (err) {
    console.error('CSV error:', err);
    res.status(500).send('Error generating CSV');
  }
});

/* ---------------------------------------------------
   START SERVER
--------------------------------------------------- */
const PORT = 3001;
app.listen(PORT, () => {
  console.log(`🚀 Backend running on http://localhost:${PORT}`);
});