"""
Water stress calculation from NDMI and MSI
"""
import numpy as np
from typing import Dict

def calculate_water_stress_score(ndmi_series: np.ndarray, msi_series: np.ndarray) -> float:
    """
    Calculate water stress score
    
    NDMI (Normalized Difference Moisture Index): Higher = more moisture
    MSI (Moisture Stress Index): Higher = more stress
    
    Formula: 0.6 * NDMI.mean() - 0.4 * MSI.mean()
    Positive = good moisture, Negative = water stress
    """
    
    # Calculate means
    ndmi_mean = np.nanmean(ndmi_series)
    msi_mean = np.nanmean(msi_series)
    
    # Calculate stress score
    stress_score = 0.6 * ndmi_mean - 0.4 * msi_mean
    
    return stress_score

def get_water_stress_level(stress_score: float) -> Dict:
    """
    Convert stress score to categorical level
    """
    if stress_score > 0.1:
        return {
            'level': 'low',
            'label': 'Adequate Moisture',
            'color': 'green',
            'multiplier': 0.95,
            'recommendation': 'Moisture levels are adequate.'
        }
    elif stress_score > -0.1:
        return {
            'level': 'medium',
            'label': 'Moderate Stress',
            'color': 'orange',
            'multiplier': 0.85,
            'recommendation': 'Consider irrigation if no rain expected.'
        }
    else:
        return {
            'level': 'high',
            'label': 'High Water Stress',
            'color': 'red',
            'multiplier': 0.70,
            'recommendation': 'Immediate irrigation recommended.'
        }

def calculate_crop_water_requirement(
    crop_type: str,
    stage: int,
    stress_level: str
) -> float:
    """
    Estimate crop water requirement in mm/day
    
    Based on FAO crop coefficients and stress levels
    """
    # Base water requirements by crop (mm/day)
    base_requirements = {
        'rice': 6.0,
        'wheat': 4.5,
        'maize': 5.0,
        'chickpea': 3.5,
        'pigeon_pea': 3.0,
        'beans': 4.0,
        'lentils': 3.0
    }
    
    # Stage multipliers (FAO Kc values approximation)
    stage_multipliers = {
        1: 0.4,
        2: 1.0,
        3: 0.7
    }
    
    # Stress adjustments
    stress_multipliers = {
        'low': 1.0,
        'medium': 1.2,
        'high': 1.5
    }
    
    base = base_requirements.get(crop_type, 4.0)
    stage_mult = stage_multipliers.get(stage, 1.0)
    stress_mult = stress_multipliers.get(stress_level, 1.0)
    
    water_req = base * stage_mult * stress_mult
    
    return water_req