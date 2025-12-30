"""
Biomass calculation from NDVI
"""
import numpy as np

def calculate_biomass_score(ndvi_series: np.ndarray) -> float:
    """
    Calculate biomass score using Area Under Curve (AUC) of NDVI
    """
    auc = np.trapz(ndvi_series)
    normalized_auc = auc / len(ndvi_series)
    biomass_score = normalized_auc * 100
    return np.clip(biomass_score, 0, 100)

def estimate_biomass_tons_ha(ndvi_mean: float, crop_type: str) -> float:
    """
    Estimate biomass in tons/hectare based on NDVI
    """
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