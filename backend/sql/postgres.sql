CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(100) UNIQUE NOT NULL,
  farmer_id VARCHAR(100) UNIQUE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS plots (
  id SERIAL PRIMARY KEY,
  farmer_id VARCHAR(100) NOT NULL,
  plot_geom GEOMETRY(POLYGON, 4326) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO users (username, farmer_id)
VALUES ('rahul', 'farmer_1700000000000_ab12cd34')
ON CONFLICT (username) DO NOTHING;

INSERT INTO plots (farmer_id, plot_geom)
VALUES (
  'farmer_1700000000000_ab12cd34',
  ST_GeomFromText('POLYGON((72.8777 19.0760, 72.8784 19.0760, 72.8784 19.0753, 72.8777 19.0753, 72.8777 19.0760))', 4326)
);

WITH frontend_payload AS (
  SELECT
    'farmer_1700000000000_ab12cd34'::text AS farmer_id,
    '[{"longitude":72.8777,"latitude":19.0760},{"longitude":72.8784,"latitude":19.0760},{"longitude":72.8784,"latitude":19.0753},{"longitude":72.8777,"latitude":19.0753}]'::jsonb AS plot_coordinates
), points AS (
  SELECT
    farmer_id,
    ord,
    longitude,
    latitude
  FROM frontend_payload,
  jsonb_to_recordset(plot_coordinates) WITH ORDINALITY AS p(longitude double precision, latitude double precision, ord bigint)
), ordered AS (
  SELECT
    farmer_id,
    ST_MakePoint(longitude, latitude) AS geom,
    ord
  FROM points
), ring AS (
  SELECT
    farmer_id,
    ST_MakeLine(ARRAY_AGG(geom ORDER BY ord)) AS line_geom
  FROM ordered
  GROUP BY farmer_id
), closed_ring AS (
  SELECT
    farmer_id,
    CASE
      WHEN ST_StartPoint(line_geom) = ST_EndPoint(line_geom) THEN line_geom
      ELSE ST_AddPoint(line_geom, ST_StartPoint(line_geom))
    END AS closed_line
  FROM ring
)
INSERT INTO plots (farmer_id, plot_geom)
SELECT
  farmer_id,
  ST_SetSRID(ST_MakePolygon(closed_line), 4326)
FROM closed_ring;

SELECT
  id,
  farmer_id,
  ST_AsText(plot_geom) AS wkt,
  ST_AsGeoJSON(plot_geom) AS geojson,
  area(plot_geom::geography) AS area_sqm,
FROM plots
ORDER BY created_at DESC
LIMIT 5;