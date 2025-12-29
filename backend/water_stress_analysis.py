"""
Water stress analysis functions with stage-aware irrigation advice
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from config import STRESS_WEIGHTS, THRESHOLDS, STATUS_COLORS

def minmax_norm(x, eps=1e-6):
    """Min-max normalization"""
    if isinstance(x, (list, np.ndarray)):
        x = np.array(x)
        if len(x) == 0 or (x.max() - x.min()) == 0:
            return np.zeros_like(x)
        return (x - x.min()) / (x.max() - x.min() + eps)
    return 0

def calculate_water_stress_score(window_mean_values):
    """Calculate water stress score for a window - FIXED NAME"""
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

# ALIAS with the old name for backward compatibility
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
        stress_result = calculate_water_stress_score(window_mean)  # Use the correct function name
        
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

def create_stress_gauge(score, status):
    """Create gauge chart for water stress score"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Water Stress Score", 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': STATUS_COLORS[status]},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, THRESHOLDS['OPTIMAL']], 'color': '#C8E6C9'},
                {'range': [THRESHOLDS['OPTIMAL'], THRESHOLDS['MILD']], 'color': '#FFF9C4'},
                {'range': [THRESHOLDS['MILD'], THRESHOLDS['MODERATE']], 'color': '#FFCC80'},
                {'range': [THRESHOLDS['MODERATE'], 100], 'color': '#FFCDD2'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': score
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig

def create_trend_chart(analysis_results):
    """Create trend chart for water stress scores"""
    fig = go.Figure()
    
    scores = analysis_results['trend']['scores']
    window_ids = [f"Window {i+1}" for i in range(len(scores))]
    dates_str = [a['dates_str'] for a in analysis_results['window_analyses']]
    
    # Add line
    fig.add_trace(go.Scatter(
        x=window_ids,
        y=scores,
        mode='lines+markers',
        name='Stress Score',
        line=dict(color='royalblue', width=3),
        marker=dict(size=10),
        text=dates_str,
        hovertemplate='%{text}<br>Score: %{y:.1f}<extra></extra>'
    ))
    
    # Add threshold areas
    fig.add_hrect(y0=0, y1=THRESHOLDS['OPTIMAL'], 
                  fillcolor="green", opacity=0.1, line_width=0,
                  annotation_text="Optimal", annotation_position="top left")
    fig.add_hrect(y0=THRESHOLDS['OPTIMAL'], y1=THRESHOLDS['MILD'], 
                  fillcolor="yellow", opacity=0.1, line_width=0,
                  annotation_text="Mild", annotation_position="top left")
    fig.add_hrect(y0=THRESHOLDS['MILD'], y1=THRESHOLDS['MODERATE'], 
                  fillcolor="orange", opacity=0.1, line_width=0,
                  annotation_text="Moderate", annotation_position="top left")
    fig.add_hrect(y0=THRESHOLDS['MODERATE'], y1=100, 
                  fillcolor="red", opacity=0.1, line_width=0,
                  annotation_text="Severe", annotation_position="top left")
    
    fig.update_layout(
        title='Water Stress Trend Over Time',
        xaxis_title='Analysis Windows',
        yaxis_title='Water Stress Score',
        hovermode='x',
        height=400,
        showlegend=False
    )
    
    return fig

def create_component_chart(components):
    """Create bar chart for stress components"""
    fig = go.Figure(data=[
        go.Bar(
            x=list(components.keys()),
            y=list(components.values()),
            marker_color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        )
    ])
    
    fig.update_layout(
        title='Stress Component Breakdown',
        xaxis_title='Index',
        yaxis_title='Contribution to Stress (%)',
        height=300
    )
    
    return fig

def create_daily_indices_chart(df, indices=['NDMI', 'NDWI', 'MSI', 'NMDI']):
    """Create line chart for daily index values"""
    fig = go.Figure()
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    
    for idx, index in enumerate(indices):
        if index in df.columns:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[index],
                mode='lines+markers',
                name=index,
                line=dict(color=colors[idx % len(colors)], width=2),
                marker=dict(size=6)
            ))
    
    fig.update_layout(
        title='Daily Water Stress Indices',
        xaxis_title='Date',
        yaxis_title='Index Value',
        hovermode='x unified',
        height=400
    )
    
    return fig