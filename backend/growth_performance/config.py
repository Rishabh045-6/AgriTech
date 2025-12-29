import os
from datetime import datetime

# Yield-specific configuration
YIELD_CONFIG = {
    'default_crop': 'wheat',
    'default_stage': 2,
    'default_location': {
        'name': 'Punjab, India',
        'corners': [
            (75.0, 30.0),  # Bottom-left
            (75.0, 30.1),  # Top-left
            (75.1, 30.1),  # Top-right
            (75.1, 30.0),  # Bottom-right
            (75.0, 30.0)   # Close polygon
        ]
    },
    'demo_date': datetime(2024, 12, 19),
    'use_mock_data': True
}

# Color scheme
COLORS = {
    'primary': '#2E8B57',     # Sea Green
    'secondary': '#3CB371',   # Medium Sea Green
    'accent': '#90EE90',      # Light Green
    'warning': '#FFA500',     # Orange
    'danger': '#FF4500',      # Orange Red
    'yield_low': '#FF6B6B',   # Red
    'yield_medium': '#FFD93D',# Yellow
    'yield_high': '#6BCF7F',  # Green
    'yield_excellent': '#4CAF50' # Dark Green
}

# Available crops
CROPS = [
    'rice', 'wheat', 'maize', 'chickpea', 
    'pigeon_pea', 'beans', 'lentils'
]

# Growth stages
STAGES = {
    1: 'Vegetative',
    2: 'Reproductive',
    3: 'Ripening/Maturity'
}

# Yield categories
YIELD_CATEGORIES = {
    'low': {'min': 0, 'max': 40, 'color': COLORS['yield_low'], 'label': 'Low Yield'},
    'medium': {'min': 40, 'max': 70, 'color': COLORS['yield_medium'], 'label': 'Medium Yield'},
    'high': {'min': 70, 'max': 85, 'color': COLORS['yield_high'], 'label': 'High Yield'},
    'excellent': {'min': 85, 'max': 100, 'color': COLORS['yield_excellent'], 'label': 'Excellent Yield'}
}

# Model paths
MODEL_PATHS = {
    'stage_classifier': {
        'rice': r"models\rice_model.pt",
        'wheat': r"models\wheat_model.pt",
        'maize': r"models\maize_model.pt",
        'chickpea': r"models\chickpea_model.pt",
        'pigeon_pea': r"models\pigeon_pea_model.pt",
        'beans': r"models\bean_model.pt",
        'lentils': r"models\lentils_model.pt"
    },
    'disease_detection': {
        'rice': r"models\rice_transformer_disease_model.pth",
        'wheat': r"models\wheat_transformer_disease_model.pth",
        'maize': r"models\maize_transformer_disease_model.pth",
        'chickpea': r"models\chickpea_transformer_disease_model.pth",
        'pigeon_pea': r"models\pigeon_pea_transformer_disease_model.pth",
        'beans': r"models\bean_transformer_disease_model.pth",
        'lentils': r"models\lentils_transformer_disease_model.pth"
    },
    'pest_risk': {
        'rice': r"models\rice_transformer_pest_model.pth",
        'wheat': r"models\wheat_transformer_pest_model.pth",
        'maize': r"models\maize_transformer_pest_model.pth",
        'chickpea': r"models\chickpea_transformer_pest_model.pth",
        'pigeon_pea': r"models\pigeon_pea_transformer_pest_model.pth",
        'beans': r"models\bean_transformer_pest_model.pth",
        'lentils': r"models\lentils_transformer_pest_model.pth"
    }
}

# Scaler paths
SCALER_PATHS = {
    'stage_classifier': {
        'rice': r"scalers\rice_scaler.pkl",
        'wheat': r"scalers\wheat_scaler.pkl",
        'maize': r"scalers\maize_scaler.pkl",
        'chickpea': r"scalers\chickpea_scaler.pkl",
        'pigeon_pea': r"scalers\pigeon_pea_scaler.pkl",
        'beans': r"scalers\bean_scaler.pkl",
        'lentils': r"scalers\lentils_scaler.pkl"
    },
    'disease_detection': {
        'rice': r"scalers\rice_scaler.pkl",
        'wheat': r"scalers\wheat_scaler.pkl",
        'maize': r"scalers\maize_scaler.pkl",
        'chickpea': r"scalers\chickpea_scaler.pkl",
        'pigeon_pea': r"scalers\pigeon_pea_scaler.pkl",
        'beans': r"scalers\bean_scaler.pkl",
        'lentils': r"scalers\lentils_scaler.pkl"
    },
    'pest_risk': {
        'rice': r"scalers\rice_scaler.pkl",
        'wheat': r"scalers\wheat_scaler.pkl",
        'maize': r"scalers\maize_scaler.pkl",
        'chickpea': r"scalers\chickpea_scaler.pkl",
        'pigeon_pea': r"scalers\pigeon_pea_scaler.pkl",
        'beans': r"scalers\bean_scaler.pkl",
        'lentils': r"scalers\lentils_scaler.pkl"
    }
}