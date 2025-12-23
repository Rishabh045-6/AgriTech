import os
from datetime import datetime

# Demo configuration
DEMO_CONFIG = {
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
    'demo_date': datetime(2024, 12, 19),  # Fixed date for demo consistency
    'use_mock_data': True  # Set to False to use real Sentinel Hub
}

# Color scheme for Streamlit
COLORS = {
    'primary': '#2E8B57',  # Sea Green
    'secondary': '#3CB371',  # Medium Sea Green
    'accent': '#90EE90',    # Light Green
    'warning': '#FFA500',   # Orange
    'danger': '#FF4500'     # Orange Red
}

# Available crops
CROPS = [
    'rice', 'wheat', 'maize', 'chickpea', 
    'pigeon_pea', 'beans', 'lentils'
]

# Crop stages
STAGES = {
    1: 'Early Stage (Vegetative)',
    2: 'Middle Stage (Reproductive)',
    3: 'Late Stage (Maturity)'
}

# Feature order for models
FEATURE_ORDER = [
    'B2', 'B3', 'B4', 'B5', 'B8', 'B11', 'B12',
    'NDVI', 'GNDVI', 'SAVI', 'NDMI', 'MSI', 'NDWI', 'NMDI',
    'NDRE', 'CIredEdge', 'CIgreen', 'PSRI', 'SIPI'
]