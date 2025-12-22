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

def load_model(crop_type):
    """Load Transformer model for specific crop"""
    model_path = f"models/{crop_type}_model.pt"
    
    try:
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        # Get model parameters
        num_features = checkpoint.get('num_features', 19)
        window_size = checkpoint.get('window_size', 7)
        
        # Create TRANSFORMER model
        from models.transformers import CropTransformer
        model = CropTransformer(
            num_features=num_features,
            window_size=window_size,
            d_model=64,
            nhead=4,
            num_layers=2,
            num_classes=checkpoint.get("num_classes", 3),
            dropout=0.1
        )
        
        model.load_state_dict(checkpoint['model_state_dict'])
        model.eval()
        
        print(f"✓ Loaded {crop_type} model: {model_path}", file=sys.stderr)  # ✅ To stderr
        return model, checkpoint
        
    except Exception as e:
        error_msg = f"Error loading {crop_type} model: {str(e)}"
        print(json.dumps({
            'error': error_msg,
            'success': False
        }))
        print(error_msg, file=sys.stderr)  # ✅ To stderr
        sys.exit(1)

def predict_crop_stage(farmer_id, crop_type, coordinates):
    try:
        with suppress_stdout():  # 🚨 SUPPRESS ALL OUTPUT FROM DATA_FETCHER
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

            model, checkpoint = load_model(crop_type)

            with torch.no_grad():
                features_tensor = torch.FloatTensor(result['window_features'])
                logits = model(features_tensor)
                probabilities = torch.softmax(logits, dim=1).numpy()[0]

            predicted_stage_idx = int(np.argmax(probabilities))

            stage_names = checkpoint.get(
                "class_names",
                ["Vegetative", "Reproductive", "Ripening"]
            )

            predicted_stage = stage_names[predicted_stage_idx]
            confidence = float(probabilities[predicted_stage_idx])

            ndvi_trend = [
                {"date": str(r["date"]), "ndvi": float(r["NDVI"])}
                for r in result["window_df"].to_dict("records")
            ]

            recommendations = {
                "Vegetative": [
                    "Monitor for early pests and diseases",
                    "Apply nitrogen fertilizer if NDVI is low",
                    "Ensure adequate irrigation for growth"
                ],
                "Reproductive": [
                    "Critical stage - monitor closely for stress",
                    "Check for flowering and grain formation",
                    "Avoid water stress during grain filling"
                ],
                "Ripening": [
                    "Gradually reduce irrigation",
                    "Monitor for lodging and harvest readiness",
                    "Prepare for harvest in 2-3 weeks"
                ]
            }

            success_result = {
                "success": True,
                "cropType": crop_type,
                "stage": predicted_stage,
                "confidence": confidence,
                "ndviTrend": ndvi_trend,
                "recommendations": recommendations.get(predicted_stage, ["Monitor crop health regularly"]),
                "healthMetrics": {
                    'nitrogen': {'level': 'Adequate', 'status': 'Good'},
                    'phosphorus': {'level': 'Low', 'status': 'Needs fertilizer'},
                    'potassium': {'level': 'Adequate', 'status': 'Good'},
                    'ph': {'level': 6.2, 'status': 'Optimal'}
                }
            }

        # ✅ ONLY JSON EVER HITS STDOUT
        print(json.dumps(success_result))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }))
        print(f"Error in predict_crop_stage: {str(e)}", file=sys.stderr)  # ✅ To stderr
        sys.exit(1)

if __name__ == "__main__":
    # Read input from command line arguments
    if len(sys.argv) != 4:
        error_msg = f'Usage: python predict_crop_stage.py <farmer_id> <crop_type> <coordinates_json>. Got {len(sys.argv)} args'
        print(json.dumps({
            'error': error_msg,
            'success': False
        }))
        print(error_msg, file=sys.stderr)  # ✅ To stderr
        sys.exit(1)
    
    farmer_id = sys.argv[1]
    crop_type = sys.argv[2]
    coordinates_json = sys.argv[3]
    
    try:
        coordinates = json.loads(coordinates_json)
        predict_crop_stage(farmer_id, crop_type, coordinates)
    except json.JSONDecodeError as e:
        error_msg = f'Failed to parse coordinates JSON: {str(e)}'
        print(json.dumps({
            'error': error_msg,
            'success': False
        }))
        print(error_msg, file=sys.stderr)  # ✅ To stderr
        sys.exit(1)
    except Exception as e:
        error_msg = f'Unexpected error: {str(e)}'
        print(json.dumps({
            'error': error_msg,
            'success': False
        }))
        print(error_msg, file=sys.stderr)  # ✅ To stderr
        sys.exit(1)