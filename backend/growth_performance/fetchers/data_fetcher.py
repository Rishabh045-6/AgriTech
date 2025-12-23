import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

def get_demo_data(corners, crop_type, current_date=None):
    """Get demo data for the app"""
    # Generate mock data similar to the app
    np.random.seed(hash(str(corners)) % 10000)  # Seed based on location
    
    window_size = 30
    dates = pd.date_range(end=current_date or datetime.now(), periods=window_size, freq='D')
    
    # Base NDVI based on crop type
    crop_bases = {
        'wheat': 0.65,
        'rice': 0.70,
        'maize': 0.60,
        'chickpea': 0.55,
        'pigeon_pea': 0.58,
        'beans': 0.62,
        'lentils': 0.57
    }
    
    base_ndvi = crop_bases.get(crop_type, 0.65)
    
    # Create NDVI series with realistic patterns
    trend = np.linspace(-0.001, 0.002, window_size)  # Slight trend
    seasonal = 0.05 * np.sin(np.linspace(0, 2 * np.pi, window_size))
    noise = np.random.normal(0, 0.03, window_size)
    
    ndvi = base_ndvi + trend + seasonal + noise
    ndvi = np.clip(ndvi, 0.2, 0.95)
    
    # Create DataFrame
    df = pd.DataFrame({
        'date': dates,
        'NDVI': ndvi,
        'GNDVI': ndvi * 0.9 + np.random.normal(0, 0.02, window_size),
        'NDMI': ndvi * 0.85 + np.random.normal(0, 0.015, window_size),
        'NDRE': ndvi * 0.88 + np.random.normal(0, 0.018, window_size),
        'SAVI': ndvi * 1.05 + np.random.normal(0, 0.01, window_size)
    })
    
    # Clip values
    for col in df.columns:
        if col != 'date' and ('ND' in col or 'GDVI' in col or 'SAVI' in col):
            df[col] = df[col].clip(-1, 1)
    
    return df

def fetch_data_for_demo(corners, crop_type, current_date=None):
    """Main function to fetch and prepare data for demo"""
    try:
        df = get_demo_data(corners, crop_type, current_date)
        
        # Prepare features in correct format
        feature_columns = [
            'B2', 'B3', 'B4', 'B5', 'B8', 'B11', 'B12',  # Raw bands
            'NDVI', 'GNDVI', 'SAVI', 'NDMI', 'MSI', 'NDWI', 'NMDI',  # Indices
            'NDRE', 'CIredEdge', 'CIgreen', 'PSRI', 'SIPI'  # More indices
        ]
        
        # Ensure all features exist
        for col in feature_columns:
            if col not in df.columns:
                df[col] = 0.0  # Fill missing with 0
        
        # Extract features as numpy array
        features = df[feature_columns].values  # Shape: (window_size, 19)
        
        # Reshape for model: (1, window_size, 19)
        features = features.reshape(1, features.shape[0], features.shape[1])
        
        return {
            'window_features': features,
            'window_df': df,
            'raw_data_count': len(df),
            'date_info': {
                'window_start': df['date'].min(),
                'window_end': df['date'].max(),
                'window_size': len(df)
            }
        }
        
    except Exception as e:
        print(f"Error in fetch_data_for_demo: {str(e)}")
        return None