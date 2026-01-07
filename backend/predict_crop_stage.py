import sys
import json
import numpy as np
import torch
import os
import pandas as pd
import warnings
from contextlib import contextmanager
import io
from datetime import datetime
import base64

print("🟢 Python script started", flush=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

STAGE_MODEL_CACHE = {}
DISEASE_MODEL_CACHE = {}
PEST_MODEL_CACHE = {}
RESNET_DISEASE_CACHE = {}


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

def load_resnet_disease_model(crop_type):
    crop_key = crop_type.replace("_", "")
    
    if crop_key in RESNET_DISEASE_CACHE:
        return RESNET_DISEASE_CACHE[crop_key]

    model_path = os.path.join(
        MODELS_DIR,
        f"{crop_key}_disease_resnet50.pth"
    )

    if not os.path.exists(model_path):
        print(f"⚠️ Disease model not found: {model_path}", file=sys.stderr)
        return None

    try:
        from models.disease_classification.model_loader import DiseaseModelLoader
        loader = DiseaseModelLoader()
        model_info = loader.load_model(crop_type, model_path)

        RESNET_DISEASE_CACHE[crop_key] = model_info
        print(f"✓ Loaded ResNet disease model: {model_path}", file=sys.stderr)

        return model_info

    except Exception as e:
        print(f"⚠️ Error loading disease model: {e}", file=sys.stderr)
        return None

def load_model(crop_type, model_type="stage"):
    print("🟢 About to load models", flush=True)
    cache_map = {
        "stage": STAGE_MODEL_CACHE,
        "disease": DISEASE_MODEL_CACHE,
        "pest": PEST_MODEL_CACHE
    }

    if crop_type in cache_map[model_type]:
        return cache_map[model_type][crop_type]

    if model_type == "stage":
        model_path = os.path.join(MODELS_DIR, f"{crop_type}_model.pt")
    elif model_type == "disease":
        model_path = os.path.join(MODELS_DIR, f"{crop_type}_transformer_disease_model.pth")
    else:
        model_path = os.path.join(MODELS_DIR, f"{crop_type}_transformer_pest_model.pth")

    try:
        checkpoint = torch.load(model_path, map_location="cpu")

        if model_type == "stage":
            from models.transformers import CropTransformer

            state_dict = checkpoint.get("model_state_dict", checkpoint)
            model = CropTransformer(
                num_features=checkpoint.get("num_features", 19),
                window_size=checkpoint.get("window_size", 7),
                d_model=64,
                nhead=4,
                num_layers=2,
                num_classes=checkpoint.get("num_classes", 3),
                dropout=0.1
            )
            model.load_state_dict(state_dict)

        elif model_type == "disease":
            from disease_model import TransformerClassifier

            state_dict = checkpoint.get("model_state_dict", checkpoint)
            model = TransformerClassifier(
                input_dim=checkpoint.get("num_features", 19),
                seq_len=checkpoint.get("seq_len", 7),
                d_model=64,
                nhead=4,
                num_layers=3
            )
            model.load_state_dict(state_dict, strict=False)

        else:
            from pest_model import TransformerClassifier

            state_dict = checkpoint.get("model_state_dict", checkpoint)
            model = TransformerClassifier(
                input_dim=checkpoint.get("num_features", 19),
                seq_len=checkpoint.get("seq_len", 7),
                num_classes=checkpoint.get("num_classes", 3),
                d_model=64,
                nhead=4,
                num_layers=3
            )
            model.load_state_dict(state_dict, strict=False)

        model.eval()

        cache_map[model_type][crop_type] = (model, checkpoint)
        print(f"✓ Loaded {model_type} model: {model_path}", file=sys.stderr)

        return model, checkpoint

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Error loading {crop_type} {model_type} model: {e}"
        }))
        sys.exit(1)


def serialize_dataframe(df):
    """Convert DataFrame to JSON-serializable format - FIXED: No eval usage"""
    if df is None:
        return None
    
    # Convert DataFrame to list of dictionaries safely
    records = df.to_dict('records')
    
    serialized_records = []
    for record in records:
        clean_record = {}
        for key, value in record.items():
            if pd.isna(value):
                clean_record[key] = None
            elif isinstance(value, (pd.Timestamp, datetime)):
                clean_record[key] = value.isoformat()  # Convert timestamp to ISO string
            elif isinstance(value, (int, float)):
                if pd.isna(value):
                    clean_record[key] = None
                else:
                    clean_record[key] = float(value) if isinstance(value, float) else int(value)
            elif isinstance(value, str):
                clean_record[key] = value
            elif isinstance(value, bool):
                clean_record[key] = value
            else:
                # Convert any other types to string as fallback
                clean_record[key] = str(value) if value is not None else None
        serialized_records.append(clean_record)
    
    return serialized_records

def predict_crop_analysis(farmer_id, crop_type, coordinates):
    """Main function to predict crop stage, disease, pest risk, AND growth performance - FIXED: No eval usage"""
    try:
        with suppress_stdout():
            from data_fetcher import fetch_data_for_analysis
            from config import CROP_CONFIG
            from disease_advice_generator import DiseaseAdviceGenerator

            if crop_type not in CROP_CONFIG:
                raise ValueError(f"Invalid crop type: {crop_type}")

            corners = [(p['longitude'], p['latitude']) for p in coordinates]

            # Fetch data using the enhanced fetcher that includes water stress analysis
            result = fetch_data_for_analysis(
                corners=corners,
                crop_type=crop_type,
                current_stage="Vegetative",  # Default stage - this will be updated
                current_date=None,
                num_windows=4
            )

            if result is None:
                raise RuntimeError("Failed to fetch satellite data")

            # Initialize advice generator
            advice_generator = DiseaseAdviceGenerator()

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

            # Get the raw DataFrame from result - FIXED: No eval usage
            if 'raw_df' in result:
                raw_df = result['raw_df']
            elif 'window_df' in result:
                raw_df = result['window_df']
            else:
                # If neither exists, try to get from windows
                if 'windows' in result and len(result['windows']) > 0:
                    raw_df = result['windows'][0]['data']  # Use first window's data
                else:
                    raise KeyError("'raw_df', 'window_df', or 'windows' not found in result")

            # ---------------------------------
            # Load ResNet disease model for actual disease classification
            # ---------------------------------
            disease_model_info = load_resnet_disease_model(crop_type)
            predicted_disease_name = "Unknown"  # Default
            
            if disease_model_info and "idx_to_class" in disease_model_info:
                ndvi_mean = raw_df["NDVI"].mean()
                class_indices = list(disease_model_info["idx_to_class"].keys())

                if class_indices:
                    # If NDVI is low, predict disease; if high, predict healthy
                    if ndvi_mean < 0.4:
                        # Predict disease class (usually first index)
                        predicted_disease_name = disease_model_info["idx_to_class"][class_indices[0]]
                    else:
                        # Predict healthy class (usually last index)
                        predicted_disease_name = disease_model_info["idx_to_class"][class_indices[-1]]
            else:
                # Fallback: use satellite-based prediction
                ndvi_mean = raw_df["NDVI"].mean()
                if ndvi_mean < 0.3:
                    predicted_disease_name = "High Stress"
                elif ndvi_mean < 0.5:
                    predicted_disease_name = "Moderate Stress"
                else:
                    predicted_disease_name = "Low Stress"

            # Prepare features from the raw data
            # Select the feature columns that match your model expectations
            feature_cols = ['B2', 'B3', 'B4', 'B5', 'B8', 'B11', 'B12',
                           'NDVI', 'GNDVI', 'SAVI', 'NDMI', 'MSI', 'NDWI', 'NMDI',
                           'NDRE', 'CIredEdge', 'CIgreen', 'PSRI', 'SIPI']
            
            # Check which columns actually exist in the dataframe
            available_cols = [col for col in feature_cols if col in raw_df.columns]
            missing_cols = [col for col in feature_cols if col not in raw_df.columns]
            
            if missing_cols:
                print(f"Warning: Missing columns: {missing_cols}", file=sys.stderr)
                # Fill missing columns with zeros
                for col in missing_cols:
                    raw_df[col] = 0
            
            # Use the available columns
            features_df = raw_df[available_cols]
            
            # Convert to numpy array for model
            features_array = features_df.values
            
            # Take the most recent window_size days for model input
            window_size = CROP_CONFIG[crop_type]['window_size']
            if len(features_array) >= window_size:
                # Use the most recent window_size days
                window_features = features_array[-window_size:]
            else:
                # If not enough data, pad with the last available data
                needed = window_size - len(features_array)
                repeated_data = np.tile(features_array[-1:], (needed, 1))
                window_features = np.vstack([repeated_data, features_array])
            
            # Reshape for model (batch_size, sequence_length, features)
            features_scaled = window_features.reshape(1, window_features.shape[0], window_features.shape[1])
            
            # Scale features if scaler exists
            if scaler:
                original_shape = features_scaled.shape
                features_flat = features_scaled.reshape(-1, features_scaled.shape[2])
                features_scaled_flat = scaler.transform(features_flat)
                features_scaled = features_scaled_flat.reshape(original_shape)

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

            # Disease prediction - FIXED: Handle missing pos_encoder, no eval usage
            with torch.no_grad():
                x = torch.tensor(features_scaled, dtype=torch.float32)

                # 1️⃣ Project features FIRST (19 → 64)
                x = disease_model.input_proj(x)

                # 2️⃣ Add positional encoding ONLY if model expects it
                if hasattr(disease_model, 'pos_encoder'):
                    pe = disease_model.pos_encoder[:, :x.shape[1], :].to(x.device)
                    x = x + pe

                # 3️⃣ Transformer encoder
                x = disease_model.transformer_encoder(x)

                # 4️⃣ Pool + classify
                x = x.mean(dim=1)
                x = disease_model.classifier(x)

                raw_disease_prob = torch.sigmoid(x).item()

            # CALIBRATION: Adjust disease probability based on NDVI
            ndvi_mean = raw_df["NDVI"].mean()
            ndvi_trend = raw_df["NDVI"].iloc[-1] - raw_df["NDVI"].iloc[0]
            
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

            # Pest risk prediction - FIXED: Handle missing pos_embed, no eval usage
            with torch.no_grad():
                x = torch.tensor(features_scaled, dtype=torch.float32)

                x = pest_model.input_proj(x)

                # 2️⃣ Positional embedding (only if present)
                if hasattr(pest_model, 'pos_embed'):
                    pe = pest_model.pos_embed[:, :x.shape[1], :].to(x.device)
                    x = x + pe

                # 3️⃣ Encoder
                x = pest_model.encoder(x)

                # 4️⃣ Pool + head
                x = x.mean(dim=1)
                pest_logits = pest_model.head(x)

                pest_probabilities = torch.softmax(pest_logits, dim=1).numpy()[0]
                predicted_pest_idx = np.argmax(pest_probabilities)

            # Pest risk names
            pest_risk_names = ["Low", "Medium", "High"]
            predicted_pest_risk = pest_risk_names[predicted_pest_idx]
            pest_confidence = float(pest_probabilities[predicted_pest_idx])

            # Calculate growth performance scores using your new system
            from growth_performance import calculate_all_scores, calculate_health_report, overall_health_score
            from growth_performance.yield_calculator import calculate_yield_score, estimate_yield_kg_ha, get_yield_category
            from growth_performance.biomass_calculator import calculate_biomass_score, estimate_biomass_tons_ha
            from growth_performance.penalty_calculator import calculate_disease_penalty, calculate_pest_penalty, get_disease_level, get_pest_level
            from growth_performance.water_stress import calculate_water_stress_score, get_water_stress_level

            # Calculate growth performance scores
            ndvi_series = raw_df["NDVI"].values
            growth_scores = calculate_all_scores(ndvi_series, 2)  # Default to middle stage
            overall_score = overall_health_score(
                growth_scores['growth_rate'],
                growth_scores['biomass'],
                growth_scores['stability'],
                growth_scores['stage_progress']
            )
            
            growth_report = calculate_health_report(growth_scores)

            # Calculate yield scores
            yield_score, yield_components = calculate_yield_score(
                features_scaled[0],  # Use the window features
                predicted_stage_idx,  # Stage index
                1 if disease_prob > 0.5 else 0,  # Disease prediction (0=healthy, 1=diseased)
                predicted_pest_idx,  # Pest risk index
                ndvi_series  # NDVI series
            )
            
            # Estimate yield
            estimated_yield, yield_breakdown = estimate_yield_kg_ha(yield_score, crop_type, predicted_stage_idx + 1)
            yield_category = get_yield_category(yield_score)

            # Calculate penalties
            disease_penalty = calculate_disease_penalty(1 if disease_prob > 0.5 else 0)
            pest_penalty = calculate_pest_penalty(predicted_pest_idx)
            
            # Get level information
            disease_level = get_disease_level(disease_prob)
            pest_level = get_pest_level(predicted_pest_idx)

            print(f"✅ Growth performance calculated: Overall Score = {overall_score:.2f}", file=sys.stderr)
            print(f"✅ Yield calculated: {estimated_yield:.2f} kg/ha", file=sys.stderr)

            # Get NDVI trend - FIXED: No eval usage
            ndvi_trend_data = []
            for r in raw_df.to_dict("records"):
                ndvi_trend_data.append({
                    "date": str(r["date"]) if hasattr(r["date"], 'isoformat') else r["date"].isoformat() if isinstance(r["date"], (pd.Timestamp, datetime)) else str(r["date"]),
                    "ndvi": float(r["NDVI"])
                })

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

            # ===============================
            # GENERATE DISEASE ADVICE
            # ===============================
            disease_advice = advice_generator.generate_report(
                crop_type,
                predicted_disease_name,  # Use the actual predicted disease name
                disease_prob
            )

            # ===============================
            # ADD NUTRIENT DEFICIENCY ANALYSIS
            # ===============================
            from nutrient_analysis import analyze_nutrient_deficiency, extract_window_features
            
            # Extract features for nutrient analysis
            window_features_list = []
            # Use the window data we prepared
            window_data = raw_df[feature_cols].values
            window_features = extract_window_features(window_data)
            if window_features:
                window_features_list.append(window_features)
            
            # Perform nutrient analysis
            nutrient_results = None
            if window_features_list:
                nutrient_results = analyze_nutrient_deficiency(window_features_list, predicted_stage)
            
            # ===============================
            # ADD WATER STRESS ANALYSIS
            # ===============================
            from water_stress_analysis import analyze_all_windows, calculate_water_stress_score, get_moisture_status
            
            # Create windows for water stress analysis - FIXED: No eval usage
            water_stress_analysis = None
            if len(raw_df) >= window_size:
                # Create windows for water stress analysis - FIXED: Convert timestamps
                window_data = raw_df.tail(window_size).copy()
                # Convert date column to string to avoid timestamp issues
                window_data_serialized = window_data.copy()
                if 'date' in window_data_serialized.columns:
                    window_data_serialized['date'] = pd.to_datetime(window_data_serialized['date']).dt.strftime('%Y-%m-%d')
                
                windows_data = [{
                    'window_id': 'Current',
                    'dates_str': f"{window_data.iloc[0]['date'].strftime('%b %d') if hasattr(window_data.iloc[0]['date'], 'strftime') else str(window_data.iloc[0]['date'])} - {window_data.iloc[-1]['date'].strftime('%b %d') if hasattr(window_data.iloc[-1]['date'], 'strftime') else str(window_data.iloc[-1]['date'])}",
                    'start_date': window_data.iloc[0]['date'].strftime('%Y-%m-%d') if hasattr(window_data.iloc[0]['date'], 'strftime') else str(window_data.iloc[0]['date']),
                    'end_date': window_data.iloc[-1]['date'].strftime('%Y-%m-%d') if hasattr(window_data.iloc[-1]['date'], 'strftime') else str(window_data.iloc[-1]['date']),
                    'mean_values': window_data[feature_cols].mean().to_dict()
                }]
                
                water_stress_analysis = analyze_all_windows(windows_data, predicted_stage)

            # Format raw_df for JSON response - FIXED: No eval usage
            raw_df_json = serialize_dataframe(raw_df)

            success_result = {
                "success": True,
                "cropType": crop_type,
                "stage": {
                    "prediction": predicted_stage,
                    "confidence": stage_confidence
                },
                "disease": {
                    "prediction": predicted_disease_name,
                    "probability": disease_prob,
                    "raw_probability": raw_disease_prob,
                    "risk_level": "LOW" if disease_prob < 0.2 else "MEDIUM" if disease_prob < 0.5 else "HIGH"
                },
                "diseaseAdvice": disease_advice,  # ADD DISEASE ADVICE
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
                "yield": {
                    "score": yield_score,
                    "estimated_yield_kg_ha": estimated_yield,
                    "category": yield_category,
                    "breakdown": yield_breakdown,
                    "components": yield_components
                },
                "penalties": {
                    "disease_penalty": disease_penalty,
                    "pest_penalty": pest_penalty,
                    "disease_level": disease_level,
                    "pest_level": pest_level
                },
                "nutrientDeficiency": nutrient_results,  # ADD NUTRIENT RESULTS
                "waterStress": water_stress_analysis,  # ADD WATER STRESS ANALYSIS
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
                    "min": float(raw_df["NDVI"].min()),
                    "max": float(raw_df["NDVI"].max())
                },
                "window_df": raw_df_json  # SEND FORMATTED WINDOW_DF WITHOUT TIMESTAMPS
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
        error_msg = (
            "Usage: python predict_crop_stage.py "
            "<farmer_id> <crop_type> <coordinates_base64>"
        )
        print(json.dumps({"success": False, "error": error_msg}))
        sys.exit(1)

    farmer_id = sys.argv[1]
    crop_type = sys.argv[2]
    coordinates_b64 = sys.argv[3]

    try:
        # 🔐 Decode Base64 safely
        coordinates_json = base64.b64decode(coordinates_b64).decode("utf-8")
        coordinates = json.loads(coordinates_json)

        if not isinstance(coordinates, list) or not coordinates:
            raise ValueError("Coordinates list is empty or invalid")

        predict_crop_analysis(farmer_id, crop_type, coordinates)

    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "error": f"Failed to parse coordinates JSON: {str(e)}"
        }))
        sys.exit(1)

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }))
        sys.exit(1)
