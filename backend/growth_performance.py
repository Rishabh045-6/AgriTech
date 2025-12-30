import sys
import json
import numpy as np
import pandas as pd
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

def calculate_growth_scores(ndvi_series):
    """Calculate growth performance scores"""
    # Growth rate score (0-100)
    if len(ndvi_series) > 1:
        trend = np.polyfit(range(len(ndvi_series)), ndvi_series, 1)[0]
        growth_score = max(0, min(100, (trend + 0.005) * 10000))
    else:
        growth_score = 50
    
    # Biomass score (0-100)
    avg_ndvi = np.mean(ndvi_series)
    biomass_score = avg_ndvi * 100
    
    # Stability score (0-100)
    std_ndvi = np.std(ndvi_series)
    stability_score = max(0, min(100, (0.1 - std_ndvi) * 1000))
    
    # Overall score
    overall_score = (growth_score + biomass_score + stability_score) / 3
    
    return {
        'growth_rate': float(growth_score),
        'biomass': float(biomass_score),
        'stability': float(stability_score),
        'overall_score': float(overall_score)
    }

def calculate_health_report(scores):
    """Calculate health report based on scores"""
    overall = scores['overall_score']
    
    if overall >= 80:
        status = "Excellent"
        color = "green"
        recommendation = "Crop is performing exceptionally well. Continue current practices."
    elif overall >= 60:
        status = "Good"
        color = "green"
        recommendation = "Crop health is good. Monitor for any changes."
    elif overall >= 40:
        status = "Fair"
        color = "orange"
        recommendation = "Crop needs attention. Consider fertilization or pest control."
    else:
        status = "Poor"
        color = "red"
        recommendation = "Immediate action required. Check for diseases, pests, or water stress."
    
    return {
        'overall_score': float(overall),
        'status': status,
        'color': color,
        'recommendation': recommendation
    }

def main():
    if len(sys.argv) != 4:
        error_msg = f'Usage: python growth_performance.py <farmer_id> <crop_type> <coordinates_json>. Got {len(sys.argv)} args'
        print(json.dumps({
            'error': error_msg,
            'success': False
        }))
        return
    
    farmer_id = sys.argv[1]
    crop_type = sys.argv[2]
    coordinates_json = sys.argv[3]
    
    try:
        coordinates = json.loads(coordinates_json)
        
        # Get demo data
        df = get_demo_data(coordinates, crop_type)
        
        # Calculate scores
        ndvi_series = df['NDVI'].values
        scores = calculate_growth_scores(ndvi_series)
        report = calculate_health_report(scores)
        
        # Prepare NDVI trend data
        ndvi_trend = []
        for _, row in df.iterrows():
            ndvi_trend.append({
                'date': str(row['date']),
                'ndvi': float(row['NDVI'])
            })
        
        # Prepare result
        result = {
            'success': True,
            'farmerId': farmer_id,
            'cropType': crop_type,
            'scores': scores,
            'report': report,
            'ndviTrend': ndvi_trend,
            'healthMetrics': {
                'growth_rate': {'level': f"{scores['growth_rate']:.1f}", 'status': 'Good' if scores['growth_rate'] >= 60 else 'Needs attention'},
                'biomass': {'level': f"{scores['biomass']:.1f}", 'status': 'Good' if scores['biomass'] >= 60 else 'Needs attention'},
                'stability': {'level': f"{scores['stability']:.1f}", 'status': 'Good' if scores['stability'] >= 60 else 'Needs attention'}
            },
            'data_summary': {
                'mean_ndvi': float(df['NDVI'].mean()),
                'min_ndvi': float(df['NDVI'].min()),
                'max_ndvi': float(df['NDVI'].max()),
                'std_ndvi': float(df['NDVI'].std())
            }
        }
        
        print(json.dumps(result))
        
    except Exception as e:
        error_msg = f'Growth performance analysis failed: {str(e)}'
        print(json.dumps({
            'error': error_msg,
            'success': False
        }))

if __name__ == "__main__":
    main()