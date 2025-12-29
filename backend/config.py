"""
Configuration for nutrient deficiency analysis with all 7 crops
"""
from datetime import datetime

# Crop configuration with ALL 7 crops
CROP_CONFIG = {
    'rice': {
        'window_size': 8,
        'sowing_start': {'month': 6, 'day': 1},
        'season_end': {'month': 10, 'day': 31},
        'model_path': 'models/rice_model.pt',
        'scaler_path': 'scalers/rice_scaler.pkl',
        'color': '#4CAF50',
        'stage_offsets': {
            'Vegetative': 30,
            'Reproductive': 60,
            'Ripening': 90
        },
        'nutrient_params': {
            'nitrogen_critical': 3,
            'chlorophyll_threshold': 0.65,
            'phosphorus_sensitive': True,
            'potassium_sensitive': True
        }
    },
    'wheat': {
        'window_size': 12,
        'sowing_start': {'month': 11, 'day': 1},
        'season_end': {'month': 4, 'day': 30},
        'model_path': 'models/wheat_model.pt',
        'scaler_path': 'scalers/wheat_scaler.pkl',
        'color': '#FF9800',
        'stage_offsets': {
            'Vegetative': 40,
            'Reproductive': 80,
            'Ripening': 120
        },
        'nutrient_params': {
            'nitrogen_critical': 3,
            'chlorophyll_threshold': 0.60,
            'phosphorus_sensitive': True,
            'potassium_sensitive': False
        }
    },
    'maize': {
        'window_size': 8,
        'sowing_start': {'month': 5, 'day': 15},
        'season_end': {'month': 9, 'day': 30},
        'model_path': 'models/maize_model.pt',
        'scaler_path': 'scalers/maize_scaler.pkl',
        'color': '#2196F3',
        'stage_offsets': {
            'Vegetative': 35,
            'Reproductive': 70,
            'Ripening': 105
        },
        'nutrient_params': {
            'nitrogen_critical': 4,
            'chlorophyll_threshold': 0.70,
            'phosphorus_sensitive': True,
            'potassium_sensitive': True
        }
    },
    'chickpea': {
        'window_size': 7,
        'sowing_start': {'month': 10, 'day': 15},
        'season_end': {'month': 3, 'day': 31},
        'model_path': 'models/chickpea_model.pt',
        'scaler_path': 'scalers/chickpea_scaler.pkl',
        'color': '#9C27B0',
        'stage_offsets': {
            'Vegetative': 30,
            'Reproductive': 60,
            'Ripening': 90
        },
        'nutrient_params': {
            'nitrogen_critical': 2,  # Legumes fix nitrogen
            'chlorophyll_threshold': 0.55,
            'phosphorus_sensitive': True,
            'potassium_sensitive': True
        }
    },
    'pigeon_pea': {
        'window_size': 7,
        'sowing_start': {'month': 6, 'day': 1},
        'season_end': {'month': 12, 'day': 31},
        'model_path': 'models/pigeonpea_model.pt',
        'scaler_path': 'scalers/pigeonpea_scaler.pkl',
        'color': '#795548',
        'stage_offsets': {
            'Vegetative': 45,
            'Reproductive': 90,
            'Ripening': 135
        },
        'nutrient_params': {
            'nitrogen_critical': 2,  # Legumes fix nitrogen
            'chlorophyll_threshold': 0.55,
            'phosphorus_sensitive': True,
            'potassium_sensitive': True
        }
    },
    'beans': {
        'window_size': 6,
        'sowing_start': {'month': 2, 'day': 1},
        'season_end': {'month': 5, 'day': 31},
        'model_path': 'models/beans_model.pt',
        'scaler_path': 'scalers/beans_scaler.pkl',
        'color': '#F44336',
        'stage_offsets': {
            'Vegetative': 25,
            'Reproductive': 50,
            'Ripening': 75
        },
        'nutrient_params': {
            'nitrogen_critical': 2,  # Legumes fix nitrogen
            'chlorophyll_threshold': 0.60,
            'phosphorus_sensitive': True,
            'potassium_sensitive': True
        }
    },
    'lentils': {
        'window_size': 7,
        'sowing_start': {'month': 10, 'day': 1},
        'season_end': {'month': 3, 'day': 31},
        'model_path': 'models/lentils_model.pt',
        'scaler_path': 'scalers/lentils_scaler.pkl',
        'color': '#00BCD4',
        'stage_offsets': {
            'Vegetative': 30,
            'Reproductive': 60,
            'Ripening': 90
        },
        'nutrient_params': {
            'nitrogen_critical': 2,  # Legumes fix nitrogen
            'chlorophyll_threshold': 0.55,
            'phosphorus_sensitive': True,
            'potassium_sensitive': True
        }
    }
}

# Sentinel Hub clients
CLIENTS = [
    ("c30e60ba-ea66-4447-a1e8-af3207786289", "EPfJJYksVRwotM0yX8qTJukW0GKAUAn6"),
    ("243d120c-aa15-4329-9365-7c970799d3ee", "uXC8gl25RML4ZILOuYCYlrHl7svleRcK"),
    ("036ec31e-54ee-4347-9267-199f5480fb3f", "ETUSehSpkGZUqjBixrjz8J3VN51gsw4S"),
    ("9bbe62fb-7b30-47d8-b903-ae6b075d9349", "VIlm7ofRmIPTvClNtCQ5KXWLOYLqymL3"),
    ("9ee87d64-a7df-4641-a4c5-df30f15b74a2", "UG3ic3LN454SB79EQA43b1i1D6O9RzXD"),
    ("26a07095-ca66-4a18-8890-25cdbdea4542", "cFdacSjQrVj6m0DdOtKgpSKDic26Nb0Z"),
]

# Feature indices mapping
FEATURE_MAPPING = {
    'B2': 0, 'B3': 1, 'B4': 2, 'B5': 3, 'B8': 4, 'B11': 5, 'B12': 6,
    'NDVI': 7, 'GNDVI': 8, 'SAVI': 9, 'NDMI': 10, 'MSI': 11, 'NDWI': 12, 'NMDI': 13,
    'NDRE': 14, 'CIredEdge': 15, 'CIgreen': 16, 'PSRI': 17, 'SIPI': 18
}

# Nutrient thresholds by stage
NUTRIENT_THRESHOLDS = {
    'Vegetative': {
        'NITROGEN_CRITICAL': 3,
        'CHLOROPHYLL_LOW': 0.5,
        'GENERAL_STRESS': 3
    },
    'Reproductive': {
        'NITROGEN_CRITICAL': 4,
        'CHLOROPHYLL_LOW': 0.6,
        'GENERAL_STRESS': 4
    },
    'Ripening': {
        'NITROGEN_CRITICAL': 2,
        'CHLOROPHYLL_LOW': 0.4,
        'GENERAL_STRESS': 2
    }
}

# Add these constants to your existing config.py if not already present
STRESS_WEIGHTS = {
    'NDMI': 0.35,
    'NDWI': 0.25,
    'MSI': 0.25,
    'NMDI': 0.15
}

THRESHOLDS = {
    'NDMI_LOW': 0.2,
    'NDWI_LOW': 0.1,
    'MSI_HIGH': 1.2,
    'NMDI_LOW': 0.1,
    'OPTIMAL': 25,
    'MILD': 45,
    'MODERATE': 65,
    'SEVERE': 100
}

STATUS_COLORS = {
    'Optimal': '#4CAF50',
    'Mild Stress': '#FFC107',
    'Moderate Stress': '#FF9800',
    'Severe Stress': '#F44336'
}

# Deficiency colors
DEFICIENCY_COLORS = {
    'Critical': '#FF5252',
    'High': '#FF9800',
    'Moderate': '#FFB74D',
    'Low': '#4CAF50',
    'Optimal': '#4CAF50',
    'Adequate': '#4CAF50',
    'Unlikely': '#4CAF50',
    'Insufficient data': '#9E9E9E'
}

# Stage names
STAGE_NAMES = ["Vegetative", "Reproductive", "Ripening"]

# Default coordinates
DEFAULT_COORDS = [
    (75.5, 30.5),
    (75.5, 30.6),
    (75.6, 30.6),
    (75.6, 30.5),
    (75.5, 30.5)
]

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
}"""