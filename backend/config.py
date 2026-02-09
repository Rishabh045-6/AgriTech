# config.py

# Configuration settings
DEMO_DATA_PATH = "./demo_data.json"
CROP_DOCS_PATH = "./crop_docs/" # Ensure this path ends with a slash if joining later

SUPPORTED_CROPS = [
    "rice", "wheat", "maize", "lentils", "bean", "pigeon_pea", "chickpea"
]

# Mapping from feature names to document sections
FEATURE_TO_SECTION = {
    "disease_detection": "DISEASE_RISK_ADVICE",
    "pest_risk": "PEST_RISK_ADVICE",
    "water_stress": "IRRIGATION_WATER_STRESS_ADVICE",
    "nutrient_deficiency": "GENERAL_NUTRIENT_STRESS_ADVICE"
}

# Additional sections for nutrient details
NUTRIENT_SECTIONS = {
    "nitrogen": "NITROGEN_STATUS_ADVICE",
    "chlorophyll": "CHLOROPHYLL_STATUS_ADVICE"
}

# Map crop stages from your data to standardized stages
# Note: If the same raw stage name maps to different standardized stages depending on crop,
# the logic in decision_engine.py needs to handle the crop-specific mapping.
# For now, assuming generic mapping where possible.
STAGE_MAPPING = {
    # Rice stages
    "tillering": "vegetative",
    "jointing": "vegetative", # Could be specific to rice/wheat - needs context
    "booting": "reproductive",
    "flowering": "reproductive", # Could be specific to rice/wheat - needs context
    "milking": "ripening",
    "dough": "ripening", # Could be specific to rice/wheat - needs context
    "maturity": "ripening",
    # Wheat stages
    "jointing": "vegetative", # Overwrites rice's jointing -> vegetative (fine if generic is ok)
    "heading": "reproductive",
    "flowering": "reproductive", # Overwrites rice's flowering -> reproductive (fine if generic is ok)
    # Maize stages
    "v6": "vegetative",
    "v12": "vegetative",
    "silking": "reproductive",
    "dough": "ripening", # Overwrites rice/wheat's dough -> ripening (fine if generic is ok)
    # Legume stages
    "branching": "vegetative",
    "flowering": "reproductive", # Overwrites rice/wheat's flowering -> reproductive (fine if generic is ok)
    "pod_filling": "ripening",
    # Generic stages that might apply broadly
    "germination": "vegetative",
    "seedling": "vegetative",
    "vegetative": "vegetative", # Identity mapping
    "reproductive": "reproductive",
    "ripening": "ripening",
    "harvest": "ripening" # Often considered part of ripening
}

# NEW: Priority levels for conflict resolution
PRIORITY_LEVELS = {
    1: "Critical - Immediate Action",
    2: "High - Action Required",
    3: "Medium - Monitor/Plan",
    4: "Low - Advisory"
}

# Legume crops (self-nitrogen fixing)
LEGUME_CROPS = ["lentils", "bean", "pigeon_pea", "chickpea"]

# Validity windows for different advice types (in days)
VALIDITY_WINDOWS = {
    "disease_risk": {
        "high": 3,        # Disease can change quickly
        "medium": 5,
        "low": 7
    },
    "pest_risk": {
        "high": 3,        # Pest outbreaks can be rapid
        "medium": 5,
        "low": 7
    },
    "water_stress": {
        "severe": 2,      # 2-day validity for "irrigate immediately"
        "moderate": 4,    # 4-day validity
        "mild": 7,        # 7-day validity
        "optimal": 7
    },
    "nutrient_stress": { # Changed key from 'nutrient_deficiency' to 'nutrient_stress' to match potential usage
        "high": 7,        # Nutrient status changes slowly
        "moderate": 7,
        "low": 7
    }
}

# Default satellite revisit assumption (days)
SATELLITE_REVISIT_DAYS = 5

# Time-sensitive keywords that need qualification
TIME_SENSITIVE_KEYWORDS = [
    "immediately", "urgently", "now", "today", "within 1-2 days",
    "within 24 hours", "as soon as possible"
]

# --- Added Constants for Consistency ---
# Define the path constants that decision_engine.py expects
DEMO_DATA_PATH = DEMO_DATA_PATH
CROP_DOCS_PATH = CROP_DOCS_PATH
SUPPORTED_CROPS = SUPPORTED_CROPS
FEATURE_TO_SECTION = FEATURE_TO_SECTION
NUTRIENT_SECTIONS = NUTRIENT_SECTIONS
STAGE_MAPPING = STAGE_MAPPING
VALIDITY_WINDOWS = VALIDITY_WINDOWS
SATELLITE_REVISIT_DAYS = SATELLITE_REVISIT_DAYS
TIME_SENSITIVE_KEYWORDS = TIME_SENSITIVE_KEYWORDS

# Ensure CROP_DOCS_PATH ends with a slash for os.path.join
if not CROP_DOCS_PATH.endswith('/'):
    CROP_DOCS_PATH = CROP_DOCS_PATH + '/'