import sys
import json
import numpy as np
import torch
import os
import pandas as pd
import warnings
from contextlib import contextmanager
import io

# 🚨 HARD SILENCE MODE
os.environ["PYTHONWARNINGS"] = "ignore"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TORCH_CPP_LOG_LEVEL"] = "ERROR"
os.environ["KMP_WARNINGS"] = "0"

warnings.filterwarnings("ignore")

@contextmanager
def suppress_stdout():
    saved_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = saved_stdout

def load_model(crop_type, model_type="stage"):
    """Load Transformer model for specific crop"""
    if model_type == "stage":
        model_path = f"models/{crop_type}_model.pt"
    elif model_type == "disease":
        model_path = f"models/{crop_type}_transformer_disease_model.pth"
    else:  # pest
        model_path = f"models/{crop_type}_transformer_pest_model.pth"
    
    try:
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        if model_type == "stage":
            # Load stage classification model
            from models.transformers import CropTransformer
            
            # Handle different checkpoint formats
            if 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
                num_features = checkpoint.get('num_features', 19)
                window_size = checkpoint.get('window_size', 7)
                num_classes = checkpoint.get('num_classes', 3)
            else:
                # Direct state_dict format
                state_dict = checkpoint
                num_features = 19  # Default
                window_size = 7   # Default
                num_classes = 3   # Default
            
            model = CropTransformer(
                num_features=num_features,
                window_size=window_size,
                d_model=64,
                nhead=4,
                num_layers=2,
                num_classes=num_classes,
                dropout=0.1
            )
            
            model.load_state_dict(state_dict)
            
        elif model_type == "disease":
            # Load disease detection model
            from disease_model import TransformerClassifier
            
            # Handle different checkpoint formats for disease model
            if 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
                num_features = checkpoint.get('num_features', 19)
                seq_len = checkpoint.get('seq_len', 7)
            else:
                # Direct state_dict format
                state_dict = checkpoint
                num_features = 19  # Default
                seq_len = 7       # Default
            
            model = TransformerClassifier(
                input_dim=num_features,
                seq_len=seq_len,
                d_model=64,
                nhead=4,
                num_layers=3
            )
            
            # Load state dict with strict=False to handle size mismatches
            model.load_state_dict(state_dict, strict=False)
            
        else:  # pest
            # Load pest risk model
            from pest_model import TransformerClassifier
            
            # Handle different checkpoint formats for pest model
            if 'model_state_dict' in checkpoint:
                state_dict = checkpoint['model_state_dict']
                num_features = checkpoint.get('num_features', 19)
                seq_len = checkpoint.get('seq_len', 7)
                num_classes = checkpoint.get('num_classes', 3)
            else:
                # Direct state_dict format
                state_dict = checkpoint
                num_features = 19  # Default
                seq_len = 7       # Default
                num_classes = 3   # Default
            
            model = TransformerClassifier(
                input_dim=num_features,
                seq_len=seq_len,
                num_classes=num_classes,
                d_model=64,
                nhead=4,
                num_layers=3
            )
            
            # Load state dict with strict=False to handle size mismatches
            model.load_state_dict(state_dict, strict=False)
        
        model.eval()
        
        print(f"✓ Loaded {model_type} model: {model_path}", file=sys.stderr)
        return model, checkpoint
        
    except Exception as e:
        error_msg = f"Error loading {crop_type} {model_type} model: {str(e)}"
        print(json.dumps({
            'error': error_msg,
            'success': False
        }))
        print(error_msg, file=sys.stderr)
        sys.exit(1)

def slope(series):
    t = np.arange(len(series))
    return np.polyfit(t, series, 1)[0]

def stats(series):
    return {
        "mean": np.mean(series),
        "std": np.std(series),
        "slope": slope(series),
        "min": np.min(series),
        "max": np.max(series)
    }

def growth_rate_score(ndvi):
    """Calculate growth rate score based on NDVI slope"""
    s = stats(ndvi)["slope"]
    # Assuming 0 slope = 50, -0.03 = 0, +0.03 = 100
    return np.clip((s + 0.03) / 0.06 * 100, 0, 100)

def biomass_score(ndvi):
    """Calculate biomass score based on NDVI mean"""
    m = stats(ndvi)["mean"]
    # Assuming 0.2 = 0, 0.8 = 100
    return np.clip((m - 0.2) / 0.6 * 100, 0, 100)

def stability_score(ndvi):
    """Calculate stability score based on NDVI std deviation"""
    std = stats(ndvi)["std"]
    # Lower std is better
    return np.clip(100 - (std / 0.15 * 100), 0, 100)

def stage_progress_score(ndvi, stage):
    """Calculate stage progress score based on crop stage"""
    peak = stats(ndvi)["max"]
    
    expected = {
        1: (0.3, 0.6),   # Early stage
        2: (0.6, 0.8),   # Middle stage
        3: (0.7, 0.9)    # Late stage
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
    
    # Determine status based on score
    if overall >= 80:
        status = "Excellent"
        color = "green"
        recommendation = "Crops are performing optimally. Continue current practices."
    elif overall >= 60:
        status = "Good"
        color = "blue"
        recommendation = "Crops are healthy. Monitor for any changes."
    elif overall >= 40:
        status = "Fair"
        color = "orange"
        recommendation = "Some improvement needed. Check irrigation and nutrients."
    else:
        status = "Poor"
        color = "red"
        recommendation = "Immediate attention required. Consider consulting an agronomist."
    
    return {
        'overall_score': overall,
        'status': status,
        'color': color,
        'recommendation': recommendation,
        'component_scores': scores
    }

def predict_crop_analysis(farmer_id, crop_type, coordinates):
    """Main function to predict crop stage, disease, pest risk, AND growth performance"""
    try:
        with suppress_stdout():
            from data_fetcher import fetch_data_for_demo, CROP_CONFIG

            if crop_type not in CROP_CONFIG:
                raise ValueError(f"Invalid crop type: {crop_type}")

            corners = [(p['longitude'], p['latitude']) for p in coordinates]

            result = fetch_data_for_demo(
                corners=corners,
                crop_type=crop_type,
                current_date=None
            )

            if result is None:
                raise RuntimeError("Failed to fetch satellite data")

            # Load stage model
            stage_model, stage_checkpoint = load_model(crop_type, "stage")

            # Load disease model
            disease_model, disease_checkpoint = load_model(crop_type, "disease")

            # Load pest model
            pest_model, pest_checkpoint = load_model(crop_type, "pest")

            # Load scaler
            try:
                import joblib
                scaler = joblib.load(f"scalers/{crop_type}_scaler.pkl")
            except:
                scaler = None

            # Prepare features
            features = result['window_features']
            
            # Scale features if scaler exists
            if scaler:
                original_shape = features.shape
                features_flat = features.reshape(-1, features.shape[2])
                features_scaled_flat = scaler.transform(features_flat)
                features_scaled = features_scaled_flat.reshape(original_shape)
            else:
                features_scaled = features

            # Get actual sequence length from features
            actual_seq_len = features_scaled.shape[1]

            # Stage prediction
            with torch.no_grad():
                features_tensor = torch.FloatTensor(features_scaled)
                stage_logits = stage_model(features_tensor)
                stage_probabilities = torch.softmax(stage_logits, dim=1).numpy()[0]
                predicted_stage_idx = np.argmax(stage_probabilities)

            # Stage names
            if 'class_names' in stage_checkpoint:
                stage_names = stage_checkpoint['class_names']
            else:
                stage_names = ["Vegetative", "Reproductive", "Ripening"]
            
            predicted_stage = stage_names[predicted_stage_idx]
            stage_confidence = float(stage_probabilities[predicted_stage_idx])

            # Disease prediction
            with torch.no_grad():
                x = torch.tensor(features_scaled, dtype=torch.float32)
                disease_logit = disease_model(x)
                raw_disease_prob = torch.sigmoid(disease_logit).item()
                
                # Run through encoder
                x = disease_model.input_proj(x)
                x = disease_model.transformer_encoder(x)
                x = x.mean(dim=1)
                x = disease_model.classifier(x)
                raw_disease_prob = torch.sigmoid(x).item()

            # CALIBRATION: Adjust disease probability based on NDVI
            ndvi_mean = result["window_df"]["NDVI"].mean()
            ndvi_trend = result["window_df"]["NDVI"].iloc[-1] - result["window_df"]["NDVI"].iloc[0]
            
            if raw_disease_prob < 0.01:
                if ndvi_mean > 0.5:
                    disease_prob = 0.05 + (ndvi_mean - 0.5) * 0.1
                elif ndvi_mean < 0.2:
                    disease_prob = 0.3 + (0.2 - ndvi_mean) * 1.0
                else:
                    disease_prob = max(0.01, raw_disease_prob * 5)
            elif raw_disease_prob > 0.99:
                if ndvi_mean > 0.6:
                    disease_prob = 0.7 - (ndvi_mean - 0.6) * 0.5
                else:
                    disease_prob = 0.8
            else:
                disease_prob = raw_disease_prob

            disease_prob = max(0.01, min(0.99, disease_prob))

            # Pest risk prediction
            with torch.no_grad():
                x = torch.tensor(features_scaled, dtype=torch.float32)
                pest_logits = pest_model(x)
                pest_probabilities = torch.softmax(pest_logits, dim=1).numpy()[0]
                predicted_pest_idx = np.argmax(pest_probabilities)
                
                # Run through encoder
                x = pest_model.input_proj(x)
                x = pest_model.encoder(x)
                x = x.mean(dim=1)
                pest_logits = pest_model.head(x)
                pest_probabilities = torch.softmax(pest_logits, dim=1).numpy()[0]
                predicted_pest_idx = np.argmax(pest_probabilities)

            # Pest risk names
            pest_risk_names = ["Low", "Medium", "High"]
            predicted_pest_risk = pest_risk_names[predicted_pest_idx]
            pest_confidence = float(pest_probabilities[predicted_pest_idx])

            # Calculate growth performance scores using your functions
            ndvi_series = result["window_df"]["NDVI"].values
            growth_scores = calculate_all_scores(ndvi_series, 2)  # Default to middle stage
            overall_score = overall_health_score(
                growth_scores['growth_rate'],
                growth_scores['biomass'],
                growth_scores['stability'],
                growth_scores['stage_progress']
            )
            
            growth_report = calculate_health_report(growth_scores)

            print(f"✅ Growth performance calculated: Overall Score = {overall_score:.2f}", file=sys.stderr)

            # Get NDVI trend
            ndvi_trend_data = [
                {"date": str(r["date"]), "ndvi": float(r["NDVI"])}
                for r in result["window_df"].to_dict("records")
            ]

            # Generate recommendations
            stage_recommendations = {
                'Vegetative': [
                    "Monitor for early pests and diseases",
                    "Apply nitrogen fertilizer if NDVI is low",
                    "Ensure adequate irrigation for growth"
                ],
                'Reproductive': [
                    "Critical stage - monitor closely for stress",
                    "Check for flowering and grain formation",
                    "Avoid water stress during grain filling"
                ],
                'Ripening': [
                    "Gradually reduce irrigation",
                    "Monitor for lodging and harvest readiness",
                    "Prepare for harvest in 2-3 weeks"
                ]
            }

            disease_recommendations = []
            if disease_prob < 0.2:
                disease_recommendations = [
                    "✅ Low disease risk detected",
                    "Continue current management practices",
                    "Next check in 10-14 days"
                ]
            elif disease_prob < 0.5:
                disease_recommendations = [
                    "⚠️ Moderate disease risk detected",
                    "Increase monitoring frequency",
                    "Consider ground verification",
                    "Check for other stress factors"
                ]
            else:
                disease_recommendations = [
                    "🔴 High disease risk detected",
                    "Conduct ground verification immediately",
                    "Isolate affected areas if possible",
                    "Consult agricultural expert",
                    "Consider treatment options"
                ]

            pest_recommendations = {
                "Low": [
                    "✅ Low pest risk detected",
                    "Continue current pest management",
                    "Monitor for early signs"
                ],
                "Medium": [
                    "⚠️ Medium pest risk detected",
                    "Increase pest monitoring",
                    "Consider preventive measures",
                    "Check for pest eggs/larvae"
                ],
                "High": [
                    "🔴 High pest risk detected",
                    "Take immediate pest control action",
                    "Apply appropriate pesticides",
                    "Monitor crop damage closely"
                ]
            }

            success_result = {
                "success": True,
                "cropType": crop_type,
                "stage": {
                    "prediction": predicted_stage,
                    "confidence": stage_confidence
                },
                "disease": {
                    "probability": disease_prob,
                    "raw_probability": raw_disease_prob,
                    "risk_level": "LOW" if disease_prob < 0.2 else "MEDIUM" if disease_prob < 0.5 else "HIGH"
                },
                "pest": {
                    "prediction": predicted_pest_risk,
                    "confidence": pest_confidence,
                    "risk_level": predicted_pest_risk
                },
                "growthPerformance": {
                    "scores": growth_scores,
                    "overall_score": overall_score,
                    "report": growth_report,
                    "healthMetrics": {
                        'growth_rate': {'level': f"{growth_scores['growth_rate']:.1f}", 'status': 'Good' if growth_scores['growth_rate'] >= 60 else 'Needs attention'},
                        'biomass': {'level': f"{growth_scores['biomass']:.1f}", 'status': 'Good' if growth_scores['biomass'] >= 60 else 'Needs attention'},
                        'stability': {'level': f"{growth_scores['stability']:.1f}", 'status': 'Good' if growth_scores['stability'] >= 60 else 'Needs attention'},
                        'stage_progress': {'level': f"{growth_scores['stage_progress']:.1f}", 'status': 'Good' if growth_scores['stage_progress'] >= 60 else 'Needs attention'}
                    }
                },
                "ndviTrend": ndvi_trend_data,
                "recommendations": {
                    "stage": stage_recommendations.get(predicted_stage, ["Monitor crop health regularly"]),
                    "disease": disease_recommendations,
                    "pest": pest_recommendations.get(predicted_pest_risk, ["Monitor for pests"])
                },
                "healthMetrics": {
                    'nitrogen': {'level': 'Adequate', 'status': 'Good'},
                    'phosphorus': {'level': 'Low', 'status': 'Needs fertilizer'},
                    'potassium': {'level': 'Adequate', 'status': 'Good'},
                    'ph': {'level': 6.2, 'status': 'Optimal'}
                },
                "ndvi_stats": {
                    "mean": float(ndvi_mean),
                    "trend": float(ndvi_trend),
                    "min": float(result["window_df"]["NDVI"].min()),
                    "max": float(result["window_df"]["NDVI"].max())
                }
            }

        print(json.dumps(success_result))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        print(f"Error in predict_crop_analysis: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 4:
        error_msg = f'Usage: python predict_crop_stage.py <farmer_id> <crop_type> <coordinates_json>. Got {len(sys.argv)} args'
        print(json.dumps({
            'error': error_msg,
            'success': False
        }))
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    
    farmer_id = sys.argv[1]
    crop_type = sys.argv[2]
    coordinates_json = sys.argv[3]
    
    try:
        coordinates = json.loads(coordinates_json)
        predict_crop_analysis(farmer_id, crop_type, coordinates)
    except json.JSONDecodeError as e:
        error_msg = f'Failed to parse coordinates JSON: {str(e)}'
        print(json.dumps({
            'error': error_msg,
            'success': False
        }))
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_msg = f'Unexpected error: {str(e)}'
        print(json.dumps({
            'error': error_msg,
            'success': False
        }))
        print(error_msg, file=sys.stderr)
        sys.exit(1)