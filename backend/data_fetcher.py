"""
Enhanced data fetcher with environment-based Sentinel Hub credentials
"""
import pandas as pd
import numpy as np
import os
import time
import sys
from datetime import datetime, timedelta, date
from sentinelhub import (
    CRS, DataCollection, Geometry,
    SentinelHubStatistical, SHConfig
)
from shapely.geometry import Polygon
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# Global variable to track current client index
current_client_idx = 0

def load_sentinel_credentials():
    """Load Sentinel Hub credentials from environment variables"""
    try:
        # Get individual credentials from environment variables
        clients = []
        
        # Load up to 6 client pairs from environment
        for i in range(1, 7):
            client_id = os.getenv(f'SENTINEL_CLIENT_{i}_ID')
            client_secret = os.getenv(f'SENTINEL_CLIENT_{i}_SECRET')
            
            if client_id and client_secret:
                clients.append((client_id, client_secret))
        
        if not clients:
            print("⚠️ Warning: No Sentinel Hub credentials found in environment variables.", file=sys.stderr)
            print("Please set SENTINEL_CLIENT_ID_1 and SENTINEL_CLIENT_SECRET_1 in your .env file", file=sys.stderr)
            return []
        
        return clients
        
    except Exception as e:
        print(f"Error loading Sentinel Hub credentials: {e}", file=sys.stderr)
        return []

def get_config():
    """Get Sentinel Hub configuration for current client"""
    global current_client_idx
    
    clients = load_sentinel_credentials()
    
    if not clients:
        raise RuntimeError("No Sentinel Hub credentials available")
    
    cfg = SHConfig()
    cfg.sh_client_id = clients[current_client_idx][0]
    cfg.sh_client_secret = clients[current_client_idx][1]
    return cfg

# EVALSCRIPT (same as before - no exposed credentials)
EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: ["B02","B03","B04","B05","B08","B11","B12","SCL","dataMask"],
    output: [
      {
        id: "default",
        bands: 19,
        sampleType: "FLOAT32"
      },
      {
        id: "dataMask",
        bands: 1
      }
    ]
  };
}

function evaluatePixel(s) {
  if (s.SCL == 3 || s.SCL == 8 || s.SCL == 9 || s.SCL == 10) {
    return {
      default: Array(19).fill(null),
      dataMask: [0]
    };
  }

  let eps = 1e-6;

  let NDVI = (s.B08 - s.B04) / (s.B08 + s.B04 + eps);
  let GNDVI = (s.B08 - s.B03) / (s.B08 + s.B03 + eps);
  let SAVI = 1.5 * (s.B08 - s.B04) / (s.B08 + s.B04 + 0.5 + eps);
  let NDMI = (s.B08 - s.B11) / (s.B08 + s.B11 + eps);
  let MSI = s.B11 / (s.B08 + eps);
  let NDWI = (s.B03 - s.B08) / (s.B03 + s.B08 + eps);
  let NMDI = (s.B08 - (s.B11 - s.B12)) / (s.B08 + (s.B11 - s.B12) + eps);
  let NDRE = (s.B08 - s.B05) / (s.B08 + s.B05 + eps);
  let CIredEdge = (s.B08 / (s.B05 + eps)) - 1;
  let CIgreen = (s.B08 / (s.B03 + eps)) - 1;
  let PSRI = (s.B04 - s.B03) / (s.B05 + eps);
  let SIPI = (s.B08 - s.B02) / (s.B08 - s.B04 + eps);

  return {
    default: [
      // RAW BANDS
      s.B02, s.B03, s.B04, s.B05, s.B08, s.B11, s.B12,
      // INDICES
      NDVI, GNDVI, SAVI, NDMI, MSI, NDWI, NMDI,
      NDRE, CIredEdge, CIgreen, PSRI, SIPI
    ],
    dataMask: [s.dataMask]
  };
}
"""

def fetch_timeseries_data(corners, date_range, max_cloud=80):
    """Fetch timeseries data from Sentinel Hub"""
    global current_client_idx
    
    geometry = Geometry(Polygon(corners), CRS.WGS84)
    date_from = date_range['window_start'].strftime("%Y-%m-%d")
    date_to = date_range['window_end'].strftime("%Y-%m-%d")
    
    clients = load_sentinel_credentials()
    
    if not clients:
        raise RuntimeError("No Sentinel Hub credentials available")
    
    while current_client_idx < len(clients):
        config = get_config()
        
        try:
            request = SentinelHubStatistical(
                aggregation={
                    "timeRange": {
                        "from": f"{date_from}T00:00:00Z",
                        "to": f"{date_to}T23:59:59Z"
                    },
                    "aggregationInterval": {"of": "P1D"},
                    "evalscript": EVALSCRIPT
                },
                calculations={
                    "default": {
                        "statistics": {
                            "default": {}
                        }
                    }
                },
                input_data=[
                    {
                        "type": "S2L2A",
                        "dataFilter": {
                            "maxCloudCoverage": max_cloud
                        }
                    }
                ],
                geometry=geometry,
                config=config
            )
            
            response = request.get_data()
            return response[0]["data"]
            
        except Exception as e:
            msg = str(e).lower()
            if "insufficient" in msg or "payment" in msg or "quota" in msg:
                current_client_idx += 1
                print(f"Switching to next Sentinel Hub client... (Client {current_client_idx + 1})", file=sys.stderr)
                continue
            time.sleep(3)
    
    # If all clients are exhausted, raise an error
    raise RuntimeError("All Sentinel Hub accounts exhausted or invalid credentials")

def process_satellite_data(raw_data):
    """Process raw API response"""
    rows = []
    
    for item in raw_data:
        date_str = item["interval"]["from"][:10]
        bands = item["outputs"]["default"]["bands"]
        
        if not bands or "B0" not in bands:
            continue
        
        def mean(b):
            v = bands.get(b, {}).get("stats", {}).get("mean")
            if v is None:
                return None
            if isinstance(v, str) and v.upper() == "NAN":
                return None
            return float(v) if isinstance(v, (int, float)) else None
        
        ndvi = mean("B7")
        if ndvi is None:
            continue
        
        rows.append({
            "date": date_str,
            "B2": mean("B0") or 0, "B3": mean("B1") or 0, "B4": mean("B2") or 0,
            "B5": mean("B3") or 0, "B8": mean("B4") or 0, "B11": mean("B5") or 0,
            "B12": mean("B6") or 0, 
            "NDVI": ndvi,
            "GNDVI": mean("B8") or 0,
            "SAVI": mean("B9") or 0,
            "NDMI": mean("B10") or 0,
            "MSI": mean("B11") or 0,
            "NDWI": mean("B12") or 0,
            "NMDI": mean("B13") or 0,
            "NDRE": mean("B14") or 0,
            "CIredEdge": mean("B15") or 0,
            "CIgreen": mean("B16") or 0,
            "PSRI": mean("B17") or 0,
            "SIPI": mean("B18") or 0
        })
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    return df

def create_analysis_windows(df, window_size, num_windows=4):
    """Create sliding windows for analysis"""
    if df is None or len(df) < window_size:
        return None, None
    
    windows = []
    window_arrays = []
    n = len(df)
    
    # Create numpy array for efficient computation
    feature_cols = ['B2', 'B3', 'B4', 'B5', 'B8', 'B11', 'B12',
                   'NDVI', 'GNDVI', 'SAVI', 'NDMI', 'MSI', 'NDWI', 'NMDI',
                   'NDRE', 'CIredEdge', 'CIgreen', 'PSRI', 'SIPI']
    
    data_array = df[feature_cols].values
    
    # Get most recent windows
    for i in range(min(num_windows, n - window_size + 1)):
        start_idx = n - window_size - i
        if start_idx < 0:
            break
        
        end_idx = start_idx + window_size
        window_array = data_array[start_idx:end_idx]
        window_df = df.iloc[start_idx:end_idx].copy()
        
        windows.append({
            'window_id': f"W{i+1}",
            'data': window_df,
            'array': window_array,
            'start_date': window_df.iloc[0]['date'],
            'end_date': window_df.iloc[-1]['date'],
            'dates_str': f"{window_df.iloc[0]['date'].strftime('%b %d')} - {window_df.iloc[-1]['date'].strftime('%b %d')}"
        })
        window_arrays.append(window_array)
    
    # Return in chronological order
    windows = windows[::-1]
    window_arrays = window_arrays[::-1]
    
    return windows, window_arrays

def generate_mock_data(date_range):
    """Generate realistic mock data for demo"""
    mock_data = []
    current_date = date_range['window_start']
    num_days = min(30, date_range['total_days_needed'])
    
    # Base values with realistic trends
    for i in range(num_days):
        # Simulate nutrient stress development
        progress = i / num_days
        stress_factor = 0.7 + (progress * 0.5)
        
        date_str = current_date.strftime("%Y-%m-%d")
        mock_item = {
            "interval": {"from": f"{date_str}T00:00:00Z"},
            "outputs": {
                "default": {
                    "bands": {
                        "B0": {"stats": {"mean": 0.2}},
                        "B1": {"stats": {"mean": 0.15}},
                        "B2": {"stats": {"mean": 0.1}},
                        "B3": {"stats": {"mean": 0.08}},
                        "B4": {"stats": {"mean": 0.3}},
                        "B5": {"stats": {"mean": 0.05}},
                        "B6": {"stats": {"mean": 0.03}},
                        "B7": {"stats": {"mean": 0.65 - (0.15 * stress_factor)}},  # NDVI
                        "B8": {"stats": {"mean": 0.55 - (0.10 * stress_factor)}},  # GNDVI
                        "B9": {"stats": {"mean": 0.55}},
                        "B10": {"stats": {"mean": 0.3}},
                        "B11": {"stats": {"mean": 0.8 + (0.3 * stress_factor)}},  # MSI
                        "B12": {"stats": {"mean": 0.2}},
                        "B13": {"stats": {"mean": 0.4}},
                        "B14": {"stats": {"mean": 0.25 - (0.07 * stress_factor)}},  # NDRE
                        "B15": {"stats": {"mean": 2.5}},
                        "B16": {"stats": {"mean": 1.8}},
                        "B17": {"stats": {"mean": 0.02 + (0.01 * stress_factor)}},  # PSRI
                        "B18": {"stats": {"mean": 1.2}}
                    }
                }
            }
        }
        mock_data.append(mock_item)
        current_date += timedelta(days=1)
    
    return mock_data

def fetch_data_for_analysis(corners, crop_type, current_stage, current_date=None, num_windows=4):
    """Main function to fetch data for analysis"""
    from config import CROP_CONFIG
    
    if current_date is None:
        current_date = datetime.now()
    elif isinstance(current_date, date):
        current_date = datetime.combine(current_date, datetime.min.time())
    
    config = CROP_CONFIG[crop_type]
    window_size = config['window_size']
    
    # Get days to go back based on stage
    stage_offset = config['stage_offsets'].get(current_stage, 60)
    
    # Total days needed: stage_offset + (num_windows - 1) + window_size
    total_days_needed = stage_offset + (num_windows - 1) + window_size
    
    # Start date
    start_date = current_date - timedelta(days=total_days_needed)
    
    # Adjust for sowing date
    sowing_year = current_date.year
    sowing_start = datetime(sowing_year, config['sowing_start']['month'], config['sowing_start']['day'])
    
    if config['sowing_start']['month'] > config['season_end']['month']:
        if current_date.month < config['sowing_start']['month']:
            sowing_year = current_date.year - 1
    
    sowing_start = datetime(sowing_year, config['sowing_start']['month'], config['sowing_start']['day'])
    
    if start_date < sowing_start:
        start_date = sowing_start
    
    date_info = {
        'window_start': start_date,
        'window_end': current_date,
        'stage_offset': stage_offset,
        'window_size': window_size,
        'num_windows': num_windows,
        'total_days_needed': total_days_needed,
        'current_stage': current_stage
    }
    
    try:
        # Fetch data
        raw_data = fetch_timeseries_data(corners, date_info)
        
        # Process data
        df = process_satellite_data(raw_data)
        
        if df is None:
            print("⚠️ No valid satellite data found, using mock data", file=sys.stderr)
            raw_data = generate_mock_data(date_info)
            df = process_satellite_data(raw_data)
        
        if df is None:
            return None
        
        # Create windows
        windows, window_arrays = create_analysis_windows(df, date_info['window_size'], num_windows)
        
        if not windows:
            return None
        
        return {
            'windows': windows,
            'window_arrays': window_arrays,
            'raw_df': df,
            'date_info': date_info,
            'crop_type': crop_type,
            'current_stage': current_stage,
            'crop_config': CROP_CONFIG[crop_type]
        }
        
    except Exception as e:
        print(f"Error in data fetching: {e}", file=sys.stderr)
        # Return mock data as fallback
        raw_data = generate_mock_data(date_info)
        df = process_satellite_data(raw_data)
        
        if df is not None:
            windows, window_arrays = create_analysis_windows(df, date_info['window_size'], num_windows)
            if windows:
                return {
                    'windows': windows,
                    'window_arrays': window_arrays,
                    'raw_df': df,
                    'date_info': date_info,
                    'crop_type': crop_type,
                    'current_stage': current_stage,
                    'crop_config': CROP_CONFIG[crop_type]
                }
        
        return None

# Add this to your config.py file as well:
"""
# In your config.py, add these environment variable examples:
import os

# Sentinel Hub clients loaded from environment variables
def get_sentinel_clients():
    clients = []
    for i in range(1, 7):
        client_id = os.getenv(f'SENTINEL_CLIENT_ID_{i}')
        client_secret = os.getenv(f'SENTINEL_CLIENT_SECRET_{i}')
        if client_id and client_secret:
            clients.append((client_id, client_secret))
    return clients

CLIENTS = get_sentinel_clients()
"""