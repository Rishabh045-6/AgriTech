# decision_engine.py
import json
import sys
import os
from datetime import datetime
import traceback # For better error reporting

# Redirect print to stderr for debugging (don't pollute stdout which must be JSON only)
def debug_print(*args, **kwargs):
    """Print to stderr for debugging without polluting JSON output."""
    print(*args, file=sys.stderr, **kwargs)

# --- Import Configuration and Conflict Resolver ---
# IMPORTANT: Ensure 'config.py' and 'conflict_resolver.py' are in the same directory as this script
# or adjust the path accordingly using sys.path.append(...)
try:
    from config import CROP_DOCS_PATH, SUPPORTED_CROPS, FEATURE_TO_SECTION, NUTRIENT_SECTIONS, STAGE_MAPPING, VALIDITY_WINDOWS, SATELLITE_REVISIT_DAYS, TIME_SENSITIVE_KEYWORDS
    CONFLICT_RESOLVER_AVAILABLE = True
    try:
        from conflict_resolver import resolver
    except ImportError:
        CONFLICT_RESOLVER_AVAILABLE = False
        debug_print("[WARNING] Conflict resolver not available. Running in basic mode.")
    debug_print("[OK] Config imported successfully")
except ImportError as e:
    debug_print(f"[ERROR] Error importing config or conflict_resolver: {e}")
    debug_print("Please ensure 'config.py' and 'conflict_resolver.py' are in the same directory as 'decision_engine.py'")
    # Exit gracefully or provide fallback values if possible
    SUPPORTED_CROPS = []
    CROP_DOCS_PATH = "./crop_docs/" # Example fallback
    CONFLICT_RESOLVER_AVAILABLE = False
    # Define other fallbacks as needed

# --- Helper Functions (Adjusted for Backend) ---
def load_json_file(file_path):
    """Load JSON file with error handling."""
    if not os.path.exists(file_path):
        debug_print(f"[ERROR] File not found: {file_path}")
        return None

    encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'ascii']
    last_error = None

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
                data = json.loads(content)
                return data
        except UnicodeDecodeError as e:
            last_error = f"Unicode decode error with {encoding}: {str(e)}"
        except json.JSONDecodeError as e:
            last_error = f"JSON parse error with {encoding}: {str(e)}"
            return None # Return None if JSON is invalid
        except Exception as e:
            last_error = f"Error with {encoding}: {str(e)}"

    # Last resort: read as binary and decode with error replacement
    try:
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='replace')
            content = content.replace('\ufffd', ' ')
            data = json.loads(content)
            debug_print(f"[WARNING] Loaded {file_path} with error replacement")
            return data
    except Exception as e:
        debug_print(f"[ERROR] Failed to load {file_path} after all attempts. Last error: {last_error}")
        return None

def get_standardized_stage(stage_from_data):
    if not stage_from_data:
        return None
    stage_lower = stage_from_data.lower()
    return STAGE_MAPPING.get(stage_lower, stage_lower)

def get_recommendation_for_feature(crop_doc, feature_name, risk_level, crop_stage=None):
    if feature_name not in FEATURE_TO_SECTION:
        return None

    section_name = FEATURE_TO_SECTION[feature_name]
    if section_name not in crop_doc:
        return None

    section_data = crop_doc[section_name]
    risk_level_lower = risk_level.lower().replace("_", " ")

    for level_data in section_data.get("levels", []):
        level_name = level_data.get("level", "").lower()
        if (level_name in risk_level_lower or risk_level_lower in level_name or
            any(word in risk_level_lower for word in level_name.split()) or
            any(word in level_name for word in risk_level_lower.split())):
            recommendations = level_data.get("recommendations", {})
            if crop_stage and crop_stage in recommendations:
                return recommendations[crop_stage]
            return recommendations.get("general", recommendations.get("all_stages", "No specific advice available."))

    return None

def get_nutrient_recommendation(crop_doc, nutrient_name, deficiency_level, crop_stage=None):
    if nutrient_name not in NUTRIENT_SECTIONS:
        return None

    section_name = NUTRIENT_SECTIONS[nutrient_name]
    if section_name not in crop_doc:
        return None

    section_data = crop_doc[section_name]
    deficiency_lower = deficiency_level.lower().replace("_", " ")

    for level_data in section_data.get("levels", []):
        level_name = level_data.get("level", "").lower()
        if (level_name in deficiency_lower or deficiency_lower in level_name or
            any(word in deficiency_lower for word in level_name.split()) or
            any(word in level_name for word in deficiency_lower.split())):
            recommendations = level_data.get("recommendations", {})
            if crop_stage and crop_stage in recommendations:
                return recommendations[crop_stage]
            return recommendations.get("general", "No specific advice available.")

    return None

def get_days_since_update(last_updated_str):
    """Calculate days since last satellite observation."""
    try:
        if not last_updated_str:  # Handle None, empty string, or null
            return 0
        # Accept both date-only and ISO datetime payloads.
        if isinstance(last_updated_str, str):
            try:
                update_date = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
            except ValueError:
                update_date = datetime.strptime(last_updated_str, "%Y-%m-%d")
        else:
            return 0
        current_date = datetime.now()
        days_diff = (current_date - update_date).days
        return max(0, days_diff)
    except (ValueError, TypeError):
        debug_print(f"[WARNING] Could not parse date: {last_updated_str}")
        return 0 # Default if parsing fails

def add_validity_qualifier(recommendation, feature, level, days_since_update):
    """Add time qualification to recommendations."""
    validity_days = VALIDITY_WINDOWS.get(feature, {}).get(level, SATELLITE_REVISIT_DAYS)
    if days_since_update > validity_days:
        qualifier = f"[NOTE] This advice is based on observations from {days_since_update} days ago. Conditions may have changed. Please verify field conditions."
        return f"{qualifier}\n\n{recommendation}"
    if days_since_update > 0:
        observation_note = f"[INFO] Latest observation: {days_since_update} day(s) ago\n\n"
        return f"{observation_note}{recommendation}"
    return recommendation

def qualify_time_sensitive_language(text, days_since_update):
    """Qualify time-sensitive phrases in recommendations."""
    if days_since_update >= 3:
        replacements = {
            "irrigate immediately": f"if no irrigation in last {days_since_update} days, irrigate",
            "apply immediately": f"consider applying if still needed",
            "urgent irrigation": f"irrigation may be needed if dry conditions persist",
            "immediate action": f"prompt action may be needed",
            "within 1-2 days": f"in the coming days if conditions haven't improved",
            "within 24 hours": f"as soon as practical if issue persists"
        }
        for old, new in replacements.items():
            if old.lower() in text.lower():
                text = text.replace(old, new)
                text = text.replace(old.capitalize(), new.capitalize())
    return text

def format_risk_level(risk_level):
    risk_emojis = {
        "low": "🟢", "medium": "🟡", "high": "🔴", "optimal": "🟢",
        "mild": "🟡", "moderate": "🟠", "severe": "🔴", "possible": "🟡", "adequate": "🟢"
    }
    base_level = risk_level.lower()
    emoji = next((v for k, v in risk_emojis.items() if k in base_level), "⚪")
    display_name = risk_level.upper().replace('_', ' ')
    return f"{emoji} {display_name}"

def get_disease_name(features_data):
    disease_class = features_data.get("disease_classification", {})
    if disease_class.get("output"):
        return disease_class.get("output")

    disease_detection = features_data.get("disease_detection", {})
    if disease_detection.get("prediction"):
        return disease_detection.get("prediction")
    if disease_detection.get("disease_name"):
        return disease_detection.get("disease_name")

    return "Unknown Disease"

def get_priority_badge_text(priority_level):
    """Get plain text for priority."""
    priority_texts = {1: "CRITICAL", 2: "HIGH", 3: "MEDIUM", 4: "ADVISORY"}
    return priority_texts.get(priority_level, "UNKNOWN")

def collect_all_recommendations(plot_data, crop_doc, current_stage):
    features_data = plot_data.get("features_data", {})
    all_recommendations = {}
    recommendation_details = {}
    individual_nutrients = {}

    # Disease Risk
    disease_data = features_data.get("disease_detection", {})
    if disease_data:
        risk_level = disease_data.get("risk_level", "").lower()
        if risk_level:
            rec = get_recommendation_for_feature(crop_doc, "disease_detection", risk_level, current_stage)
            if rec:
                all_recommendations["disease_detection"] = rec
                recommendation_details["disease_detection"] = {
                    "level": risk_level,
                    "probability": disease_data.get("disease_prob", 0),
                    "disease_name": get_disease_name(features_data)
                }

    # Pest Risk
    pest_data = features_data.get("pest_risk", {})
    if pest_data:
        risk_level = pest_data.get("risk_level", "").lower()
        if risk_level:
            rec = get_recommendation_for_feature(crop_doc, "pest_risk", risk_level, current_stage)
            if rec:
                all_recommendations["pest_risk"] = rec
                recommendation_details["pest_risk"] = {
                    "level": risk_level,
                    "confidence": pest_data.get("confidence", 0)
                }

    # Water Stress
    water_data = features_data.get("water_stress", {})
    if water_data:
        stress_level = water_data.get("stress", "").lower()
        if stress_level:
            rec = get_recommendation_for_feature(crop_doc, "water_stress", stress_level, current_stage)
            if rec:
                all_recommendations["water_stress"] = rec
                recommendation_details["water_stress"] = {
                    "level": stress_level,
                    "score": water_data.get("score", 0)
                }

    # Nutrient Recommendations
    nutrient_data = features_data.get("nutrient_deficiency", {})
    if nutrient_data:
        nutrient_levels = []
        for nutrient, level in nutrient_data.items():
            if nutrient != "timestamp" and level != "insufficient_data":
                nutrient_levels.append(level)

        if nutrient_levels:
            if any("high" in str(l).lower() for l in nutrient_levels):
                overall_stress = "high"
            elif any("moderate" in str(l).lower() or "possible" in str(l).lower() for l in nutrient_levels):
                overall_stress = "moderate"
            elif any("low" in str(l).lower() for l in nutrient_levels):
                overall_stress = "low"
            else:
                overall_stress = "optimal"

            if overall_stress != "optimal":
                rec = get_recommendation_for_feature(crop_doc, "nutrient_deficiency", overall_stress, current_stage)
                if rec:
                    all_recommendations["nutrient_deficiency"] = rec
                    recommendation_details["nutrient_deficiency"] = {
                        "level": overall_stress,
                        "nitrogen_level": nutrient_data.get("nitrogen", "adequate")
                    }

    # Specific nutrient recommendations
    if nutrient_data:
        for nutrient, level in nutrient_data.items():
            if nutrient != "timestamp" and level != "insufficient_data" and nutrient in NUTRIENT_SECTIONS:
                rec = get_nutrient_recommendation(crop_doc, nutrient, level, current_stage)
                if rec:
                    individual_nutrients[nutrient] = {
                        "recommendation": rec,
                        "level": level
                    }

    return all_recommendations, recommendation_details, individual_nutrients

def resolve_conflicts_if_available(all_recommendations, plot_data, crop_doc, current_stage):
    """Apply conflict resolution if the module is available."""
    if CONFLICT_RESOLVER_AVAILABLE and all_recommendations:
        try:
            resolved_recs, conflicts_found = resolver.resolve_conflicts(
                plot_data, crop_doc, current_stage, all_recommendations
            )
            return resolved_recs, conflicts_found
        except Exception as e:
            debug_print(f"[WARNING] Error during conflict resolution: {e}")
            traceback.print_exc(file=sys.stderr)
            # Fallback to original recommendations if resolution fails
            return all_recommendations, []
    else:
        return all_recommendations, []

# --- Main Function ---
def generate_recommendations(plot_data_dict):
    """
    Takes plot data as a dictionary and returns a dictionary of recommendations.
    """
    try:
        debug_print(f"Processing plot data for ID: {plot_data_dict.get('plot_id')}")
        crop_type = plot_data_dict.get("current_crop", "").lower()

        if crop_type not in SUPPORTED_CROPS:
            return {"error": f"Unsupported crop: {crop_type}"}

        # Load crop documentation
        crop_doc_path = os.path.join(CROP_DOCS_PATH, f"{crop_type}.json") # Use os.path.join for robustness
        crop_doc = load_json_file(crop_doc_path)
        if not crop_doc:
            return {"error": f"No documentation available for {crop_type} at {crop_doc_path}"}

        # Get current crop stage
        features_data = plot_data_dict.get("features_data", {})
        current_stage_raw = features_data.get("stage_classifier", {}).get("stage", "")
        current_stage = get_standardized_stage(current_stage_raw)

        # Collect all recommendations first
        all_recommendations, rec_details, individual_nutrients = collect_all_recommendations(
            plot_data_dict, crop_doc, current_stage
        )

        # Apply conflict resolution if available
        final_recommendations, conflicts_found = resolve_conflicts_if_available(
            all_recommendations, plot_data_dict, crop_doc, current_stage
        )

        # Calculate data recency
        days_since_update = get_days_since_update(plot_data_dict.get("last_updated", ""))

        # Add metadata and return final structure
        output_data = {
            "plot_id": plot_data_dict.get("plot_id"),
            "farmer_id": plot_data_dict.get("farmer_id"), # Include farmer_id if available in input
            "crop_type": crop_type,
            "current_stage": current_stage_raw,
            "recommendations": final_recommendations, # The main output
            "recommendation_details": rec_details,
            "individual_nutrients": individual_nutrients,
            "conflicts_resolved": conflicts_found,
            "data_recency_days": days_since_update,
            "timestamp": datetime.now().isoformat()
        }

        debug_print(f"Successfully generated recommendations for plot {plot_data_dict.get('plot_id')}")
        return output_data

    except Exception as e:
        debug_print(f"[ERROR] Error generating recommendations: {e}")
        traceback.print_exc(file=sys.stderr) # Print full traceback for debugging
        return {"error": f"Failed to generate recommendations: {str(e)}"}

if __name__ == "__main__":
    input_data_str = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        if not input_data_str:
            raise ValueError("No input JSON provided")

        input_data = json.loads(input_data_str)
        result = generate_recommendations(input_data)

        # IMPORTANT: stdout must be JSON ONLY
        print(json.dumps(result))

    except Exception as e:
        error_response = {
            "error": "Python execution failed",
            "details": str(e)
        }
        print(json.dumps(error_response))
