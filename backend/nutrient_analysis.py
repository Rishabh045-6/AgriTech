"""
Nutrient deficiency analysis module
"""
import numpy as np
import pandas as pd
from config import NUTRIENT_THRESHOLDS, DEFICIENCY_COLORS, FEATURE_MAPPING

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