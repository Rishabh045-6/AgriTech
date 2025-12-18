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
// Update your POST /api/save-plot endpoint
app.post('/api/save-plot', async (req, res) => {
  try {
    const { farmerId, plotCoordinates } = req.body;
    
    if (!farmerId || !Array.isArray(plotCoordinates) || plotCoordinates.length < 3) {
      return res.status(400).json({ error: 'Invalid input' });
    }

    let coords = plotCoordinates;
    const first = coords[0];
    const last = coords[coords.length - 1];
    if (first[0] !== last[0] || first[1] !== last[1]) {
      coords = [...coords, first];
    }

    const wkt = `POLYGON((${coords.map(pt => `${pt[1]} ${pt[0]}`).join(', ')}))`;

    // Insert and return the created plot
    const result = await pool.query(
      `INSERT INTO plots (farmer_id, plot_geom) 
       VALUES ($1, ST_GeomFromText($2, 4326))
       RETURNING id, farmer_id, created_at`,
      [farmerId, wkt]
    );

    // Get GeoJSON for the saved plot
    const geojsonResult = await pool.query(
      `SELECT ST_AsGeoJSON(plot_geom) AS geojson FROM plots WHERE id = $1`,
      [result.rows[0].id]
    );

    const plotData = {
      id: result.rows[0].id,
      farmerId: result.rows[0].farmer_id,
      createdAt: result.rows[0].created_at,
      geometry: JSON.parse(geojsonResult.rows[0].geojson),
      coordinates: coords // Original format for your model
    };

    res.json({ 
      success: true, 
      message: 'Plot saved!',
      plot: plotData
    });
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

// Get plot data as JSON
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
       WHERE farmer_id = $1`,
      [req.params.farmerId]
    );

    if (rows.length === 0) {
      return res.status(404).json({ error: 'Plot not found' });
    }

    const plot = rows[0];
    const area_acres = parseFloat((plot.area_sqm * 0.000247105).toFixed(2)); // sqm → acres

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

// Get plot data as CSV
app.get('/api/plot-data/:farmerId.csv', async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT 
        farmer_id,
        ST_X(ST_Centroid(plot_geom)) AS center_lng,
        ST_Y(ST_Centroid(plot_geom)) AS center_lat,
        ST_Area(plot_geom::geography) * 0.000247105 AS area_acres
       FROM plots 
       WHERE farmer_id = $1`,
      [req.params.farmerId]
    );

    if (rows.length === 0) {
      return res.status(404).send('Plot not found');
    }

    const plot = rows[0];
    const csv = `farmerId,centerLat,centerLng,areaAcres\n${plot.farmer_id},${plot.center_lat},${plot.center_lng},${plot.area_acres}`;
    
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename=plot_data.csv');
    res.send(csv);
  } catch (err) {
    res.status(500).send('Error generating CSV');
  }
});

// Start server
const PORT = 3001;
app.listen(PORT, () => {
  console.log(`🚀 Backend running on http://localhost:${PORT}`);
});