"""
Disease and pest penalty calculations
"""
from typing import Dict

def calculate_disease_penalty(disease_label: int) -> float:
    """
    Calculate yield penalty due to disease
    
    Args:
        disease_label: 0 = healthy, 1 = diseased
    
    Returns:
        Penalty factor (0-1, where 0.25 = 25% yield loss)
    """
    if disease_label == 0:
        return 0.0  # No penalty for healthy crops
    else:
        return 0.25  # 25% yield loss for diseased crops

def calculate_pest_penalty(pest_risk: int) -> float:
    """
    Calculate yield penalty due to pests
    
    Args:
        pest_risk: 0 = low, 1 = medium, 2 = high
    
    Returns:
        Penalty factor (0-1)
    """
    if pest_risk == 2:  # High risk
        return 0.20  # 20% yield loss
    elif pest_risk == 1:  # Medium risk
        return 0.10  # 10% yield loss
    else:  # Low risk
        return 0.0   # No penalty

def get_disease_level(disease_probability: float) -> Dict:
    """
    Convert disease probability to categorical level
    """
    if disease_probability < 0.3:
        return {
            'level': 'none',
            'label': 'Healthy',
            'color': 'green',
            'multiplier': 1.0,
            'recommendation': 'No disease detected.'
        }
    elif disease_probability < 0.7:
        return {
            'level': 'mild',
            'label': 'Potential Disease',
            'color': 'orange',
            'multiplier': 0.85,
            'recommendation': 'Monitor closely for disease symptoms.'
        }
    else:
        return {
            'level': 'severe',
            'label': 'Diseased',
            'color': 'red',
            'multiplier': 0.65,
            'recommendation': 'Immediate disease management needed.'
        }

def get_pest_level(pest_risk: int) -> Dict:
    """
    Convert pest risk to categorical level
    """
    if pest_risk == 0:
        return {
            'level': 'low',
            'label': 'Low Pest Risk',
            'color': 'green',
            'multiplier': 0.95,
            'recommendation': 'Normal pest monitoring.'
        }
    elif pest_risk == 1:
        return {
            'level': 'medium',
            'label': 'Medium Pest Risk',
            'color': 'orange',
            'multiplier': 0.80,
            'recommendation': 'Increase pest monitoring frequency.'
        }
    else:  # pest_risk == 2
        return {
            'level': 'high',
            'label': 'High Pest Risk',
            'color': 'red',
            'multiplier': 0.60,
            'recommendation': 'Immediate pest control measures needed.'
        }

def calculate_total_penalty(
    disease_penalty: float,
    pest_penalty: float
) -> Dict:
    """
    Calculate total penalty and provide insights
    """
    total_penalty = disease_penalty + pest_penalty
    
    # Maximum penalty cap (can't lose more than 50% yield)
    total_penalty = min(total_penalty, 0.5)
    
    insights = []
    
    if disease_penalty > 0:
        insights.append(f"Disease risk causing {disease_penalty*100:.0f}% yield reduction")
    
    if pest_penalty > 0:
        insights.append(f"Pest risk causing {pest_penalty*100:.0f}% yield reduction")
    
    if total_penalty == 0:
        insights.append("No significant biotic stress detected")
    
    return {
        'total_penalty': total_penalty,
        'disease_penalty': disease_penalty,
        'pest_penalty': pest_penalty,
        'insights': insights,
        'remaining_yield_potential': 1 - total_penalty
    }