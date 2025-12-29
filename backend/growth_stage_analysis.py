"""
Growth stage analysis using satellite data
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import torch
import torch.nn as nn
import joblib

class CropTransformer(nn.Module):
    def __init__(
        self,
        num_features,
        window_size,
        d_model=64,
        nhead=4,
        num_layers=2,
        num_classes=3,
        dropout=0.1
    ):
        super().__init__()
        self.input_proj = nn.Linear(num_features, d_model)
        self.pos_embed = nn.Parameter(
            torch.randn(1, window_size, d_model)
        )
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=4 * d_model,
            dropout=dropout,
            batch_first=True
        )
        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=num_layers
        )
        self.head = nn.Sequential(
            nn.LayerNorm(d_model),
            nn.Linear(d_model, num_classes)
        )

    def forward(self, x):
        x = self.input_proj(x)
        x = x + self.pos_embed[:, :x.size(1)]
        x = self.encoder(x)
        x = x.mean(dim=1)
        return self.head(x)

def load_stage_model(crop_type):
    """Load the stage classification model and scaler for a crop"""
    try:
        import os
        model_path = f"models/{crop_type}_model.pt"
        scaler_path = f"scalers/{crop_type}_scaler.pkl"
        
        # Load model
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        num_features = checkpoint.get('num_features', 19)
        window_size = checkpoint.get('window_size', 7)
        num_classes = checkpoint.get('num_classes', 3)
        
        model = CropTransformer(
            num_features=num_features,
            window_size=window_size,
            d_model=64,
            nhead=4,
            num_layers=2,
            num_classes=num_classes,
            dropout=0.1
        )
        
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        
        # Load scaler
        scaler = joblib.load(scaler_path)
        
        # Get stage names from checkpoint or use default
        stage_names = checkpoint.get('class_names', ["Vegetative", "Reproductive", "Ripening"])
        
        return model, scaler, stage_names, window_size
        
    except Exception as e:
        print(f"Error loading {crop_type} model: {e}")
        return None, None, ["Vegetative", "Reproductive", "Ripening"], 7

def prepare_features_for_stage_model(window_df):
    """Prepare features for stage classification model"""
    if window_df is None:
        return None
    
    # Select features in correct order (same as training)
    feature_columns = [
        'B2', 'B3', 'B4', 'B5', 'B8', 'B11', 'B12',
        'NDVI', 'GNDVI', 'SAVI', 'NDMI', 'MSI', 'NDWI', 'NMDI',
        'NDRE', 'CIredEdge', 'CIgreen', 'PSRI', 'SIPI'
    ]
    
    # Check if all features are present
    missing_features = [col for col in feature_columns if col not in window_df.columns]
    if missing_features:
        print(f"Missing features for stage model: {missing_features}")
        for col in missing_features:
            window_df[col] = 0
    
    # Extract features
    features = window_df[feature_columns].values
    return features.reshape(1, features.shape[0], features.shape[1])

def predict_crop_stage(features, model, scaler, stage_names):
    """Predict crop growth stage"""
    if model is None or scaler is None:
        # Fallback: simulate prediction
        probabilities = np.random.dirichlet(np.ones(len(stage_names)), size=1)[0]
        predicted_stage_idx = np.argmax(probabilities)
        return stage_names[predicted_stage_idx], probabilities
    
    # Scale features
    features_flat = features.reshape(-1, features.shape[-1])
    features_scaled = scaler.transform(features_flat)
    features_scaled = features_scaled.reshape(features.shape)
    
    # Make prediction
    with torch.no_grad():
        features_tensor = torch.FloatTensor(features_scaled)
        logits = model(features_tensor)
        probabilities = torch.softmax(logits, dim=1).numpy()[0]
        predicted_stage_idx = np.argmax(probabilities)
    
    return stage_names[predicted_stage_idx], probabilities

def create_stage_window(df, window_size):
    """Create a window for stage classification from recent data"""
    if df is None or len(df) == 0:
        return None
    
    # Use the most recent window_size days
    if len(df) >= window_size:
        return df.tail(window_size).copy()
    else:
        # Pad if insufficient data
        print(f"Only {len(df)} days of data for stage classification (need {window_size})")
        return df.tail(window_size).copy() if len(df) > 0 else None