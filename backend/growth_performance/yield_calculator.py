"""
Main yield calculation logic
"""
import numpy as np
from typing import Dict, Tuple

# National averages for Indian crops (kg/ha)
NATIONAL_AVERAGES = {
    'rice': 3700,
    'wheat': 3200,
    'maize': 3800,
    'chickpea': 1100,
    'pigeon_pea': 950,
    'beans': 850,
    'lentils': 750
}

# Base potential yields
BASE_YIELDS = {
    'rice': 4000,
    'wheat': 3500,
    'maize': 4500,
    'chickpea': 1200,
    'pigeon_pea': 1000,
    'beans': 900,
    'lentils': 800
}

# Stage multipliers
STAGE_MULTIPLIERS = {1: 0.6, 2: 0.8, 3: 1.0}

def estimate_yield_kg_ha(
    yield_score: float,
    crop_type: str,
    stage: int
) -> Tuple[float, Dict]:
    """
    Estimate yield in kg/hectare based on yield score
    """
    # Get base values with defaults
    base_yield = BASE_YIELDS.get(crop_type, 2000)
    stage_mult = STAGE_MULTIPLIERS.get(stage, 0.8)
    national_avg = NATIONAL_AVERAGES.get(crop_type, 2000)
    
    # Calculate estimated yield
    estimated_yield = base_yield * (yield_score / 100) * stage_mult
    
    # Create COMPLETE breakdown with ALL keys used in app.py
    breakdown = {
        'base_yield': base_yield,
        'yield_score_effect': yield_score / 100,
        'stage_multiplier': stage_mult,
        'water_stress_multiplier': 0.9,  # Default value
        'disease_multiplier': 1.0,       # Default value
        'pest_multiplier': 1.0,          # Default value
        'estimated_yield': estimated_yield,
        'national_average': national_avg,
        'expected_potential': base_yield * stage_mult
    }
    
    return estimated_yield, breakdown

def get_yield_category(yield_score: float) -> Dict:
    """
    Get yield category based on score
    """
    if yield_score >= 85:
        return {'name': 'excellent', 'label': 'Excellent Yield', 'color': '#4CAF50'}
    elif yield_score >= 70:
        return {'name': 'high', 'label': 'High Yield', 'color': '#6BCF7F'}
    elif yield_score >= 40:
        return {'name': 'medium', 'label': 'Medium Yield', 'color': '#FFD93D'}
    else:
        return {'name': 'low', 'label': 'Low Yield', 'color': '#FF6B6B'}

def calculate_yield_score(
    window_features: np.ndarray,
    stage_prediction: int,
    disease_prediction: int,
    pest_prediction: int,
    ndvi_series: np.ndarray
) -> Tuple[float, Dict]:
    """
    Calculate yield score based on multiple factors
    """
    # Extract NDVI from features (assuming it's at index 7)
    NDVI = ndvi_series  # Use the actual NDVI series
    
    # Basic scores
    biomass_score = np.mean(NDVI) * 100
    water_stress_score = 70  # Placeholder
    growth_rate = 75  # Placeholder
    stability = 80  # Placeholder
    
    # Calculate penalties
    disease_penalty = 0.25 if disease_prediction == 1 else 0.0
    pest_penalty = 0.2 if pest_prediction == 2 else (0.1 if pest_prediction == 1 else 0.0)
    
    # Base score
    base_score = (
        0.35 * biomass_score +
        0.25 * growth_rate +
        0.20 * (100 - water_stress_score) +
        0.20 * stability
    )
    
    # Apply penalties
    final_score = base_score * (1 - disease_penalty - pest_penalty)
    final_score = np.clip(final_score, 0, 100)
    
    # Component scores
    component_scores = {
        'biomass': biomass_score,
        'water_stress': water_stress_score,
        'growth_rate': growth_rate,
        'stability': stability,
        'disease_penalty': disease_penalty * 100,
        'pest_penalty': pest_penalty * 100,
        'base_score': base_score,
        'final_score': final_score
    }
    
    return final_score, component_scores