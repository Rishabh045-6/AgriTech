"""
Fixed growth stage analysis without eval()
"""
import numpy as np
import pandas as pd

def calculate_biomass_score(ndvi_series: np.ndarray) -> float:
    """Calculate biomass score using Area Under Curve (AUC) of NDVI"""
    auc = np.trapz(ndvi_series)
    normalized_auc = auc / len(ndvi_series)
    biomass_score = normalized_auc * 100
    return np.clip(biomass_score, 0, 100)

def estimate_biomass_tons_ha(ndvi_mean: float, crop_type: str) -> float:
    """Estimate biomass in tons/hectare based on NDVI"""
    if ndvi_mean < 0.2:
        base_biomass = 1.0
    elif ndvi_mean < 0.4:
        base_biomass = 3.0
    elif ndvi_mean < 0.6:
        base_biomass = 5.0
    elif ndvi_mean < 0.8:
        base_biomass = 7.0
    else:
        base_biomass = 9.0
    
    crop_adjustments = {
        'rice': 1.2,
        'wheat': 1.1,
        'maize': 1.3,
        'chickpea': 0.8,
        'pigeon_pea': 0.9,
        'beans': 0.7,
        'lentils': 0.7
    }
    
    adjustment = crop_adjustments.get(crop_type, 1.0)
    return base_biomass * adjustment

def stats(series):
    """Basic statistics for time series"""
    return {
        "mean": np.mean(series),
        "std": np.std(series),
        "min": np.min(series),
        "max": np.max(series),
        "slope": np.polyfit(np.arange(len(series)), series, 1)[0]
    }

def growth_rate_score(ndvi):
    """Calculate growth rate score based on NDVI slope"""
    s = stats(ndvi)["slope"]
    return np.clip((s + 0.03) / 0.06 * 100, 0, 100)

def biomass_score(ndvi):
    """Calculate biomass score based on NDVI mean"""
    m = stats(ndvi)["mean"]
    return np.clip((m - 0.2) / 0.6 * 100, 0, 100)

def stability_score(ndvi):
    """Calculate stability score based on NDVI std deviation"""
    std = stats(ndvi)["std"]
    return np.clip(100 - (std / 0.15 * 100), 0, 100)

def stage_progress_score(ndvi, stage):
    """Calculate stage progress score based on crop stage"""
    peak = stats(ndvi)["max"]
    
    expected = {
        1: (0.3, 0.6),
        2: (0.6, 0.8),
        3: (0.7, 0.9)
    }
    
    low, high = expected.get(stage, (0.3, 0.8))
    
    if peak < low:
        return 30
    elif peak > high:
        return 85
    return 60 + (peak - low) / (high - low) * 40

def calculate_all_scores(ndvi_series, stage=2):
    """Calculate all growth scores"""
    return {
        'growth_rate': growth_rate_score(ndvi_series),
        'biomass': biomass_score(ndvi_series),
        'stability': stability_score(ndvi_series),
        'stage_progress': stage_progress_score(ndvi_series, stage)
    }

def overall_health_score(growth, biomass, stability, stage_progress):
    """Calculate weighted overall health score"""
    return round(
        0.35 * growth +
        0.30 * biomass +
        0.20 * stability +
        0.15 * stage_progress,
        1
    )

def calculate_health_report(scores):
    """Generate a comprehensive health report"""
    overall = overall_health_score(
        scores['growth_rate'],
        scores['biomass'],
        scores['stability'],
        scores['stage_progress']
    )
    
    if overall >= 80:
        status = "Excellent"
        color = "green"
        recommendation = "Crops are performing optimally."
    elif overall >= 60:
        status = "Good"
        color = "blue"
        recommendation = "Crops are healthy."
    elif overall >= 40:
        status = "Fair"
        color = "orange"
        recommendation = "Some improvement needed."
    else:
        status = "Poor"
        color = "red"
        recommendation = "Immediate attention required."
    
    return {
        'overall_score': overall,
        'status': status,
        'color': color,
        'recommendation': recommendation
    }