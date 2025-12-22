import pandas as pd
import numpy as np
import os
import time
from datetime import datetime, timedelta, date  # Add 'date' to imports
from sentinelhub import (
    CRS, DataCollection, Geometry,
    SentinelHubStatistical, SHConfig
)
from shapely.geometry import Polygon

# ===============================
# CROP CONFIGURATIONS
# ===============================
CROP_CONFIG = {
    'rice': {
        'window_size': 8,
        'sowing_start': {'month': 6, 'day': 1},   # June 1
        'season_end': {'month': 10, 'day': 31},   # Oct 31
        'model_path': r"C:\Users\Arun\Downloads\Crops\Rice\Stage classification\rice_model.pt"
    },
    'wheat': {
        'window_size': 12,
        'sowing_start': {'month': 11, 'day': 1},  # Nov 1
        'season_end': {'month': 4, 'day': 30},    # Apr 30 (next year)
        'model_path': r"C:\Users\Arun\Downloads\Crops\Wheat\Stage classification\wheat_model.pt"
    },
    'maize': {
        'window_size': 8,
        'sowing_start': {'month': 5, 'day': 15},  # May 15
        'season_end': {'month': 9, 'day': 30},    # Sep 30
        'model_path': r"C:\Users\Arun\Downloads\Crops\Maize\Stage classification\maize_model.pt"
    },
    'chickpea': {
        'window_size': 7,
        'sowing_start': {'month': 10, 'day': 15}, # Oct 15
        'season_end': {'month': 3, 'day': 31},    # Mar 31 (next year)
        'model_path': r"C:\Users\Arun\Downloads\Crops\Chickpea\Stage classification\chickpea_model.pt"
    },
    'pigeon_pea': {
        'window_size': 7,
        'sowing_start': {'month': 6, 'day': 1},   # June 1
        'season_end': {'month': 12, 'day': 31},   # Dec 31
        'model_path': r"C:\Users\Arun\Downloads\Crops\PigeonPea\Stage classification\pigeonpea_model.pt"
    },
    'beans': {
        'window_size': 6,
        'sowing_start': {'month': 2, 'day': 1},   # Feb 1
        'season_end': {'month': 5, 'day': 31},    # May 31
        'model_path': r"C:\Users\Arun\Downloads\Crops\Beans\Stage classification\beans_model.pt"
    },
    'lentils': {
        'window_size': 7,
        'sowing_start': {'month': 10, 'day': 1},  # Oct 1
        'season_end': {'month': 3, 'day': 31},    # Mar 31 (next year)
        'model_path': r"C:\Users\Arun\Downloads\Crops\Lentils\Stage classification\lentils_model.pt"
    }
}

# ===============================
# SENTINEL HUB CONFIG
# ===============================
CLIENTS = [
    ("99dff32e-01cf-4c21-9b43-aef3262ab2a3", "vjMQcfTYxMqI32qlB6PCKPjgzlVqL1dk"),
    ("5b7528ec-fee8-4176-96d1-0784b4cd5f0c", "be3sp3EbnoA8VzEQlH1jFUfeMbzi1OwU"),
    ("ef4cab95-f360-4bd8-a5a6-76766f01dfdc", "ikttFkyFaayLXGMOgul6zUvfYa7BsnfI"),
    ("58eabf3f-0d1b-476f-8e4a-ac573ec49b67", "q1xcKSrwTHUvKGCt9MZKnsMRqTsFt6Yz"),
    ("73f638c7-de16-4d7e-8779-faf7ec2b4f05", "I6fA2rbLE376HqF0uxJlpKPDWvtUDVf1"),
    ("1ab951e7-be10-4e1f-8a55-1007606aef50", "wYg7AvtIitZCzjOTmNyp0kS9Jil2HV5g"),
]

current_client_idx = 0

def get_config():
    global current_client_idx
    cfg = SHConfig()
    cfg.sh_client_id = CLIENTS[current_client_idx][0]
    cfg.sh_client_secret = CLIENTS[current_client_idx][1]
    return cfg

# ===============================
# EVALSCRIPT (Same as before)
# ===============================
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
  
  // Convert to reflectance (0-1)
  let B02 = s.B02 / 10000.0;
  let B03 = s.B03 / 10000.0;
  let B04 = s.B04 / 10000.0;
  let B05 = s.B05 / 10000.0;
  let B08 = s.B08 / 10000.0;
  let B11 = s.B11 / 10000.0;
  let B12 = s.B12 / 10000.0;

  // Calculate indices
  let NDVI = (B08 - B04) / (B08 + B04 + eps);
  let GNDVI = (B08 - B03) / (B08 + B03 + eps);
  let SAVI = 1.5 * (B08 - B04) / (B08 + B04 + 0.5 + eps);
  let NDMI = (B08 - B11) / (B08 + B11 + eps);
  let MSI = B11 / (B08 + eps);
  let NDWI = (B03 - B08) / (B03 + B08 + eps);
  let NMDI = (B08 - (B11 - B12)) / (B08 + (B11 - B12) + eps);
  let NDRE = (B08 - B05) / (B08 + B05 + eps);
  let CIredEdge = (B08 / (B05 + eps)) - 1;
  let CIgreen = (B08 / (B03 + eps)) - 1;
  let PSRI = (B04 - B03) / (B05 + eps);
  let SIPI = (B08 - B02) / (B08 - B04 + eps);
  
  // Bound extreme values to reasonable ranges
  function clamp(val, min, max) {
    return Math.max(min, Math.min(max, val));
  }
  
  NDVI = clamp(NDVI, -1, 1);
  GNDVI = clamp(GNDVI, -1, 1);
  SAVI = clamp(SAVI, -1, 1);
  NDMI = clamp(NDMI, -1, 1);
  MSI = clamp(MSI, 0, 3);  // MSI > 3 is unrealistic
  NDWI = clamp(NDWI, -1, 1);
  NMDI = clamp(NMDI, -1, 1);
  NDRE = clamp(NDRE, -1, 1);
  CIredEdge = clamp(CIredEdge, -1, 3);  // Typically < 2
  CIgreen = clamp(CIgreen, -1, 5);      // Typically < 4
  PSRI = clamp(PSRI, -1, 2);           // Typically < 1
  SIPI = clamp(SIPI, 0, 2.5);          // Typically 0.5-2.0

  return {
    default: [
      // RAW BANDS (normalized to 0-1)
      B02, B03, B04, B05, B08, B11, B12,
      // BOUNDED INDICES
      NDVI, GNDVI, SAVI, NDMI, MSI, NDWI, NMDI,
      NDRE, CIredEdge, CIgreen, PSRI, SIPI
    ],
    dataMask: [s.dataMask]
  };
}
"""

# ===============================
# DATA FETCHING FUNCTIONS
# ===============================
def calculate_date_range(crop_type, current_date=None):
    """Calculate date range for display purposes"""
    if current_date is None:
        current_date = datetime.now()
    elif isinstance(current_date, date) and not isinstance(current_date, datetime):
        # Convert date to datetime if it's a date object
        current_date = datetime.combine(current_date, datetime.min.time())
    
    config = CROP_CONFIG[crop_type]
    
    sowing_start = datetime(current_date.year, config['sowing_start']['month'], config['sowing_start']['day'])
    
    if config['season_end']['month'] < config['sowing_start']['month']:
        season_end = datetime(current_date.year + 1, config['season_end']['month'], config['season_end']['day'])
    else:
        season_end = datetime(current_date.year, config['season_end']['month'], config['season_end']['day'])
    
    return {
        'window_start': sowing_start,
        'window_end': season_end,
        'season_start': sowing_start,
        'season_end': season_end,
        'window_size': config['window_size']
    }

def fetch_timeseries_for_polygon(corners, date_range, retries=3):
    """Fetch timeseries data for a polygon"""
    global current_client_idx
    
    # Create polygon from corners
    # corners should be list of (lon, lat) tuples
    geometry = Geometry(Polygon(corners), CRS.WGS84)
    
    date_from = date_range['window_start'].strftime("%Y-%m-%d")
    date_to = date_range['window_end'].strftime("%Y-%m-%d")
    
    print(f"Fetching data from {date_from} to {date_to}")
    
    while current_client_idx < len(CLIENTS):
        config = get_config()
        
        for attempt in range(retries):
            try:
                request = SentinelHubStatistical(
                    aggregation={
                        "timeRange": {
                            "from": f"{date_from}T00:00:00Z",
                            "to": f"{date_to}T23:59:59Z"
                        },
                        "aggregationInterval": {"of": "P1D"},  # Daily aggregation
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
                                "maxCloudCoverage": 40
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
                
                # Switch key if funds exhausted
                if "insufficient" in msg or "payment" in msg or "quota" in msg:
                    print(f"Client {current_client_idx+1} exhausted. Switching key...")
                    current_client_idx += 1
                    break
                
                print(f"Retry {attempt+1}/{retries}: {e}")
                time.sleep(10)
    
    raise RuntimeError("All Sentinel Hub accounts exhausted")

def process_raw_data(raw_data):
    """Process raw API response into clean DataFrame"""
    rows = []
    
    for item in raw_data:
        date = item["interval"]["from"][:10]
        bands = item["outputs"]["default"]["bands"]
        
        # Skip if no data
        if not bands or "B0" not in bands:
            continue
        
        # Helper to safely extract mean
        def mean(b):
            v = bands.get(b, {}).get("stats", {}).get("mean")
            if v is None:
                return None
            if isinstance(v, str) and v.upper() == "NAN":
                return None
            return v
        
        # Skip if NDVI (band B7) is missing
        if mean("B7") is None:
            continue
        
        # Get all values directly from evalscript
        # The evalscript already calculates indices, so use them
        b2 = mean("B0")  # These should be reflectance values
        b3 = mean("B1")
        b4 = mean("B2")
        b5 = mean("B3")
        b8 = mean("B4")
        b11 = mean("B5")
        b12 = mean("B6")
        
        # Use the indices calculated in evalscript
        ndvi = mean("B7")
        gndvi = mean("B8")
        savi = mean("B9")
        ndmi = mean("B10")
        msi = mean("B11")
        ndwi = mean("B12")
        nmdi = mean("B13")
        ndre = mean("B14")
        cired_edge = mean("B15")
        cigreen = mean("B16")
        psri = mean("B17")
        sipi = mean("B18")
        
        # Apply reasonable bounds to handle any extreme values
        def bound(val, min_val, max_val, default=None):
            if val is None:
                return default
            if val < min_val or val > max_val:
                # If value is extreme, use a reasonable default
                return default if default is not None else (min_val + max_val) / 2
            return val
        
        rows.append({
            "date": date,
            # RAW BANDS - use as-is (should be 0-1 reflectance)
            "B2": bound(b2, 0, 1, 0.1),
            "B3": bound(b3, 0, 1, 0.1),
            "B4": bound(b4, 0, 1, 0.1),
            "B5": bound(b5, 0, 1, 0.1),
            "B8": bound(b8, 0, 1, 0.2),
            "B11": bound(b11, 0, 1, 0.1),
            "B12": bound(b12, 0, 1, 0.1),
            # INDICES with reasonable bounds
            "NDVI": bound(ndvi, -1, 1, 0.3),
            "GNDVI": bound(gndvi, -1, 1, 0.3),
            "SAVI": bound(savi, -1, 1, 0.3),
            "NDMI": bound(ndmi, -1, 1, 0.1),
            "MSI": bound(msi, 0, 3, 1.0),
            "NDWI": bound(ndwi, -1, 1, -0.1),
            "NMDI": bound(nmdi, -1, 1, 0.1),
            "NDRE": bound(ndre, -1, 1, 0.2),
            "CIredEdge": bound(cired_edge, -1, 3, 1.0),
            "CIgreen": bound(cigreen, -1, 5, 2.0),
            "PSRI": bound(psri, -1, 2, 0.1),
            "SIPI": bound(sipi, 0, 3, 1.2),
        })
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Fill any remaining NaN values with column means
    for col in df.columns:
        if col != 'date' and df[col].isna().any():
            col_mean = df[col].mean()
            if pd.notna(col_mean):
                df[col] = df[col].fillna(col_mean)
            else:
                df[col] = df[col].fillna(0)
    
    print(f"\nData summary:")
    print(f"NDVI: {df['NDVI'].mean():.3f} ± {df['NDVI'].std():.3f}")
    print(f"MSI: {df['MSI'].mean():.3f} ± {df['MSI'].std():.3f}")
    print(f"CIredEdge: {df['CIredEdge'].mean():.3f} ± {df['CIredEdge'].std():.3f}")
    
    return df

def create_model_window(df, window_size):
    """Create window for model input from available data"""
    if df is None or len(df) == 0:
        return None
    
    # If we have exactly window_size days, perfect
    if len(df) >= window_size:
        # Take the most recent window_size days
        recent_df = df.tail(window_size).copy()
        
        # Ensure exactly window_size rows
        if len(recent_df) == window_size:
            return recent_df
    
    # If we have fewer than window_size days, pad with most recent data
    print(f"Only {len(df)} valid days found. Padding to {window_size} days...")
    
    # Create new DataFrame with required window_size
    window_dates = []
    window_data = []
    
    # Start from most recent date and go backwards
    for i in range(window_size):
        if i < len(df):
            # Use available data
            idx = len(df) - 1 - i
            window_dates.append(df.iloc[idx]['date'])
            window_data.append(df.iloc[idx].to_dict())
        else:
            # Pad with most recent available data
            window_dates.append(df.iloc[-1]['date'] - timedelta(days=(i - len(df) + 1) * 6))
            window_data.append(df.iloc[-1].to_dict())
    
    # Create DataFrame and sort chronologically (oldest to newest)
    padded_df = pd.DataFrame(window_data)
    padded_df = padded_df.sort_values('date').reset_index(drop=True)
    
    return padded_df

def prepare_features_for_model(window_df, crop_type):
    """Prepare features in correct format for model"""
    if window_df is None:
        return None
    
    # Select features in correct order
    feature_columns = [
        'B2', 'B3', 'B4', 'B5', 'B8', 'B11', 'B12',  # Raw bands
        'NDVI', 'GNDVI', 'SAVI', 'NDMI', 'MSI', 'NDWI', 'NMDI',  # Indices
        'NDRE', 'CIredEdge', 'CIgreen', 'PSRI', 'SIPI'  # More indices
    ]
    
    # Check if all features are present
    missing_features = [col for col in feature_columns if col not in window_df.columns]
    if missing_features:
        print(f"Warning: Missing features: {missing_features}")
        # Fill with 0 or appropriate value
        for col in missing_features:
            window_df[col] = 0
    
    # Extract features as numpy array
    features = window_df[feature_columns].values  # Shape: (window_size, 19)
    
    # Reshape for model: (1, window_size, 19)
    features = features.reshape(1, features.shape[0], features.shape[1])
    
    return features

# ===============================
# MAIN FETCHING FUNCTION
# ===============================
def fetch_data_for_demo(corners, crop_type, current_date=None):
    """
    Main function to fetch and prepare data for demo
    
    Args:
        corners: List of (lon, lat) tuples defining polygon
        crop_type: One of 'rice', 'wheat', 'maize', 'chickpea', 'pigeon_pea', 'beans', 'lentils'
        current_date: Date to use as reference (defaults to today)
    
    Returns:
        dict containing:
            - window_features: numpy array for model input
            - window_df: DataFrame with dates and features
            - date_info: Date range information
            - raw_data_count: Number of valid days fetched
    """
    print(f"\n{'='*60}")
    print(f"FETCHING DATA FOR {crop_type.upper()}")
    print(f"{'='*60}")
    
    # Validate crop type
    if crop_type not in CROP_CONFIG:
        raise ValueError(f"Invalid crop type: {crop_type}. Choose from: {list(CROP_CONFIG.keys())}")
    
    # Calculate date range
    date_info = calculate_date_range(crop_type, current_date)
    window_size = CROP_CONFIG[crop_type]['window_size']
    
    print(f"Crop: {crop_type}")
    print(f"Window size: {window_size} days")
    print(f"Season: {date_info['season_start'].strftime('%Y-%m-%d')} to {date_info['season_end'].strftime('%Y-%m-%d')}")
    print(f"Fetching window: {date_info['window_start'].strftime('%Y-%m-%d')} to {date_info['window_end'].strftime('%Y-%m-%d')}")
    
    # Fetch data from Sentinel Hub
    print("\nFetching data from Sentinel Hub...")
    raw_data = fetch_timeseries_for_polygon(corners, date_info)
    
    # Process data
    print("Processing data...")
    df = process_raw_data(raw_data)
    
    if df is None:
        print("No valid data found!")
        return None
    
    print(f"Found {len(df)} valid days of data")
    
    # Create window for model
    window_df = create_model_window(df, window_size)
    
    if window_df is None:
        print("Failed to create window!")
        return None
    
    # Prepare features
    features = prepare_features_for_model(window_df, crop_type)
    
    if features is None:
        print("Failed to prepare features!")
        return None
    
    print(f"\nSuccessfully created window of shape: {features.shape}")
    print(f"Window dates: {window_df['date'].min().strftime('%Y-%m-%d')} to {window_df['date'].max().strftime('%Y-%m-%d')}")
    
    return {
        'window_features': features,
        'window_df': window_df,
        'date_info': date_info,
        'raw_data_count': len(df),
        'crop_config': CROP_CONFIG[crop_type]
    }

# ===============================
# EXAMPLE USAGE
# ===============================
if __name__ == "__main__":
    # Example polygon corners (rectangle in Punjab, India)
    corners = [
        (75.0, 30.0),  # Bottom-left
        (75.0, 30.1),  # Top-left
        (75.1, 30.1),  # Top-right
        (75.1, 30.0),  # Bottom-right
        (75.0, 30.0)   # Close polygon
    ]
    
    # Test with wheat (current date will be today)
    try:
        result = fetch_data_for_demo(
            corners=corners,
            crop_type='wheat',
            current_date=datetime(2024, 12, 19)  # Or use None for today
        )
        
        if result:
            print("\n✓ Data fetch successful!")
            print(f"Window shape: {result['window_features'].shape}")
            print(f"Dates in window: {len(result['window_df'])} days")
            print(f"NDVI trend: {result['window_df']['NDVI'].mean():.3f} (avg)")
            
            # You would now load the model and make prediction here
            # model = load_model(result['crop_config']['model_path'])
            # prediction = model.predict(result['window_features'])
            
    except Exception as e:
        print(f"Error: {e}")