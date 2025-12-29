"""
Enhanced data fetcher with water stress analysis
"""
import pandas as pd
import numpy as np
import os
import time
from datetime import datetime, timedelta, date
from sentinelhub import (
    CRS, DataCollection, Geometry,
    SentinelHubStatistical, SHConfig
)
from shapely.geometry import Polygon

# Import your water stress analysis
from water_stress_analysis import (
    analyze_all_windows, 
    get_moisture_status
)


# Import CROP_CONFIG from config, not define it here
from config import CROP_CONFIG, CLIENTS, EVALSCRIPT

# Import your water stress analysis
from water_stress_analysis import (
    analyze_all_windows, 
    calculate_window_water_stress, 
    get_moisture_status, 
    get_stage_aware_irrigation_advice,
    identify_stress_drivers
)


# ===============================
# SENTINEL HUB CONFIGURATION
# ===============================
CLIENTS = [
    ("c30e60ba-ea66-4447-a1e8-af3207786289", "EPfJJYksVRwotM0yX8qTJukW0GKAUAn6"),
    ("243d120c-aa15-4329-9365-7c970799d3ee", "uXC8gl25RML4ZILOuYCYlrHl7svleRcK"),
    ("036ec31e-54ee-4347-9267-199f5480fb3f", "ETUSehSpkGZUqjBixrjz8J3VN51gsw4S"),
    ("9bbe62fb-7b30-47d8-b903-ae6b075d9349", "VIlm7ofRmIPTvClNtCQ5KXWLOYLqymL3"),
    ("9ee87d64-a7df-4641-a4c5-df30f15b74a2", "UG3ic3LN454SB79EQA43b1i1D6O9RzXD"),
    ("26a07095-ca66-4a18-8890-25cdbdea4542", "cFdacSjQrVj6m0DdOtKgpSKDic26Nb0Z"),
]

current_client_idx = 0

def get_config():
    global current_client_idx
    cfg = SHConfig()
    cfg.sh_client_id = CLIENTS[current_client_idx][0]
    cfg.sh_client_secret = CLIENTS[current_client_idx][1]
    return cfg

# EVALSCRIPT (same as before)
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

# ===============================
# WATER STRESS ANALYSIS INTEGRATION
# ===============================
def create_analysis_windows(df, window_size, num_windows=4):
    """Create sliding windows for analysis including water stress"""
    if df is None or len(df) < window_size:
        return None, None
    
    windows = []
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
            'dates_str': f"{window_df.iloc[0]['date'].strftime('%b %d')} - {window_df.iloc[-1]['date'].strftime('%b %d')}",
            'mean_values': window_df[feature_cols].mean().to_dict()
        })
    
    # Return in chronological order
    windows = windows[::-1]
    
    return windows

def fetch_data_for_analysis(corners, crop_type, current_stage, current_date=None, num_windows=4):
    """Enhanced fetcher that includes water stress analysis"""
    # Calculate date range based on stage (you already have this logic)
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
    
    # Fetch data (your existing fetch logic)
    raw_data = fetch_timeseries_data(corners, date_info)
    
    # Process data (your existing process logic)
    df = process_satellite_data(raw_data)
    
    if df is None:
        return None
    
    # Create windows
    windows = create_analysis_windows(df, date_info['window_size'], num_windows)
    
    if not windows:
        return None
    
    # Perform water stress analysis
    water_stress_analysis = analyze_all_windows(windows, current_stage)
    
    return {
        'windows': windows,
        'raw_df': df,
        'date_info': date_info,
        'crop_type': crop_type,
        'current_stage': current_stage,
        'crop_config': CROP_CONFIG[crop_type],
        'water_stress_analysis': water_stress_analysis  # ADD WATER STRESS ANALYSIS
    }

def fetch_timeseries_data(corners, date_range, max_cloud=80):
    """Your existing fetch logic"""
    global current_client_idx
    
    geometry = Geometry(Polygon(corners), CRS.WGS84)
    date_from = date_range['window_start'].strftime("%Y-%m-%d")
    date_to = date_range['window_end'].strftime("%Y-%m-%d")
    
    while current_client_idx < len(CLIENTS):
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
                continue
            time.sleep(3)
    
    # Fallback to mock data
    return generate_mock_data(date_range)

def process_satellite_data(raw_data):
    """Your existing process logic"""
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

def generate_mock_data(date_range):
    """Your existing mock data generator"""
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