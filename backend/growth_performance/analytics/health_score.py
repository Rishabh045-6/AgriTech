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