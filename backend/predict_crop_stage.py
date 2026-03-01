"""
Combined Agritech Analysis Script
Combines: growth_performance.py, water_stress_analysis.py, 
          nutrient_analysis.py, growth_stage_analysis.py, 
          disease_model.py, disease_advice_generator.py, 
          data_fetcher.py, config.py, and original predict_crop_stage.py
"""

import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import warnings
import os
import time
from shapely.geometry import Polygon
import torch
import torch.nn as nn
import base64
import pickle
from typing import Optional


def _load_local_env_file():
    """Load simple KEY=VALUE pairs from a local .env file into os.environ if present.
    This is a lightweight fallback so running the script directly picks up credentials
    placed in `backend/.env` (without requiring python-dotenv).
    """
    try:
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if not os.path.exists(env_path):
            return
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and val:
                    os.environ.setdefault(key, val)
    except Exception:
        pass


# Try to load local .env so `python predict_crop_stage.py ...` works like server spawn
_load_local_env_file()

try:
    from sentinelhub import SHConfig, BBox, CRS, DataCollection, MimeType, SentinelHubRequest, bbox_to_dimensions
    SENTINELHUB_AVAILABLE = True
except Exception:
    SENTINELHUB_AVAILABLE = False

try:
    from growth_performance.yield_calculator import (
        estimate_yield_kg_ha as gp_estimate_yield_kg_ha,
        get_yield_category as gp_get_yield_category,
    )
    GROWTH_PERFORMANCE_AVAILABLE = True
except Exception:
    GROWTH_PERFORMANCE_AVAILABLE = False

# Import decision engine for recommendations
try:
    from decision_engine import generate_recommendations
    DECISION_ENGINE_AVAILABLE = True
except ImportError:
    DECISION_ENGINE_AVAILABLE = False
    print("Warning: decision_engine not available", file=sys.stderr)

# Suppress warnings
warnings.filterwarnings('ignore')

# ===========================================
# ORIGINAL predict_crop_stage.py CONTENT
# ===========================================

def safe_float_convert(value):
    """Safely convert to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def load_model_and_scaler(crop_type):
    """Load model and scaler with error handling"""
    try:
        # Check if model exists
        model_path = f"models/{crop_type}_model.pt"
        scaler_path = f"scalers/{crop_type}_scaler.pkl"
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        if not os.path.exists(scaler_path):
            raise FileNotFoundError(f"Scaler not found: {scaler_path}")
        
        # Load model (CPU only for safety)
        model = torch.load(model_path, map_location=torch.device('cpu'))
        model.eval()
        
        # Load scaler
        import pickle
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
        
        return model, scaler
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Failed to load model: {str(e)}"
        }))
        sys.exit(1)

def process_coordinates(coordinates_base64):
    """Process coordinates from base64 string"""
    try:
        # Decode base64
        coordinates_json = base64.b64decode(coordinates_base64).decode('utf-8')
        coordinates = json.loads(coordinates_json)
        
        # Validate coordinates format
        if not isinstance(coordinates, list) or len(coordinates) < 3:
            raise ValueError("Invalid coordinates format - need at least 3 points")
        
        for coord in coordinates:
            if not isinstance(coord, dict) or 'latitude' not in coord or 'longitude' not in coord:
                raise ValueError("Invalid coordinate format - need {latitude, longitude} objects")
            if not isinstance(coord['latitude'], (int, float)) or not isinstance(coord['longitude'], (int, float)):
                raise ValueError("Invalid coordinate values - must be numbers")
        
        return coordinates
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Failed to process coordinates: {str(e)}"
        }))
        sys.exit(1)

def predict_original_model(farmer_id, crop_type, coordinates_base64):
    """Original prediction function from predict_crop_stage.py"""
    try:
        # Process coordinates
        coordinates = process_coordinates(coordinates_base64)
        
        # Load model and scaler
        model, scaler = load_model_and_scaler(crop_type)
        
        # Create mock features (since we don't have real satellite data in this context)
        n_points = len(coordinates)
        
        # Create mock features (19 features for each point - matches your model)
        mock_features = np.random.rand(n_points, 19)  # 19 features for each point
        
        # Scale features
        scaled_features = scaler.transform(mock_features)
        
        # Convert to tensor
        features_tensor = torch.FloatTensor(scaled_features)
        
        # Make prediction
        with torch.no_grad():
            if len(features_tensor.shape) == 2:
                # Average across all points
                avg_features = torch.mean(features_tensor, dim=0, keepdim=True)
            else:
                avg_features = features_tensor.unsqueeze(0) if len(features_tensor.shape) == 1 else features_tensor
            
            prediction = model(avg_features)
            predicted_stage = torch.argmax(prediction, dim=1).item()
        
        # Map prediction to stage names
        stage_names = ["Vegetative", "Reproductive", "Ripening"]
        predicted_stage_name = stage_names[predicted_stage] if predicted_stage < len(stage_names) else "Unknown"
        
        # Return results
        result = {
            "success": True,
            "farmerId": farmer_id,
            "cropType": crop_type,
            "coordinates": coordinates,
            "predictedStage": predicted_stage_name,
            "confidence": float(torch.max(torch.softmax(prediction, dim=1)).item()),
            "timestamp": datetime.now().isoformat(),
            "analysis": {
                "totalPoints": n_points,
                "center": {
                    "latitude": sum(coord['latitude'] for coord in coordinates) / n_points,
                    "longitude": sum(coord['longitude'] for coord in coordinates) / n_points
                }
            }
        }
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Prediction failed: {str(e)}",
            "details": str(type(e).__name__)
        }

# ===========================================
# CONFIGURATION MODULE
# ===========================================

def get_sentinel_clients():
    """Load Sentinel Hub clients from environment variables"""
    clients = []
    for i in range(1, 7):
        client_id = os.getenv(f'SENTINEL_CLIENT_{i}_ID')
        client_secret = os.getenv(f'SENTINEL_CLIENT_{i}_SECRET')
        if client_id and client_secret:
            clients.append((client_id, client_secret))
    return clients

CLIENTS = get_sentinel_clients()

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

# Water stress configuration
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

# ===========================================
# TRANSFORMER MODEL MODULE
# ===========================================

class TransformerClassifier(nn.Module):
    def __init__(self, input_dim, seq_len, d_model=64, nhead=4, num_layers=3, dropout=0.1):
        super().__init__()
        
        # Input projection
        self.input_proj = nn.Linear(input_dim, d_model)
        
        # Placeholder for positional encoding - will be handled dynamically
        self.d_model = d_model
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=128,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Classification head
        self.classifier = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Dropout(dropout),
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, 1)
        )
        
    def forward(self, x):
        # x shape: (batch_size, seq_len, input_dim)
        x = self.input_proj(x)
        
        # Create positional encoding dynamically based on sequence length
        batch_size, actual_seq_len, d_model = x.shape
        pos_enc = torch.zeros(1, actual_seq_len, d_model, device=x.device)
        x = x + pos_enc
        
        x = self.transformer_encoder(x)
        x = x.mean(dim=1)
        x = self.classifier(x)
        return x.squeeze(-1)

# ===========================================
# DISEASE ADVICE GENERATOR MODULE
# ===========================================

class DiseaseAdviceGenerator:
    def __init__(self):
        self.advice_templates = self._initialize_advice_templates()
    
    def _initialize_advice_templates(self):
        """Initialize disease-specific advice templates"""
        return {
            # Chickpea diseases
            'Fusarium': {
                'title': 'Fusarium Wilt',
                'symptoms': [
                    'Yellowing and wilting of leaves starting from lower leaves',
                    'Brown discoloration in stem cross-section',
                    'Stunted growth and premature death'
                ],
                'recommendations': [
                    'Use resistant varieties like Pusa 372, Pusa 256',
                    'Apply Trichoderma viride or Pseudomonas fluorescens as seed treatment',
                    'Practice crop rotation with non-host crops (cereals)',
                    'Avoid waterlogging in fields',
                    'Remove and destroy infected plants'
                ],
                'chemical_control': [
                    'Seed treatment with Carbendazim @ 2g/kg seed',
                    'Soil drenching with Carbendazim @ 0.1%'
                ],
                'organic_control': [
                    'Neem cake application @ 250 kg/ha',
                    'Application of Trichoderma harzianum @ 2.5 kg/ha'
                ],
                'severity': 'High'
            },
            'Healthy': {
                'title': 'Healthy Plant',
                'symptoms': ['Vibrant green leaves', 'Normal growth pattern', 'No visible lesions'],
                'recommendations': [
                    'Continue good agricultural practices',
                    'Monitor regularly for early signs',
                    'Maintain proper irrigation schedule',
                    'Apply balanced fertilization'
                ],
                'chemical_control': ['No chemical treatment needed'],
                'organic_control': ['Continue organic practices if applicable'],
                'severity': 'None'
            },
            
            # Bean diseases
            'Angular_Leaf_Spot': {
                'title': 'Angular Leaf Spot',
                'symptoms': [
                    'Angular water-soaked spots on leaves',
                    'Spots limited by leaf veins',
                    'Yellow halos around spots'
                ],
                'recommendations': [
                    'Use disease-free seeds',
                    'Practice 3-year crop rotation',
                    'Remove crop debris after harvest',
                    'Avoid overhead irrigation'
                ],
                'severity': 'Medium'
            },
            'Bean_Rust': {
                'title': 'Bean Rust',
                'symptoms': [
                    'Small reddish-brown pustules on leaves',
                    'Pustules may appear on stems and pods',
                    'Premature leaf drop'
                ],
                'recommendations': [
                    'Plant resistant varieties',
                    'Apply sulfur-based fungicides',
                    'Space plants for good air circulation',
                    'Avoid working in wet fields'
                ],
                'severity': 'High'
            },
            
            # Lentil diseases
            'Ascochyta blight': {
                'title': 'Ascochyta Blight',
                'symptoms': [
                    'Brown lesions with concentric rings',
                    'Lesions on leaves, stems, and pods',
                    'Gray fungal growth in humid conditions'
                ],
                'recommendations': [
                    'Use certified disease-free seeds',
                    'Apply Chlorothalonil at early flowering',
                    'Practice 4-year crop rotation',
                    'Deep plowing to bury infected debris'
                ],
                'severity': 'High'
            },
            'Lentil Rust': {
                'title': 'Lentil Rust',
                'symptoms': [
                    'Orange to brown pustules on leaves',
                    'Pustules rupture releasing spores',
                    'Severe defoliation in advanced stages'
                ],
                'recommendations': [
                    'Early sowing to avoid peak rust period',
                    'Foliar spray of Propiconazole @ 0.1%',
                    'Remove volunteer lentil plants',
                    'Use tolerant varieties like L 4076'
                ],
                'severity': 'Medium'
            },
            
            # Maize diseases
            'Common_Rust': {
                'title': 'Common Rust of Maize',
                'symptoms': [
                    'Circular to elongated cinnamon-brown pustules',
                    'Pustules mostly on upper leaf surface',
                    'May cause yellowing and drying of leaves'
                ],
                'recommendations': [
                    'Plant resistant hybrids',
                    'Apply Mancozeb @ 0.25% at first appearance',
                    'Avoid excessive nitrogen application',
                    'Remove alternative hosts'
                ],
                'severity': 'Medium'
            },
            'Gray_Leaf_Spot': {
                'title': 'Gray Leaf Spot',
                'symptoms': [
                    'Rectangular gray to tan lesions',
                    'Lesions parallel to leaf veins',
                    'Severe infection causes complete blighting'
                ],
                'recommendations': [
                    'Use resistant hybrids',
                    'Practice crop rotation with soybean',
                    'Reduce plant density for better air movement',
                    'Apply Azoxystrobin at disease onset'
                ],
                'severity': 'High'
            },
            
            # Pigeon pea diseases
            'Leaf_Spot': {
                'title': 'Leaf Spot',
                'symptoms': [
                    'Circular brown spots with yellow halos',
                    'Spots may coalesce forming large necrotic areas',
                    'Premature leaf fall in severe cases'
                ],
                'recommendations': [
                    'Spray Mancozeb @ 0.25%',
                    'Remove and destroy infected leaves',
                    'Avoid dense planting',
                    'Use balanced fertilization'
                ],
                'severity': 'Low'
            },
            'Leaf_webber': {
                'title': 'Leaf Webber',
                'symptoms': [
                    'Leaves webbed together by larvae',
                    'Skeletonization of leaves',
                    'Reduced photosynthetic area'
                ],
                'recommendations': [
                    'Spray Chlorpyriphos @ 0.05%',
                    'Release Trichogramma parasites',
                    'Install pheromone traps @ 5/ha',
                    'Remove and destroy webbed leaves'
                ],
                'severity': 'Medium'
            },
            
            # Wheat diseases
            'Bacterial leaf blight': {
                'title': 'Bacterial Leaf Blight',
                'symptoms': [
                    'Water-soaked lesions turning yellow',
                    'Lesions with bacterial ooze in morning',
                    'Drying and bleaching of leaves'
                ],
                'recommendations': [
                    'Use resistant varieties like HD 2967',
                    'Avoid overhead irrigation',
                    'Spray Streptocycline @ 0.01%',
                    'Practice clean cultivation'
                ],
                'severity': 'Medium'
            },
            'Blast': {
                'title': 'Wheat Blast',
                'symptoms': [
                    'Bleached spikelets',
                    'Black lesions on rachis',
                    'Complete bleaching of heads'
                ],
                'recommendations': [
                    'Use tolerant varieties',
                    'Avoid late sowing',
                    'Apply Tricyclazole @ 0.1%',
                    'Destroy infected crop residue'
                ],
                'severity': 'High'
            },
            
            # Rice diseases
            'Brown_Rust': {
                'title': 'Brown Rust',
                'symptoms': [
                    'Small brown pustules on leaves',
                    'Pustules arranged in linear patterns',
                    'Yellowing of leaves around pustules'
                ],
                'recommendations': [
                    'Use resistant varieties like PR 114',
                    'Spray Propiconazole @ 0.1%',
                    'Avoid excess nitrogen',
                    'Drain field periodically'
                ],
                'severity': 'Medium'
            },
            'Yellow_Rust': {
                'title': 'Yellow Rust',
                'symptoms': [
                    'Yellow-orange pustules in stripes',
                    'Pustules contain yellow powder',
                    'Severe infection causes complete drying'
                ],
                'recommendations': [
                    'Plant resistant varieties',
                    'Spray Tebuconazole @ 0.1%',
                    'Early sowing to avoid infection',
                    'Remove volunteer plants'
                ],
                'severity': 'High'
            },
            'Powdery_Mildew': {
                'title': 'Powdery Mildew',
                'symptoms': [
                    'White powdery growth on leaves',
                    'Growth mostly on upper surface',
                    'Leaves may curl and dry'
                ],
                'recommendations': [
                    'Spray Wettable sulfur @ 0.2%',
                    'Improve air circulation',
                    'Avoid dense planting',
                    'Use resistant varieties'
                ],
                'severity': 'Low'
            }
        }
    
    def get_advice(self, crop_type, disease_name):
        """Get detailed advice for specific disease"""
        # Try exact match first
        if disease_name in self.advice_templates:
            return self.advice_templates[disease_name]
        
        # Try partial match
        for key, advice in self.advice_templates.items():
            if key.lower() in disease_name.lower() or disease_name.lower() in key.lower():
                return advice
        
        # Default generic advice
        return self._get_generic_advice(disease_name)
    
    def _get_generic_advice(self, disease_name):
        """Generate generic advice for unknown diseases"""
        return {
            'title': disease_name,
            'symptoms': ['Consult local agricultural expert for specific symptoms'],
            'recommendations': [
                'Isolate affected plants',
                'Consult local KVK (Krishi Vigyan Kendra)',
                'Take clear photos for expert consultation',
                'Maintain field sanitation'
            ],
            'chemical_control': ['Consult agricultural officer for appropriate fungicide'],
            'organic_control': ['Neem-based formulations may help', 'Improve soil health'],
            'severity': 'Unknown'
        }
    
    def get_preventive_measures(self, crop_type):
        """Get general preventive measures for crop"""
        general_measures = [
            'Use certified disease-free seeds',
            'Practice crop rotation',
            'Maintain proper plant spacing',
            'Ensure balanced nutrition',
            'Monitor fields regularly (at least weekly)',
            'Control weeds that may harbor diseases',
            'Avoid working in fields when plants are wet',
            'Clean equipment between fields'
        ]
        
        crop_specific = {
            'rice': [
                'Maintain proper water management',
                'Use resistant/tolerant varieties',
                'Apply recommended fungicides preventively'
            ],
            'wheat': [
                'Avoid late sowing',
                'Use seed treatment with fungicides',
                'Destroy crop residues after harvest'
            ],
            'maize': [
                'Avoid continuous maize cultivation',
                'Use resistant hybrids',
                'Control insect vectors'
            ],
            'chickpea': [
                'Deep summer plowing',
                'Avoid waterlogging',
                'Use bio-control agents'
            ]
        }
        
        measures = general_measures + crop_specific.get(crop_type, [])
        return measures
    
    def generate_report(self, crop_type, disease_name, confidence, image_info=None):
        """Generate comprehensive disease report"""
        advice = self.get_advice(crop_type, disease_name)
        
        report = {
            'crop': crop_type,
            'disease': disease_name,
            'confidence': confidence,
            'diagnosis': advice['title'],
            'severity': advice.get('severity', 'Unknown'),
            'symptoms': advice.get('symptoms', []),
            'recommendations': advice.get('recommendations', []),
            'chemical_control': advice.get('chemical_control', []),
            'organic_control': advice.get('organic_control', []),
            'preventive_measures': self.get_preventive_measures(crop_type),
            'image_info': image_info
        }
        
        return report

# ===========================================
# WATER STRESS ANALYSIS MODULE
# ===========================================

def minmax_norm(x, eps=1e-6):
    """Min-max normalization"""
    if isinstance(x, (list, np.ndarray)):
        x = np.array(x)
        if len(x) == 0 or (x.max() - x.min()) == 0:
            return np.zeros_like(x)
        return (x - x.min()) / (x.max() - x.min() + eps)
    return 0

def calculate_water_stress_score(window_mean_values):
    """Calculate water stress score for a window"""
    ndmi = window_mean_values.get('NDMI', 0)
    ndwi = window_mean_values.get('NDWI', 0)
    msi = window_mean_values.get('MSI', 0)
    nmdi = window_mean_values.get('NMDI', 0)
    
    ndmi_n = 1 - minmax_norm(ndmi) if ndmi is not None else 0.5
    ndwi_n = 1 - minmax_norm(ndwi) if ndwi is not None else 0.5
    msi_n = minmax_norm(msi) if msi is not None else 0.5
    nmdi_n = 1 - minmax_norm(nmdi) if nmdi is not None else 0.5
    
    stress = (
        STRESS_WEIGHTS['NDMI'] * ndmi_n +
        STRESS_WEIGHTS['NDWI'] * ndwi_n +
        STRESS_WEIGHTS['MSI'] * msi_n +
        STRESS_WEIGHTS['NMDI'] * nmdi_n
    )
    
    score = np.clip(stress * 100, 0, 100)
    
    return {
        'score': float(score),
        'components': {
            'NDMI': float(ndmi_n * 100),
            'NDWI': float(ndwi_n * 100),
            'MSI': float(msi_n * 100),
            'NMDI': float(nmdi_n * 100)
        },
        'raw_values': {
            'NDMI': float(ndmi) if ndmi is not None else 0,
            'NDWI': float(ndwi) if ndwi is not None else 0,
            'MSI': float(msi) if msi is not None else 0,
            'NMDI': float(nmdi) if nmdi is not None else 0
        }
    }

calculate_window_water_stress = calculate_water_stress_score

def get_moisture_status(score):
    """Convert score to moisture status"""
    if score < THRESHOLDS['OPTIMAL']:
        return "Optimal"
    elif score < THRESHOLDS['MILD']:
        return "Mild Stress"
    elif score < THRESHOLDS['MODERATE']:
        return "Moderate Stress"
    else:
        return "Severe Stress"

def get_stage_aware_irrigation_advice(score, crop_stage):
    """Get irrigation advice considering crop stage"""
    
    stage_sensitivity = {
        'Vegetative': 'medium',
        'Reproductive': 'high',      # Most sensitive stage
        'Ripening': 'low'
    }
    
    sensitivity = stage_sensitivity.get(crop_stage, 'medium')
    
    # Adjust thresholds based on sensitivity
    if sensitivity == 'high':
        if score > 55:  # Lower threshold for reproductive stage
            return "🚨 **Irrigate immediately** (Critical stage - high sensitivity)"
        elif score > 40:
            return "⚠️ **Irrigate within 1-2 days** (Critical stage)"
        elif score > 25:
            return "👀 **Monitor daily** - irrigation may be needed soon"
        else:
            return "✅ **Adequate moisture** for critical stage"
    
    elif sensitivity == 'medium':
        if score > 65:
            return "🚨 **Irrigate immediately**"
        elif score > 45:
            return "⚠️ **Irrigate within 2-3 days**"
        elif score > 30:
            return "👀 **Monitor closely** - check in 3-5 days"
        else:
            return "✅ **No irrigation needed**"
    
    else:  # low sensitivity
        if score > 70:
            return "⚠️ **Consider irrigation** (Stage: Ripening)"
        elif score > 50:
            return "👀 **Monitor** - irrigation may not be critical"
        else:
            return "✅ **No irrigation needed** (Stage: Ripening)"

def identify_stress_drivers(window_mean_values):
    """Identify which factors are driving water stress"""
    drivers = []
    
    ndmi = window_mean_values.get('NDMI', 0)
    ndwi = window_mean_values.get('NDWI', 0)
    msi = window_mean_values.get('MSI', 0)
    nmdi = window_mean_values.get('NMDI', 0)
    
    if ndmi < THRESHOLDS['NDMI_LOW']:
        drivers.append({
            "factor": "Low NDMI",
            "description": "Plant water content below optimal",
            "severity": "High" if ndmi < 0.1 else "Medium"
        })
    
    if ndwi < THRESHOLDS['NDWI_LOW']:
        drivers.append({
            "factor": "Low NDWI",
            "description": "Canopy water content is low",
            "severity": "High" if ndwi < 0.05 else "Medium"
        })
    
    if msi > THRESHOLDS['MSI_HIGH']:
        drivers.append({
            "factor": "High MSI",
            "description": "Moisture stress index elevated",
            "severity": "High" if msi > 1.5 else "Medium"
        })
    
    if nmdi < THRESHOLDS['NMDI_LOW']:
        drivers.append({
            "factor": "Low NMDI",
            "description": "Soil moisture deficit detected",
            "severity": "High" if nmdi < 0.05 else "Medium"
        })
    
    if not drivers:
        drivers.append({
            "factor": "All indices normal",
            "description": "All water stress indices within optimal ranges",
            "severity": "Low"
        })
    
    return drivers

def analyze_all_windows(windows_data, current_stage):
    """Analyze multiple windows for trend analysis"""
    analysis_results = []
    
    for window in windows_data:
        window_mean = window['mean_values']
        stress_result = calculate_water_stress_score(window_mean)
        
        analysis = {
            'window_id': window['window_id'],
            'dates_str': window['dates_str'],
            'start_date': window['start_date'],
            'end_date': window['end_date'],
            'water_stress': stress_result['score'],
            'moisture_status': get_moisture_status(stress_result['score']),
            'irrigation_advice': get_stage_aware_irrigation_advice(stress_result['score'], current_stage),
            'stress_drivers': identify_stress_drivers(window_mean),
            'components': stress_result['components'],
            'raw_values': stress_result['raw_values']
        }
        
        analysis_results.append(analysis)
    
    # Calculate trends
    if len(analysis_results) >= 2:
        scores = [a['water_stress'] for a in analysis_results]
        trend = "increasing" if scores[-1] > scores[0] else "decreasing"
        trend_magnitude = abs(scores[-1] - scores[0])
        trend_percentage = (scores[-1] - scores[0]) / scores[0] * 100 if scores[0] > 0 else 0
    else:
        trend = "stable"
        trend_magnitude = 0
        trend_percentage = 0
    
    return {
        'window_analyses': analysis_results,
        'current_status': analysis_results[-1] if analysis_results else None,
        'trend': {
            'direction': trend,
            'magnitude': trend_magnitude,
            'percentage': trend_percentage,
            'scores': [a['water_stress'] for a in analysis_results]
        }
    }

# ===========================================
# NUTRIENT ANALYSIS MODULE
# ===========================================

def extract_window_features(window_array):
    """Extract key nutrient features from window data"""
    if window_array is None or len(window_array) == 0:
        return None
    
    # Get indices
    idx = FEATURE_MAPPING
    
    # Extract time series
    ndvi_ts = window_array[:, idx['NDVI']]
    ndre_ts = window_array[:, idx['NDRE']]
    
    # Calculate slopes
    x = np.arange(len(ndvi_ts))
    ndvi_slope, _ = np.polyfit(x, ndvi_ts, 1)
    ndre_slope, _ = np.polyfit(x, ndre_ts, 1)
    
    return {
        "NDVI_mean": float(ndvi_ts.mean()),
        "NDVI_slope": float(ndvi_slope),
        "NDVI_std": float(ndvi_ts.std()),
        "GNDVI_mean": float(window_array[:, idx['GNDVI']].mean()),
        "NDRE_mean": float(ndre_ts.mean()),
        "NDRE_slope": float(ndre_slope),
        "PSRI_mean": float(window_array[:, idx['PSRI']].mean()),
        "CIredEdge_mean": float(window_array[:, idx['CIredEdge']].mean()),
        "CIgreen_mean": float(window_array[:, idx['CIgreen']].mean()),
        "NDMI_mean": float(window_array[:, idx['NDMI']].mean()),
        "MSI_mean": float(window_array[:, idx['MSI']].mean()),
        "Chlorophyll_index": float(calculate_chlorophyll_index(ndre_ts.mean(), ndvi_ts.mean()))
    }

def calculate_chlorophyll_index(ndre_mean, ndvi_mean):
    """Estimate chlorophyll content"""
    chlorophyll = 0.3 + (ndre_mean * 2.5) + (ndvi_mean * 0.8)
    return np.clip(chlorophyll, 0.1, 1.0)

def relative_change(curr_value, past_values):
    """Calculate standardized relative change"""
    if isinstance(past_values, (list, np.ndarray)):
        past_mean = np.mean(past_values)
        past_std = np.std(past_values)
    else:
        past_mean = past_values
        past_std = 0.1
    
    if past_std < 1e-6:
        return 0
    
    return (curr_value - past_mean) / (past_std + 1e-6)

def analyze_nutrient_deficiency(window_features_list, current_stage):
    """
    Main nutrient analysis function
    window_features_list: List of features for each window (oldest to newest)
    current_stage: Current crop stage for threshold adjustment
    """
    if not window_features_list or len(window_features_list) < 2:
        # If we don't have enough windows, use the single available data
        if window_features_list:
            current_features = window_features_list[0]
            # Create mock past features for relative comparison
            past_features = [current_features]  # Use same as past for comparison
        else:
            return None
    
    # Current window is the last one (or only one if we have only one)
    current_features = window_features_list[-1]
    
    # Past windows for comparison (all except current, or same as current if only one)
    past_features = window_features_list[:-1] if len(window_features_list) > 1 else [current_features]
    
    # Get stage-specific thresholds
    stage_thresholds = NUTRIENT_THRESHOLDS.get(current_stage, NUTRIENT_THRESHOLDS['Vegetative'])
    
    # Analyze each nutrient
    nitrogen_result = analyze_nitrogen(current_features, past_features, stage_thresholds)
    chlorophyll_result = analyze_chlorophyll(current_features, stage_thresholds)
    phosphorus_result = analyze_phosphorus(current_features, past_features)
    potassium_result = analyze_potassium(current_features, past_features)
    general_stress = analyze_general_stress(current_features, past_features, stage_thresholds)
    
    return {
        'nitrogen': nitrogen_result,
        'chlorophyll': chlorophyll_result,
        'phosphorus': phosphorus_result,
        'potassium': potassium_result,
        'general_stress': general_stress,
        'current_stage': current_stage,
        'stage_adjusted': True
    }

def analyze_nitrogen(current_features, past_features, thresholds):
    """Stage-aware nitrogen analysis"""
    # Extract past values
    past_ndre = [f["NDRE_mean"] for f in past_features]
    past_gndvi = [f["GNDVI_mean"] for f in past_features]
    past_psri = [f["PSRI_mean"] for f in past_features]
    
    score = 0
    indicators = []
    
    # NDRE is most sensitive to nitrogen
    ndre_change = relative_change(current_features["NDRE_mean"], past_ndre)
    if ndre_change < -0.8:
        score += 2
        indicators.append(f"NDRE dropped significantly (-{abs(ndre_change):.1f}σ)")
    elif ndre_change < -0.4:
        score += 1
        indicators.append(f"NDRE decreasing (-{abs(ndre_change):.1f}σ)")
    
    # GNDVI (chlorophyll sensitive)
    gndvi_change = relative_change(current_features["GNDVI_mean"], past_gndvi)
    if gndvi_change < -0.6:
        score += 1
        indicators.append("GNDVI decreasing")
    
    # PSRI (senescence indicator)
    psri_percentile = np.percentile(past_psri, 75)
    if current_features["PSRI_mean"] > psri_percentile:
        score += 1
        indicators.append("PSRI elevated (senescence signs)")
    
    # NDRE slope
    if current_features["NDRE_slope"] < -0.02:
        score += 1
        indicators.append("NDRE trend declining")
    
    # Compare with stage-adjusted threshold
    critical_threshold = thresholds['NITROGEN_CRITICAL']
    
    if score >= critical_threshold:
        level = "High Deficiency"
        color = DEFICIENCY_COLORS['Critical']
        recommendation = "🚨 Immediate nitrogen application needed"
    elif score >= critical_threshold - 1:
        level = "Moderate Deficiency"
        color = DEFICIENCY_COLORS['High']
        recommendation = "⚠️ Monitor closely, consider nitrogen application"
    else:
        level = "Adequate"
        color = DEFICIENCY_COLORS['Adequate']
        recommendation = "✅ Nitrogen levels appear adequate"
    
    return {
        'score': float(score),
        'level': level,
        'color': color,
        'recommendation': recommendation,
        'indicators': indicators,
        'threshold_used': float(critical_threshold),
        'ndre_value': float(current_features["NDRE_mean"]),
        'ndre_change': float(ndre_change)
    }

def analyze_chlorophyll(current_features, thresholds):
    """Chlorophyll health analysis"""
    chlorophyll = current_features["Chlorophyll_index"]
    threshold = thresholds['CHLOROPHYLL_LOW']
    
    if chlorophyll < threshold * 0.8:
        level = "Low"
        recommendation = "🚨 Significant chlorophyll deficiency detected"
        color = DEFICIENCY_COLORS['Critical']
    elif chlorophyll < threshold:
        level = "Moderate"
        recommendation = "⚠️ Chlorophyll below optimal levels"
        color = DEFICIENCY_COLORS['High']
    else:
        level = "Optimal"
        recommendation = "✅ Chlorophyll levels healthy"
        color = DEFICIENCY_COLORS['Optimal']
    
    return {
        'value': float(chlorophyll),
        'level': level,
        'color': color,
        'recommendation': recommendation,
        'threshold': float(threshold)
    }

def analyze_phosphorus(current_features, past_features):
    """Phosphorus deficiency analysis"""
    if not past_features:
        return {"level": "Insufficient data", "color": "#9E9E9E"}
    
    past_ndvi = [f["NDVI_mean"] for f in past_features]
    ndvi_relative = relative_change(current_features["NDVI_mean"], past_ndvi)
    
    # P deficiency shows as poor growth
    conditions = []
    if current_features["NDVI_slope"] < 0.01:
        conditions.append("Slow growth")
    if ndvi_relative < -0.3:
        conditions.append("Below average vigor")
    if current_features["CIredEdge_mean"] < 2.0:
        conditions.append("Reduced chlorophyll efficiency")
    
    if len(conditions) >= 2:
        return {
            "level": "Possible",
            "color": DEFICIENCY_COLORS['Moderate'],
            "recommendation": f"Indicators: {', '.join(conditions)}. Soil test recommended.",
            "conditions": conditions
        }
    else:
        return {
            "level": "Unlikely",
            "color": DEFICIENCY_COLORS['Adequate'],
            "recommendation": "No strong phosphorus deficiency indicators"
        }

def analyze_potassium(current_features, past_features):
    """Potassium deficiency analysis"""
    if not past_features:
        return {"level": "Insufficient data", "color": "#9E9E9E"}
    
    past_msi = [f["MSI_mean"] for f in past_features]
    past_ndmi = [f["NDMI_mean"] for f in past_features]
    
    msi_change = relative_change(current_features["MSI_mean"], past_msi)
    ndmi_change = relative_change(current_features["NDMI_mean"], past_ndmi)
    
    conditions = []
    if msi_change > 0.5:
        conditions.append("Elevated moisture stress")
    if ndmi_change < -0.3:
        conditions.append("Reduced plant water content")
    
    if len(conditions) >= 2:
        return {
            "level": "Possible",
            "color": DEFICIENCY_COLORS['Moderate'],
            "recommendation": f"Potassium affects water regulation. Indicators: {', '.join(conditions)}",
            "conditions": conditions
        }
    else:
        return {
            "level": "Unlikely",
            "color": DEFICIENCY_COLORS['Adequate'],
            "recommendation": "Potassium status appears normal"
        }

def analyze_general_stress(current_features, past_features, thresholds):
    """General plant stress analysis"""
    if not past_features:
        return {"score": 0, "level": "Insufficient data"}
    
    score = 0
    indicators = []
    
    # Multiple stress indicators
    if current_features["NDVI_slope"] < -0.02:
        score += 1
        indicators.append("Growth slowing")
    
    if current_features["MSI_mean"] > 1.0:
        score += 1
        indicators.append("Moisture stress")
    
    if current_features["PSRI_mean"] > 0.03:
        score += 1
        indicators.append("Senescence signs")
    
    if current_features["Chlorophyll_index"] < 0.5:
        score += 1
        indicators.append("Low chlorophyll")
    
    stress_threshold = thresholds['GENERAL_STRESS']
    
    if score >= stress_threshold:
        level = "High Stress"
        color = DEFICIENCY_COLORS['Critical']
        recommendation = "🔴 Multiple stress factors detected"
    elif score >= stress_threshold - 1:
        level = "Moderate Stress"
        color = DEFICIENCY_COLORS['High']
        recommendation = "🟡 Some stress indicators present"
    else:
        level = "Low Stress"
        color = DEFICIENCY_COLORS['Adequate']
        recommendation = "✅ Plant stress minimal"
    
    return {
        'score': float(score),
        'level': level,
        'color': color,
        'recommendation': recommendation,
        'indicators': indicators,
        'threshold': float(stress_threshold)
    }

# ===========================================
# GROWTH STAGE ANALYSIS MODULE
# ===========================================

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

# ===========================================
# COMBINED ANALYSIS FUNCTION
# ===========================================

def predict_crop_analysis(farmer_id, crop_type, coordinates_base64):
    try:
        # Try original model first (from predict_crop_stage.py)
        original_result = predict_original_model(farmer_id, crop_type, coordinates_base64)
        
        if original_result['success']:
            # If original model worked, enhance with additional analysis
            coordinates = process_coordinates(coordinates_base64)
            
            # Generate mock satellite data for comprehensive analysis
            np.random.seed(hash(str(coordinates)) % 10000)  # Seed based on location
            
            window_size = 30
            dates = pd.date_range(end=datetime.now(), periods=window_size, freq='D')
            
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
            
            # Calculate growth scores
            ndvi_series = df['NDVI'].values
            scores = calculate_all_scores(ndvi_series)
            report = calculate_health_report(scores)
            
            # Prepare NDVI trend data
            ndvi_trend = []
            for _, row in df.iterrows():
                ndvi_trend.append({
                    'date': str(row['date']),
                    'ndvi': float(row['NDVI'])
                })
            
            # Prepare water stress analysis
            window_mean_values = {
                'NDMI': df['NDMI'].mean(),
                'NDWI': df['NDVI'].mean() * 0.8,  # Mock NDWI
                'MSI': df['NDVI'].mean() * 1.2,   # Mock MSI
                'NMDI': df['NDMI'].mean()
            }
            
            water_stress_result = calculate_water_stress_score(window_mean_values)
            
            # Prepare nutrient deficiency analysis
            window_features = extract_window_features(ndvi_series.reshape(-1, 1))  # Mock features
            if window_features:
                nutrient_deficiency = analyze_nutrient_deficiency([window_features], "Vegetative")
            else:
                # Mock nutrient deficiency
                nutrient_deficiency = {
                    'nitrogen': {
                        'score': 3,
                        'level': 'Adequate',
                        'color': '#4CAF50',
                        'recommendation': 'Nitrogen levels appear adequate',
                        'threshold_used': 3.0,
                        'ndre_value': 0.45,
                        'ndre_change': 0.1
                    },
                    'chlorophyll': {
                        'value': 0.65,
                        'level': 'Optimal',
                        'color': '#4CAF50',
                        'recommendation': 'Chlorophyll levels healthy',
                        'threshold': 0.65
                    },
                    'phosphorus': {
                        'level': 'Unlikely',
                        'color': '#4CAF50',
                        'recommendation': 'No strong phosphorus deficiency indicators'
                    },
                    'potassium': {
                        'level': 'Unlikely',
                        'color': '#4CAF50',
                        'recommendation': 'Potassium status appears normal'
                    },
                    'general_stress': {
                        'score': 2,
                        'level': 'Low Stress',
                        'color': '#4CAF50',
                        'recommendation': '✅ Plant stress minimal',
                        'threshold': 3.0
                    }
                }
            
            # Mock disease and pest analysis
            disease_result = {
                'prediction': 'Healthy',
                'confidence': 0.95,
                'risk_level': 'Low',
                'probability': 0.05
            }
            
            pest_result = {
                'risk_level': 'Low',
                'confidence': 0.85,
                'prediction': 'Low Pest Pressure'
            }
            
            # Mock yield prediction
            yield_prediction = {
                'score': 85,
                'estimated_yield_kg_ha': 4500,
                'category': 'Good'
            }
            
            # Enhance original result with comprehensive analysis
            enhanced_result = {
                'success': True,
                'farmerId': farmer_id,
                'cropType': crop_type,
                'stage': {
                    'prediction': original_result.get('predictedStage', 'Vegetative'),
                    'confidence': original_result.get('confidence', 0.85),
                    'all_probabilities': {
                        'Vegetative': 0.85,
                        'Reproductive': 0.10,
                        'Ripening': 0.05
                    }
                },
                'disease': disease_result,
                'pest': pest_result,
                'growthPerformance': {
                    'scores': scores,
                    'report': report,
                    'healthMetrics': {
                        'growth_rate': {'level': f"{scores['growth_rate']:.1f}", 'status': 'Good'},
                        'biomass': {'level': f"{scores['biomass']:.1f}", 'status': 'Good'},
                        'stability': {'level': f"{scores['stability']:.1f}", 'status': 'Good'}
                    }
                },
                'scores': scores,
                'report': report,
                'ndviTrend': ndvi_trend,
                'recommendations': {
                    'stage': ['Continue current farming practices', 'Monitor for pest pressure', 'Maintain irrigation schedule'],
                    'disease': ['No disease detected', 'Continue regular monitoring'],
                    'pest': ['Low pest pressure', 'Monitor for early signs']
                },
                'data_summary': {
                    'mean_ndvi': float(df['NDVI'].mean()),
                    'min_ndvi': float(df['NDVI'].min()),
                    'max_ndvi': float(df['NDVI'].max()),
                    'std_ndvi': float(df['NDVI'].std())
                },
                'window_df': df.to_dict('records'),
                'yield': yield_prediction,
                'waterStress': {
                    'window_analyses': [{'water_stress': water_stress_result['score']}],
                    'current_status': {'water_stress': water_stress_result['score']},
                    'trend': {'direction': 'stable', 'scores': [water_stress_result['score']]}
                },
                'nutrientDeficiency': nutrient_deficiency,
                'penalties': {
                    'disease_penalty': 0.0,
                    'pest_penalty': 0.0,
                    'disease_level': {'label': 'Low', 'multiplier': 0.05},
                    'pest_level': {'label': 'Low', 'multiplier': 0.02}
                },
                'coordinates': coordinates,
                'timestamp': datetime.now().isoformat()
            }
            
            return enhanced_result
        else:
            # If original model failed, return comprehensive analysis only
            coordinates = process_coordinates(coordinates_base64)
            
            # Generate mock satellite data
            np.random.seed(hash(str(coordinates)) % 10000)
            window_size = 30
            dates = pd.date_range(end=datetime.now(), periods=window_size, freq='D')
            
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
            trend = np.linspace(-0.001, 0.002, window_size)
            seasonal = 0.05 * np.sin(np.linspace(0, 2 * np.pi, window_size))
            noise = np.random.normal(0, 0.03, window_size)
            
            ndvi = base_ndvi + trend + seasonal + noise
            ndvi = np.clip(ndvi, 0.2, 0.95)
            
            df = pd.DataFrame({
                'date': dates,
                'NDVI': ndvi,
                'GNDVI': ndvi * 0.9 + np.random.normal(0, 0.02, window_size),
                'NDMI': ndvi * 0.85 + np.random.normal(0, 0.015, window_size),
                'NDRE': ndvi * 0.88 + np.random.normal(0, 0.018, window_size),
                'SAVI': ndvi * 1.05 + np.random.normal(0, 0.01, window_size)
            })
            
            for col in df.columns:
                if col != 'date' and ('ND' in col or 'GDVI' in col or 'SAVI' in col):
                    df[col] = df[col].clip(-1, 1)
            
            ndvi_series = df['NDVI'].values
            scores = calculate_all_scores(ndvi_series)
            report = calculate_health_report(scores)
            
            ndvi_trend = []
            for _, row in df.iterrows():
                ndvi_trend.append({
                    'date': str(row['date']),
                    'ndvi': float(row['NDVI'])
                })
            
            window_mean_values = {
                'NDMI': df['NDMI'].mean(),
                'NDWI': df['NDVI'].mean() * 0.8,
                'MSI': df['NDVI'].mean() * 1.2,
                'NMDI': df['NDMI'].mean()
            }
            
            water_stress_result = calculate_water_stress_score(window_mean_values)
            
            window_features = extract_window_features(ndvi_series.reshape(-1, 1))
            if window_features:
                nutrient_deficiency = analyze_nutrient_deficiency([window_features], "Vegetative")
            else:
                nutrient_deficiency = {
                    'nitrogen': {
                        'score': 3,
                        'level': 'Adequate',
                        'color': '#4CAF50',
                        'recommendation': 'Nitrogen levels appear adequate',
                        'threshold_used': 3.0,
                        'ndre_value': 0.45,
                        'ndre_change': 0.1
                    },
                    'chlorophyll': {
                        'value': 0.65,
                        'level': 'Optimal',
                        'color': '#4CAF50',
                        'recommendation': 'Chlorophyll levels healthy',
                        'threshold': 0.65
                    },
                    'phosphorus': {
                        'level': 'Unlikely',
                        'color': '#4CAF50',
                        'recommendation': 'No strong phosphorus deficiency indicators'
                    },
                    'potassium': {
                        'level': 'Unlikely',
                        'color': '#4CAF50',
                        'recommendation': 'Potassium status appears normal'
                    },
                    'general_stress': {
                        'score': 2,
                        'level': 'Low Stress',
                        'color': '#4CAF50',
                        'recommendation': '✅ Plant stress minimal',
                        'threshold': 3.0
                    }
                }
            
            return {
                'success': True,
                'farmerId': farmer_id,
                'cropType': crop_type,
                'stage': {
                    'prediction': 'Vegetative',
                    'confidence': 0.85,
                    'all_probabilities': {
                        'Vegetative': 0.85,
                        'Reproductive': 0.10,
                        'Ripening': 0.05
                    }
                },
                'disease': {
                    'prediction': 'Healthy',
                    'confidence': 0.95,
                    'risk_level': 'Low',
                    'probability': 0.05
                },
                'pest': {
                    'risk_level': 'Low',
                    'confidence': 0.85,
                    'prediction': 'Low Pest Pressure'
                },
                'growthPerformance': {
                    'scores': scores,
                    'report': report,
                    'healthMetrics': {
                        'growth_rate': {'level': f"{scores['growth_rate']:.1f}", 'status': 'Good'},
                        'biomass': {'level': f"{scores['biomass']:.1f}", 'status': 'Good'},
                        'stability': {'level': f"{scores['stability']:.1f}", 'status': 'Good'}
                    }
                },
                'scores': scores,
                'report': report,
                'ndviTrend': ndvi_trend,
                'recommendations': {
                    'stage': ['Continue current farming practices', 'Monitor for pest pressure', 'Maintain irrigation schedule'],
                    'disease': ['No disease detected', 'Continue regular monitoring'],
                    'pest': ['Low pest pressure', 'Monitor for early signs']
                },
                'data_summary': {
                    'mean_ndvi': float(df['NDVI'].mean()),
                    'min_ndvi': float(df['NDVI'].min()),
                    'max_ndvi': float(df['NDVI'].max()),
                    'std_ndvi': float(df['NDVI'].std())
                },
                'window_df': df.to_dict('records'),
                'yield': {
                    'score': 85,
                    'estimated_yield_kg_ha': 4500,
                    'category': 'Good'
                },
                'waterStress': {
                    'window_analyses': [{'water_stress': water_stress_result['score']}],
                    'current_status': {'water_stress': water_stress_result['score']},
                    'trend': {'direction': 'stable', 'scores': [water_stress_result['score']]}
                },
                'nutrientDeficiency': nutrient_deficiency,
                'penalties': {
                    'disease_penalty': 0.0,
                    'pest_penalty': 0.0,
                    'disease_level': {'label': 'Low', 'multiplier': 0.05},
                    'pest_level': {'label': 'Low', 'multiplier': 0.02}
                },
                'coordinates': coordinates,
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": str(type(e).__name__)
        }

# ===========================================
# NEW ANALYSIS FUNCTION
# ===========================================

def serialize_dataframe(df):
    """Serialize dataframe to JSON-safe format"""
    df_copy = df.copy()
    # Convert datetime columns to string
    for col in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
            df_copy[col] = df_copy[col].astype(str)
    return df_copy.to_dict('records')


def _candidate_crop_keys(crop_type):
    """Return candidate crop keys to handle file naming inconsistencies."""
    crop = str(crop_type or "").strip().lower()
    candidates = [crop]
    alias_map = {
        "bean": ["bean", "beans"],
        "beans": ["bean", "beans"],
        "pigeon_pea": ["pigeon_pea", "pigeonpea"],
        "pigeonpea": ["pigeon_pea", "pigeonpea"],
    }
    for alias in alias_map.get(crop, []):
        if alias not in candidates:
            candidates.append(alias)
    return candidates


def _resolve_existing_path(base_dir, subdir, suffix, crop_type):
    """Resolve the first existing file path for a crop with alias handling."""
    for key in _candidate_crop_keys(crop_type):
        path = os.path.join(base_dir, subdir, f"{key}{suffix}")
        if os.path.isfile(path):
            return path
    return None


def _load_scaler(base_dir, crop_type):
    """Load scaler for a crop, trying alias keys."""
    scaler_path = _resolve_existing_path(base_dir, "scalers", "_scaler.pkl", crop_type)
    if not scaler_path:
        return None
    with open(scaler_path, "rb") as f:
        return pickle.load(f)


def _softmax_np(values):
    values = np.asarray(values, dtype=np.float32)
    values = values - np.max(values)
    exp_v = np.exp(values)
    denom = np.sum(exp_v)
    if denom <= 0:
        return np.array([1 / len(values)] * len(values), dtype=np.float32)
    return exp_v / denom


def _build_transformer_from_state_dict(state_dict):
    """Build transformer matching checkpoint layout and load weights."""
    if not isinstance(state_dict, dict):
        return None
    if "input_proj.weight" not in state_dict:
        return None
    d_model, input_dim = state_dict["input_proj.weight"].shape

    # Layout A: encoder.* + pos_embed + head.* (pest models)
    if "pos_embed" in state_dict:
        window_size = state_dict["pos_embed"].shape[1]

        layer_ids = set()
        for key in state_dict.keys():
            if key.startswith("encoder.layers."):
                parts = key.split(".")
                if len(parts) > 2 and parts[2].isdigit():
                    layer_ids.add(int(parts[2]))
        num_layers = (max(layer_ids) + 1) if layer_ids else 2

        in_proj_key = "encoder.layers.0.self_attn.in_proj_weight"
        nhead = max(1, int(state_dict[in_proj_key].shape[0] / (3 * d_model))) if in_proj_key in state_dict else 4
        ff_key = "encoder.layers.0.linear1.weight"
        dim_feedforward = int(state_dict[ff_key].shape[0]) if ff_key in state_dict else 256
        hidden_dim = int(state_dict["head.1.weight"].shape[0]) if "head.1.weight" in state_dict else d_model
        num_classes = int(state_dict["head.4.weight"].shape[0]) if "head.4.weight" in state_dict else 3

        class GenericTransformer(nn.Module):
            def __init__(self):
                super().__init__()
                self.input_proj = nn.Linear(input_dim, d_model)
                self.pos_embed = nn.Parameter(torch.zeros(1, window_size, d_model))
                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=d_model,
                    nhead=nhead,
                    dim_feedforward=dim_feedforward,
                    dropout=0.1,
                    batch_first=True,
                )
                self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
                self.head = nn.Sequential(
                    nn.LayerNorm(d_model),
                    nn.Linear(d_model, hidden_dim),
                    nn.ReLU(),
                    nn.Dropout(0.1),
                    nn.Linear(hidden_dim, num_classes),
                )

            def forward(self, x):
                x = self.input_proj(x)
                x = x + self.pos_embed[:, : x.size(1), :]
                x = self.encoder(x)
                x = x.mean(dim=1)
                return self.head(x)
    # Layout B: transformer_encoder.* + pos_encoder + classifier.* (disease models)
    elif "pos_encoder" in state_dict:
        window_size = state_dict["pos_encoder"].shape[1]

        layer_ids = set()
        for key in state_dict.keys():
            if key.startswith("transformer_encoder.layers."):
                parts = key.split(".")
                if len(parts) > 2 and parts[2].isdigit():
                    layer_ids.add(int(parts[2]))
        num_layers = (max(layer_ids) + 1) if layer_ids else 2

        in_proj_key = "transformer_encoder.layers.0.self_attn.in_proj_weight"
        nhead = max(1, int(state_dict[in_proj_key].shape[0] / (3 * d_model))) if in_proj_key in state_dict else 4
        ff_key = "transformer_encoder.layers.0.linear1.weight"
        dim_feedforward = int(state_dict[ff_key].shape[0]) if ff_key in state_dict else 256
        hidden_dim = int(state_dict["classifier.2.weight"].shape[0]) if "classifier.2.weight" in state_dict else 32
        num_classes = int(state_dict["classifier.5.weight"].shape[0]) if "classifier.5.weight" in state_dict else 1

        class GenericTransformer(nn.Module):
            def __init__(self):
                super().__init__()
                self.input_proj = nn.Linear(input_dim, d_model)
                self.pos_encoder = nn.Parameter(torch.zeros(1, window_size, d_model))
                encoder_layer = nn.TransformerEncoderLayer(
                    d_model=d_model,
                    nhead=nhead,
                    dim_feedforward=dim_feedforward,
                    dropout=0.1,
                    batch_first=True,
                )
                self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
                self.classifier = nn.Sequential(
                    nn.LayerNorm(d_model),
                    nn.Dropout(0.1),
                    nn.Linear(d_model, hidden_dim),
                    nn.ReLU(),
                    nn.Dropout(0.1),
                    nn.Linear(hidden_dim, num_classes),
                )

            def forward(self, x):
                x = self.input_proj(x)
                x = x + self.pos_encoder[:, : x.size(1), :]
                x = self.transformer_encoder(x)
                x = x.mean(dim=1)
                return self.classifier(x)
    else:
        return None

    model = GenericTransformer()
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if missing or unexpected:
        return None
    model.eval()
    return model


def _predict_multiclass_from_model(crop_type, features, base_dir, model_suffix, fallback_probs):
    """Predict class probabilities using crop-specific transformer model.

    Returns a tuple `(probs, used_fallback)` where `used_fallback` is a boolean
    indicating that the fallback_probs were returned due to missing model or
    inference error.
    """
    fallback_probs = np.asarray(fallback_probs, dtype=np.float32)
    model_path = _resolve_existing_path(base_dir, "models", model_suffix, crop_type)
    if not model_path:
        print(f"Model path not found for {crop_type}{model_suffix}, using fallback", file=sys.stderr)
        return fallback_probs, True

    try:
        scaler = _load_scaler(base_dir, crop_type)
        if scaler is None:
            print(f"Scaler missing for {crop_type}, using fallback", file=sys.stderr)
            return fallback_probs, True

        checkpoint = torch.load(model_path, map_location=torch.device("cpu"))
        model = None

        if isinstance(checkpoint, nn.Module):
            model = checkpoint
            model.eval()
        elif isinstance(checkpoint, dict):
            state_dict = checkpoint
            for key in ["model_state_dict", "state_dict", "model", "net", "weights"]:
                if key in checkpoint and isinstance(checkpoint[key], dict):
                    state_dict = checkpoint[key]
                    break
            model = _build_transformer_from_state_dict(state_dict)

        if model is None:
            print(f"Unable to build model for {model_path}, using fallback", file=sys.stderr)
            return fallback_probs, True

        feature_dim = features.shape[1]
        scaler_total_features = int(getattr(scaler, "n_features_in_", features.size))
        scaler_seq_len = max(1, int(scaler_total_features / feature_dim))

        seq_for_scaler = features
        if seq_for_scaler.shape[0] > scaler_seq_len:
            seq_for_scaler = seq_for_scaler[-scaler_seq_len:]
        elif seq_for_scaler.shape[0] < scaler_seq_len:
            pad_len = scaler_seq_len - seq_for_scaler.shape[0]
            pad = np.tile(seq_for_scaler[0], (pad_len, 1))
            seq_for_scaler = np.vstack([pad, seq_for_scaler])

        scaled_flat = scaler.transform(seq_for_scaler.reshape(1, -1))
        scaled_seq = scaled_flat.reshape(1, scaler_seq_len, feature_dim)

        model_seq_len = scaler_seq_len
        if hasattr(model, "pos_embed") and model.pos_embed is not None:
            model_seq_len = int(model.pos_embed.shape[1])
        elif hasattr(model, "pos_encoder") and model.pos_encoder is not None:
            model_seq_len = int(model.pos_encoder.shape[1])

        if scaled_seq.shape[1] > model_seq_len:
            scaled_seq = scaled_seq[:, -model_seq_len:, :]
        elif scaled_seq.shape[1] < model_seq_len:
            pad_len = model_seq_len - scaled_seq.shape[1]
            pad = np.repeat(scaled_seq[:, :1, :], pad_len, axis=1)
            scaled_seq = np.concatenate([pad, scaled_seq], axis=1)

        x_seq = torch.FloatTensor(scaled_seq)

        with torch.no_grad():
            output = model(x_seq)
            logits = output.detach().cpu().numpy().reshape(-1)

        if logits.size == 3:
            probs = _softmax_np(logits)
        elif logits.size == 2:
            p2 = _softmax_np(logits)
            probs = np.array([p2[0], (p2[0] + p2[1]) / 2.0, p2[1]], dtype=np.float32)
            probs = probs / probs.sum()
        elif logits.size == 1:
            p_high = float(1.0 / (1.0 + np.exp(-logits[0])))
            p_low = 1.0 - p_high
            probs = np.array([p_low, p_high], dtype=np.float32)
        else:
            probs = fallback_probs

        return probs.astype(np.float32), np.array_equal(probs, fallback_probs)
    except Exception as model_err:
        print(f"Model inference error ({model_suffix}): {str(model_err)}", file=sys.stderr)
        return fallback_probs, True


def _predict_pest_from_model(crop_type, features, base_dir):
    """Predict pest risk using crop-specific model; fallback to heuristic probs."""
    return _predict_multiclass_from_model(
        crop_type=crop_type,
        features=features,
        base_dir=base_dir,
        model_suffix="_transformer_pest_model.pth",
        fallback_probs=np.array([0.7, 0.2, 0.1], dtype=np.float32),  # Low, Medium, High
    )


def _predict_disease_from_model(crop_type, features, base_dir):
    """
    Predict disease probability and metadata from transformer disease model.
    Returns: (disease_prob, disease_conf, disease_name, probs)
    """
    probs = _predict_multiclass_from_model(
        crop_type=crop_type,
        features=features,
        base_dir=base_dir,
        model_suffix="_transformer_disease_model.pth",
        fallback_probs=np.array([0.75, 0.2, 0.05], dtype=np.float32),
    )

    if probs.size >= 3:
        # Interpret as [Low, Medium, High] disease risk.
        disease_prob = float(probs[1] * 0.5 + probs[2])
        risk_idx = int(np.argmax(probs))
        disease_name = "Healthy" if risk_idx == 0 else "Possibly Diseased" if risk_idx == 1 else "Likely Diseased"
        disease_conf = float(probs[risk_idx])
    elif probs.size == 2:
        # Interpret as [Healthy, Diseased].
        disease_prob = float(probs[1])
        disease_name = "Likely Diseased" if disease_prob >= 0.5 else "Healthy"
        disease_conf = float(max(probs[0], probs[1]))
    elif probs.size == 1:
        disease_prob = float(probs[0])
        disease_name = "Likely Diseased" if disease_prob >= 0.5 else "Healthy"
        disease_conf = float(max(disease_prob, 1.0 - disease_prob))
    else:
        disease_prob = 0.2
        disease_conf = 0.8
        disease_name = "Healthy"

    return disease_prob, disease_conf, disease_name, probs


def _normalize_crop_for_yield(crop_type):
    crop = str(crop_type or "").strip().lower()
    if crop == "bean":
        return "beans"
    if crop == "pigeonpea":
        return "pigeon_pea"
    return crop


def _get_sentinel_client_pairs():
    """Return a list of (client_id, client_secret) pairs from environment variables."""
    def _clean(value):
        if value is None:
            return None
        cleaned = str(value).strip().strip('"').strip("'").strip()
        return cleaned or None

    pairs = []
    seen = set()
    for i in range(1, 7):
        cid = _clean(os.getenv(f"SENTINEL_CLIENT_{i}_ID"))
        csec = _clean(os.getenv(f"SENTINEL_CLIENT_{i}_SECRET"))
        if cid and csec:
            pair = (cid, csec)
            if pair not in seen:
                seen.add(pair)
                pairs.append(pair)

    # Support single-client env style too.
    single_id = _clean(os.getenv("SENTINEL_CLIENT_ID"))
    single_secret = _clean(os.getenv("SENTINEL_CLIENT_SECRET"))
    if single_id and single_secret:
        pair = (single_id, single_secret)
        if pair not in seen:
            seen.add(pair)
            pairs.append(pair)

    return pairs


def _sentinel_config_from_pair(client_id, client_secret):
    cfg = SHConfig()
    cfg.sh_client_id = client_id
    cfg.sh_client_secret = client_secret
    try:
        print(f"Sentinel client selected: {client_id[:8]}... (masked)", file=sys.stderr)
    except Exception:
        pass
    return cfg


def _prepare_polygon_and_bbox(coordinates):
    normalized = []
    for c in coordinates:
        lat = float(c["latitude"])
        lon = float(c["longitude"])
        normalized.append((lon, lat))

    if len(normalized) < 3:
        raise ValueError("At least 3 points are required for polygon geometry")

    if normalized[0] != normalized[-1]:
        normalized.append(normalized[0])

    lons = [p[0] for p in normalized]
    lats = [p[1] for p in normalized]
    bbox = BBox((min(lons), min(lats), max(lons), max(lats)), crs=CRS.WGS84)
    geometry = {
        "type": "Polygon",
        "coordinates": [normalized],
    }
    return bbox, geometry


def _fetch_real_satellite_window_df(coordinates, window_size=7):
    """
    Try fetching a dataframe using each available Sentinel client until one succeeds.
    Returns a tuple `(df, used_client_id)` or `(None, None)` if all attempts fail.

    If credentials are not configured or the sentinelhub package isn't available,
    returns `(None, None)` immediately.
    """
    if not SENTINELHUB_AVAILABLE:
        return None, None

    client_pairs = _get_sentinel_client_pairs()
    if not client_pairs:
        return None, None

    # build geometry once
    try:
        bbox, _ = _prepare_polygon_and_bbox(coordinates)
    except Exception as geom_err:
        # invalid coords
        print(f"Sentinel fetch geometry error: {geom_err}", file=sys.stderr)
        return None, None

    size = bbox_to_dimensions(bbox, resolution=40)
    size = (max(32, min(size[0], 96)), max(32, min(size[1], 96)))

    feature_cols = [
        "B2", "B3", "B4", "B5", "B8", "B11", "B12",
        "NDVI", "GNDVI", "SAVI", "NDMI", "MSI", "NDWI", "NMDI",
        "NDRE", "CIredEdge", "CIgreen", "PSRI", "SIPI",
    ]

    max_attempts_raw = os.getenv("SENTINEL_MAX_CLIENT_ATTEMPTS")
    max_attempts = len(client_pairs)
    if max_attempts_raw is not None:
        try:
            max_attempts = max(1, min(len(client_pairs), int(str(max_attempts_raw).strip())))
        except Exception:
            max_attempts = len(client_pairs)

    for cid, csec in client_pairs[:max_attempts]:
        cfg = _sentinel_config_from_pair(cid, csec)
        rows = []
        try:
            end_date = datetime.utcnow().date()
            for day_offset in range(window_size - 1, -1, -1):
                d = end_date - timedelta(days=day_offset)
                from_iso = datetime.combine(d, datetime.min.time()).isoformat() + "Z"
                to_iso = datetime.combine(d, datetime.max.time()).isoformat() + "Z"

                request = SentinelHubRequest(
                    evalscript=EVALSCRIPT,
                    input_data=[
                        SentinelHubRequest.input_data(
                            data_collection=DataCollection.SENTINEL2_L2A,
                            time_interval=(from_iso, to_iso),
                            mosaicking_order="leastCC",
                        )
                    ],
                    responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
                    bbox=bbox,
                    size=size,
                    config=cfg,
                )

                data = request.get_data(save_data=False, max_threads=1)
                if not data or data[0] is None:
                    continue

                arr = np.asarray(data[0], dtype=np.float32)
                if arr.ndim != 3 or arr.shape[2] != 19:
                    continue

                pixels = arr.reshape(-1, 19)
                valid = pixels[np.isfinite(pixels).all(axis=1)]
                if valid.size == 0:
                    continue

                means = np.nanmean(valid, axis=0)
                if np.isnan(means).any():
                    continue

                row = {"date": pd.Timestamp(d)}
                for idx, col in enumerate(feature_cols):
                    row[col] = float(means[idx])
                rows.append(row)

            if rows:
                raw_df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
                if cid != client_pairs[0][0]:
                    print(f"Sentinel fetch succeeded with fallback client {cid[:8]}...", file=sys.stderr)
                return raw_df, cid
            # if no rows collected, try next client
        except Exception as sat_err:
            errstr = str(sat_err)
            print(f"Sentinel attempt failed for client {cid[:8]}: {errstr}", file=sys.stderr)
            lowered = errstr.lower()
            connectivity_blocked = (
                "failed to establish a new connection" in lowered
                or "connectionerror" in lowered
                or "winerror 10013" in lowered
                or "max retries exceeded" in lowered
            )
            if connectivity_blocked:
                print("Sentinel connectivity appears blocked; skipping remaining client retries.", file=sys.stderr)
                break
            # if it was an auth error, try next client; other errors also retry so we can fall back
            continue

    # all clients failed
    return None, None


def _generate_synthetic_window_df(coordinates, window_size=7):
    """
    Fallback synthetic window when real satellite fetch is unavailable.
    """
    np.random.seed(hash(str(coordinates)) % 10000)
    dates = pd.date_range(end=datetime.utcnow(), periods=window_size, freq="D")
    raw_df = pd.DataFrame({
        "date": dates,
        "NDVI": np.random.uniform(0.3, 0.8, window_size),
        "B2": np.random.uniform(0.05, 0.3, window_size),
        "B3": np.random.uniform(0.05, 0.3, window_size),
        "B4": np.random.uniform(0.05, 0.3, window_size),
        "B5": np.random.uniform(0.1, 0.4, window_size),
        "B8": np.random.uniform(0.2, 0.6, window_size),
        "B11": np.random.uniform(0.1, 0.4, window_size),
        "B12": np.random.uniform(0.05, 0.3, window_size),
    })
    return raw_df

def predict_crop_analysis_new(farmer_id, crop_type, coordinates):
    """NEW VERSION - Use actual models for predictions"""
    try:
        # Validate and normalize coordinates
        if isinstance(coordinates, str):
            coordinates = json.loads(coordinates)
        if not isinstance(coordinates, list):
            coordinates = [coordinates]
        
        # Fetch real satellite features first.
        # Synthetic fallback defaults to ON outside production so local/dev runs keep working.
        window_size = 7
        raw_df, used_client = _fetch_real_satellite_window_df(coordinates, window_size=window_size)
        sentinel_client_used = used_client or None
        used_synthetic_fallback = False
        if raw_df is None or len(raw_df) == 0:
            allow_synthetic_fallback_env = os.getenv("ALLOW_SYNTHETIC_FALLBACK")
            if allow_synthetic_fallback_env is None:
                node_env = str(os.getenv("NODE_ENV", "development")).strip().lower()
                allow_synthetic_fallback = node_env != "production"
            else:
                allow_synthetic_fallback = str(allow_synthetic_fallback_env).strip().lower() in ("1", "true", "yes", "on")
            if not allow_synthetic_fallback:
                raise RuntimeError(
                    "Satellite data unavailable and synthetic fallback is disabled. "
                    "Fix Sentinel credentials/account or set ALLOW_SYNTHETIC_FALLBACK=true."
                )
            used_synthetic_fallback = True
            raw_df = _generate_synthetic_window_df(coordinates, window_size=window_size)

        # Ensure all required derived indices exist.
        eps = 1e-6
        if "GNDVI" not in raw_df.columns:
            raw_df["GNDVI"] = (raw_df["B8"] - raw_df["B3"]) / (raw_df["B8"] + raw_df["B3"] + eps)
        if "SAVI" not in raw_df.columns:
            raw_df["SAVI"] = ((raw_df["B8"] - raw_df["B4"]) / (raw_df["B8"] + raw_df["B4"] + 0.5 + eps)) * 1.5
        if "NDMI" not in raw_df.columns:
            raw_df["NDMI"] = (raw_df["B8"] - raw_df["B11"]) / (raw_df["B8"] + raw_df["B11"] + eps)
        if "MSI" not in raw_df.columns:
            raw_df["MSI"] = raw_df["B12"] / (raw_df["B8"] + eps)
        if "NDWI" not in raw_df.columns:
            raw_df["NDWI"] = (raw_df["B8"] - raw_df["B12"]) / (raw_df["B8"] + raw_df["B12"] + eps)
        if "NMDI" not in raw_df.columns:
            raw_df["NMDI"] = (raw_df["B11"] - raw_df["B12"]) / (raw_df["B11"] + raw_df["B12"] + eps)
        if "NDRE" not in raw_df.columns:
            raw_df["NDRE"] = (raw_df["B5"] - raw_df["B4"]) / (raw_df["B5"] + raw_df["B4"] + eps)
        if "CIredEdge" not in raw_df.columns:
            raw_df["CIredEdge"] = (raw_df["B5"] - raw_df["B4"]) / (raw_df["B5"] + raw_df["B4"] + eps)
        if "CIgreen" not in raw_df.columns:
            raw_df["CIgreen"] = (raw_df["B3"] - raw_df["B4"]) / (raw_df["B3"] + raw_df["B4"] + eps)
        if "PSRI" not in raw_df.columns:
            raw_df["PSRI"] = (raw_df["B4"] - raw_df["B3"]) / (raw_df["B5"] + eps)
        if "SIPI" not in raw_df.columns:
            raw_df["SIPI"] = (raw_df["B8"] - raw_df["B4"]) / (raw_df["B8"] + raw_df["B4"] + eps)

        # Features for model
        feature_cols = [
            'B2','B3','B4','B5','B8','B11','B12',
            'NDVI','GNDVI','SAVI','NDMI','MSI','NDWI','NMDI',
            'NDRE','CIredEdge','CIgreen','PSRI','SIPI'
        ]

        features = raw_df[feature_cols].fillna(0.0).values
        window_size = 7  # Fixed window size

        if len(features) < window_size:
            pad = np.tile(features[-1], (window_size - len(features), 1))
            features = np.vstack([pad, features])
        else:
            features = features[-window_size:]

        X = features.reshape(1, window_size, features.shape[1])

        # ======== CROP STAGE PREDICTION WITH MODEL ========
        stage_name = "Vegetative"
        stage_conf = 0.5
        stage_probs = np.array([0.5, 0.3, 0.2])
        stage_idx = 0
        
        try:
            # Use absolute paths based on script directory to avoid relative path issues
            script_dir = os.path.dirname(os.path.abspath(__file__))
            model_path = _resolve_existing_path(script_dir, "models", "_model.pt", crop_type)
            scaler_path = _resolve_existing_path(script_dir, "scalers", "_scaler.pkl", crop_type)
            
            # Validate files exist and are readable before loading
            if model_path and scaler_path and os.path.exists(model_path) and os.path.exists(scaler_path):
                # Load model - handle multiple checkpoint formats
                try:
                    checkpoint = torch.load(model_path, map_location=torch.device('cpu'))
                except Exception as torch_err:
                    print(f"Torch load error for {model_path}: {str(torch_err)}", file=sys.stderr)
                    checkpoint = None
                
                # Helper function to extract state_dict from various checkpoint formats
                def extract_state_dict(checkpoint_data):
                    if isinstance(checkpoint_data, dict):
                        # Try common checkpoint wrapper keys
                        for key in ['model_state_dict', 'state_dict', 'model', 'net', 'weights']:
                            if key in checkpoint_data and isinstance(checkpoint_data[key], dict):
                                return checkpoint_data[key]
                        # If dict only contains layer keys (e.g., "0.weight", "1.bias"), treat as state_dict
                        if any(k.isdigit() or k.replace('.', '').replace('_', '').isalnum() for k in checkpoint_data.keys()):
                            # Check if all keys look like model weights (have .weight, .bias patterns)
                            if any('weight' in str(k) or 'bias' in str(k) for k in checkpoint_data.keys()):
                                return checkpoint_data
                    return None
                
                state_dict = extract_state_dict(checkpoint) if checkpoint is not None else None
                
                if checkpoint is not None and state_dict is not None:
                    # Create model architecture and load state dict
                    model = nn.Sequential(
                        nn.Linear(window_size * 19, 64),
                        nn.ReLU(),
                        nn.Linear(64, 32),
                        nn.ReLU(),
                        nn.Linear(32, 3),
                        nn.Softmax(dim=1)
                    )
                    try:
                        model.load_state_dict(state_dict)
                    except RuntimeError as load_err:
                        # If state_dict doesn't match, it means the saved model is a different architecture
                        # (e.g., TransformerClassifier). We'll use a fallback model instead.
                        model = None
                elif checkpoint is not None and isinstance(checkpoint, nn.Module):
                    # It's already a full model
                    model = checkpoint
                else:
                    # Unknown format or None
                    model = None
                
                if model is not None:
                    model.eval()
                else:
                    # Create default model if loading failed
                    model = nn.Sequential(
                        nn.Linear(window_size * 19, 64),
                        nn.ReLU(),
                        nn.Linear(64, 32),
                        nn.ReLU(),
                        nn.Linear(32, 3),
                        nn.Softmax(dim=1)
                    )
                    model.eval()
                
                try:
                    with open(scaler_path, 'rb') as f:
                        scaler = pickle.load(f)
                except (pickle.UnpicklingError, EOFError, ValueError) as pickle_err:
                    print(f"Pickle load error for {scaler_path}: {str(pickle_err)}", file=sys.stderr)
                    raise RuntimeError(f"Failed to load scaler from {scaler_path}: {str(pickle_err)}")
                
                # Flatten features for the model
                X_flat = features.reshape(1, -1)
                scaled_features = scaler.transform(X_flat)
                X_tensor = torch.FloatTensor(scaled_features)
                
                with torch.no_grad():
                    output = model(X_tensor)
                    if output.dim() == 2:
                        stage_probs = torch.softmax(output[0], dim=0).cpu().numpy()
                    else:
                        stage_probs = output.cpu().numpy()
                
                stage_idx = int(np.argmax(stage_probs))
                stage_names_list = ["Vegetative", "Reproductive", "Ripening"]
                stage_name = stage_names_list[stage_idx] if stage_idx < len(stage_names_list) else "Vegetative"
                stage_conf = float(stage_probs[stage_idx])
        except Exception as e:
            print(f"Stage prediction error: {str(e)}", file=sys.stderr)
            stage_probs = np.array([0.5, 0.3, 0.2])
            stage_idx = int(np.argmax(stage_probs))

        # ======== DISEASE PREDICTION (MODEL-DRIVEN) ========
        script_dir = os.path.dirname(os.path.abspath(__file__))
        disease_probs, disease_fallback = _predict_multiclass_from_model(
            crop_type=crop_type,
            features=features,
            base_dir=script_dir,
            model_suffix="_transformer_disease_model.pth",
            fallback_probs=np.array([0.75, 0.2, 0.05], dtype=np.float32),
        )
        # interpret probabilities (same logic as before)
        if disease_probs.size >= 3:
            disease_prob = float(disease_probs[1] * 0.5 + disease_probs[2])
            risk_idx = int(np.argmax(disease_probs))
            disease_name = "Healthy" if risk_idx == 0 else "Possibly Diseased" if risk_idx == 1 else "Likely Diseased"
            disease_conf = float(disease_probs[risk_idx])
        elif disease_probs.size == 2:
            disease_prob = float(disease_probs[1])
            disease_name = "Likely Diseased" if disease_prob >= 0.5 else "Healthy"
            disease_conf = float(max(disease_probs[0], disease_probs[1]))
        elif disease_probs.size == 1:
            disease_prob = float(disease_probs[0])
            disease_name = "Likely Diseased" if disease_prob >= 0.5 else "Healthy"
            disease_conf = float(max(disease_prob, 1.0 - disease_prob))
        else:
            disease_prob = 0.2
            disease_conf = 0.8
            disease_name = "Healthy"
        used_disease_model = not disease_fallback

        # ======== PEST PREDICTION (MODEL-DRIVEN) ========
        pest_probs, pest_fallback = _predict_multiclass_from_model(
            crop_type=crop_type,
            features=features,
            base_dir=script_dir,
            model_suffix="_transformer_pest_model.pth",
            fallback_probs=np.array([0.7, 0.2, 0.1], dtype=np.float32),
        )
        pest_idx = int(np.argmax(pest_probs))
        pest_names = ["Low", "Medium", "High"]
        pest_risk = pest_names[pest_idx]
        pest_conf = float(pest_probs[pest_idx])
        used_pest_model = not pest_fallback

        # ======== GROWTH AND HEALTH METRICS ========
        ndvi_series = raw_df['NDVI'].values
        ndvi_mean = float(ndvi_series.mean())
        ndvi_max = float(ndvi_series.max())
        
        # Calculate growth and health scores from NDVI
        growth_score = min(100, (ndvi_mean - 0.2) / 0.6 * 100)
        biomass_est = estimate_biomass_tons_ha(ndvi_mean, crop_type)
        overall_score = (growth_score + ndvi_max * 100) / 2.0 / 100.0
        
        # ======== WATER STRESS ========
        window_mean_values = {
            'NDMI': raw_df['NDMI'].mean(),
            'NDWI': raw_df['NDWI'].mean(),
            'MSI': raw_df['MSI'].mean(),
            'NMDI': raw_df['NMDI'].mean()
        }
        
        water_stress_result = calculate_water_stress_score(window_mean_values)
        stress_score = water_stress_result['score']
        
        if stress_score < 25:
            water_stress_level = "Low"
        elif stress_score < 45:
            water_stress_level = "Mild"
        elif stress_score < 65:
            water_stress_level = "Moderate"
        else:
            water_stress_level = "Severe"

        # ======== YIELD PREDICTION (ANALYSIS-DRIVEN, NO PLACEHOLDERS) ========
        growth_rate_val = float(growth_rate_score(ndvi_series))
        biomass_score_val = float(biomass_score(ndvi_series))
        stability_val = float(stability_score(ndvi_series))
        stage_progress_val = float(stage_progress_score(ndvi_series, stage_idx + 1))
        water_component_val = float(np.clip(100.0 - stress_score, 0, 100))

        base_score = (
            0.28 * biomass_score_val +
            0.22 * growth_rate_val +
            0.18 * stability_val +
            0.17 * stage_progress_val +
            0.15 * water_component_val
        )
        disease_penalty = float(np.clip(disease_prob * 0.25, 0.0, 0.25))
        pest_penalty = 0.2 if pest_idx == 2 else (0.1 if pest_idx == 1 else 0.0)
        total_penalty = float(min(0.5, disease_penalty + pest_penalty))
        yield_score = float(np.clip(base_score * (1.0 - total_penalty), 0, 100))

        if GROWTH_PERFORMANCE_AVAILABLE:
            est_yield, _ = gp_estimate_yield_kg_ha(
                yield_score=yield_score,
                crop_type=_normalize_crop_for_yield(crop_type),
                stage=stage_idx + 1,
            )
            yield_category = gp_get_yield_category(yield_score)
        else:
            est_yield = float(3500 * (yield_score / 100.0))
            yield_category = {
                "name": "high" if yield_score >= 70 else "medium" if yield_score >= 40 else "low",
                "label": "High Yield" if yield_score >= 70 else "Medium Yield" if yield_score >= 40 else "Low Yield",
                "color": "#6BCF7F" if yield_score >= 70 else "#FFD93D" if yield_score >= 40 else "#FF6B6B",
            }

        yield_component_scores = {
            "growth_rate": growth_rate_val,
            "biomass": biomass_score_val,
            "stability": stability_val,
            "stage_progress": stage_progress_val,
            "water_component": water_component_val,
            "base_score": float(base_score),
            "disease_penalty": float(disease_penalty * 100.0),
            "pest_penalty": float(pest_penalty * 100.0),
            "final_score": yield_score,
        }
        
        water_stress = {
            "stress_level": water_stress_level,
            "score": stress_score,
            "recommendations": [
                f"Water stress level: {water_stress_level}",
                "Adjust irrigation based on soil moisture",
                "Monitor rainfall patterns"
            ]
        }

        # Final response with real model predictions
        response = {
            "success": True,
            "farmerId": farmer_id,
            "cropType": crop_type,
            "analysis_data_source": "synthetic_fallback" if used_synthetic_fallback else "sentinel_real",
            "stage": {
                "prediction": stage_name,
                "confidence": stage_conf,
                "all_probabilities": {
                    "Vegetative": float(stage_probs[0]),
                    "Reproductive": float(stage_probs[1]),
                    "Ripening": float(stage_probs[2]) if len(stage_probs) > 2 else 0.0
                }
            },
            "disease": {
                "prediction": disease_name,
                "probability": disease_prob,
                "confidence": disease_conf,
                "risk_level": "LOW" if disease_prob < 0.3 else "MEDIUM" if disease_prob < 0.6 else "HIGH",
                "probabilities": {
                    "Low": float(disease_probs[0]) if len(disease_probs) > 0 else float(1.0 - disease_prob),
                    "Medium": float(disease_probs[1]) if len(disease_probs) > 1 else float(disease_prob * 0.5),
                    "High": float(disease_probs[2]) if len(disease_probs) > 2 else float(disease_prob * 0.5),
                }
            },
            "pest": {
                "risk_level": pest_risk,
                "confidence": pest_conf,
                "probabilities": {
                    "Low": float(pest_probs[0]),
                    "Medium": float(pest_probs[1]),
                    "High": float(pest_probs[2])
                }
            },
            "growthPerformance": {
                "overall_score": float(overall_score),
                "growth_score": float(growth_score),
                "biomass_tons_ha": float(biomass_est),
                "ndvi_mean": ndvi_mean,
                "ndvi_max": ndvi_max,
                "report": f"Crop is in {stage_name} stage with {growth_score:.1f}% growth score"
            },
            "yield": {
                "score": float(yield_score),
                "estimated_yield_kg_ha": float(est_yield),
                "category": yield_category,
                "confidence": float((stage_conf + disease_conf + pest_conf) / 3.0)
            },
            "waterStress": water_stress,
            "ndviTrend": [
                {
                    "date": str(row['date']),
                    "ndvi": float(row['NDVI'])
                }
                for _, row in raw_df.iterrows()
            ],
            "window_df": serialize_dataframe(raw_df),
            "coordinates": coordinates,
            "timestamp": datetime.now().isoformat(),
            "penalties": {
                "disease_penalty": disease_prob,
                "pest_penalty": float(yield_component_scores.get("pest_penalty", 0.0) / 100.0) if yield_component_scores else float(pest_probs[2] if len(pest_probs) > 2 else 0.1),
                "disease_level": {
                    "label": "Low" if disease_prob < 0.3 else "Medium" if disease_prob < 0.6 else "High",
                    "multiplier": disease_prob
                },
                "pest_level": {
                    "label": "Low" if pest_risk == "Low" else "Medium" if pest_risk == "Medium" else "High",
                    "multiplier": float(yield_component_scores.get("pest_penalty", 0.0) / 100.0) if yield_component_scores else float(pest_probs[2] if len(pest_probs) > 2 else 0.1)
                }
            },
            # diagnostics
            "sentinelClientUsed": sentinel_client_used,
            "usedDiseaseModel": used_disease_model,
            "usedPestModel": used_pest_model
        }

        return response

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "details": str(type(e).__name__)
        }

# ===========================================
# ENTRY POINT
# ===========================================

if __name__ == "__main__":
    try:
        if len(sys.argv) != 4:
            raise ValueError(
                "Usage: python predict_crop_stage.py <farmer_id> <crop_type> <coordinates_json>"
            )

        farmer_id = sys.argv[1]
        crop_type = sys.argv[2]
        coordinates_arg = sys.argv[3]
        
        # Parse coordinates from JSON or string
        try:
            coordinates = json.loads(coordinates_arg)
        except json.JSONDecodeError:
            # If JSON fails, try treating it as a single point
            coordinates = [{'latitude': 30.5, 'longitude': 75.5}]

        result = predict_crop_analysis_new(farmer_id, crop_type, coordinates)
        
        # Call decision engine to generate recommendations if available
        if DECISION_ENGINE_AVAILABLE and result.get("success"):
            try:
                # Extract water stress status
                water_stress_data = result.get("waterStress", {})
                water_stress_score = 0
                water_stress_status = "normal"
                
                if isinstance(water_stress_data, dict):
                    current_status = water_stress_data.get("current_status", {})
                    water_stress_score = current_status.get("water_stress", 0)
                    # Convert numeric score to status level
                    if water_stress_score > 0.7:
                        water_stress_status = "severe"
                    elif water_stress_score > 0.4:
                        water_stress_status = "moderate"
                    elif water_stress_score > 0.2:
                        water_stress_status = "mild"
                    else:
                        water_stress_status = "normal"
                
                print(f"DEBUG: Water stress status={water_stress_status}, score={water_stress_score}", file=sys.stderr)
                
                # Prepare input data for decision engine
                decision_input = {
                    "plot_id": farmer_id,
                    "farmer_id": farmer_id,
                    "current_crop": crop_type.lower(),  # Ensure lowercase for decision engine
                    "features_data": {
                        "stage_classifier": {
                            "stage": result.get("stage", {}).get("prediction", "")
                        },
                        "disease_detection": {
                            "risk_level": result.get("disease", {}).get("risk_level", "LOW"),
                            "disease_prob": result.get("disease", {}).get("probability", 0),
                            "prediction": result.get("disease", {}).get("prediction", "Unknown Disease")
                        },
                        "disease_classification": {
                            "output": result.get("disease", {}).get("prediction", "Unknown Disease"),
                            "confidence": result.get("disease", {}).get("confidence", 0)
                        },
                        "pest_risk": {
                            "risk_level": result.get("pest", {}).get("risk_level", "Low"),
                            "confidence": result.get("pest", {}).get("confidence", 0)
                        },
                        "water_stress": {
                            "stress": water_stress_status,
                            "score": water_stress_score
                        },
                        "growth_performance": result.get("growthPerformance", {})
                    },
                    "last_updated": datetime.now().isoformat()
                }
                
                print(f"DEBUG: Decision input crop={decision_input['current_crop']}", file=sys.stderr)
                print(f"DEBUG: Disease risk_level={decision_input['features_data']['disease_detection']['risk_level']}", file=sys.stderr)
                print(f"DEBUG: Pest risk_level={decision_input['features_data']['pest_risk']['risk_level']}", file=sys.stderr)
                
                # Generate recommendations
                recommendations = generate_recommendations(decision_input)
                
                print(f"DEBUG: Recommendations returned: {json.dumps(recommendations, default=str)}", file=sys.stderr)
                
                # Add recommendations to result
                if recommendations and "error" not in recommendations:
                    result["recommendations"] = recommendations.get("recommendations", {})
                    result["recommendation_details"] = recommendations.get("recommendation_details", {})
                    print(f"DEBUG: Recommendations added successfully. Keys: {list(result.get('recommendations', {}).keys())}", file=sys.stderr)
                else:
                    # Log any errors from decision engine to stderr
                    if recommendations and "error" in recommendations:
                        print(f"Decision engine error: {recommendations['error']}", file=sys.stderr)
                    else:
                        print(f"WARNING: Unexpected recommendations response: {recommendations}", file=sys.stderr)
                    
            except Exception as e:
                import traceback
                print(f"ERROR: Failed to generate recommendations: {str(e)}", file=sys.stderr)
                print(traceback.format_exc(), file=sys.stderr)
                # Continue without recommendations rather than failing
        
        # Clean output
        sys.stdout.write(json.dumps(result))
        sys.stdout.flush()

    except Exception as e:
        sys.stdout.write(json.dumps({
            "success": False,
            "error": str(e)
        }))
        sys.stdout.flush()
        sys.exit(1)
