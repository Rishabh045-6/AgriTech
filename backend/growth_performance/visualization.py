"""
Yield-specific visualizations
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np

def create_yield_gauge(yield_score: float, category: dict) -> go.Figure:
    """
    Create yield score gauge chart
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=yield_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Yield Score", 'font': {'size': 24}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': category['color']},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 40], 'color': '#FF6B6B'},
                {'range': [40, 70], 'color': '#FFD93D'},
                {'range': [70, 85], 'color': '#6BCF7F'},
                {'range': [85, 100], 'color': '#4CAF50'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 50
            }
        }
    ))
    
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig

def create_component_chart(component_scores: dict) -> go.Figure:
    """
    Create component scores bar chart
    """
    categories = list(component_scores.keys())
    values = list(component_scores.values())
    
    colors = []
    for score in values:
        if score >= 80:
            colors.append('#4CAF50')
        elif score >= 60:
            colors.append('#6BCF7F')
        elif score >= 40:
            colors.append('#FFD93D')
        else:
            colors.append('#FF6B6B')
    
    fig = go.Figure(data=[
        go.Bar(
            x=categories,
            y=values,
            marker_color=colors,
            text=[f'{v:.1f}' for v in values],
            textposition='auto',
        )
    ])
    
    fig.update_layout(
        title='Yield Component Scores',
        xaxis_title='Component',
        yaxis_title='Score',
        yaxis_range=[0, 100],
        template='plotly_white',
        height=400
    )
    
    return fig

def create_yield_breakdown_chart(breakdown: dict) -> go.Figure:
    """
    Create yield breakdown waterfall chart
    """
    factors = list(breakdown.keys())
    values = list(breakdown.values())
    
    fig = go.Figure(go.Waterfall(
        name="Yield Factors",
        orientation="v",
        measure=["relative"] * (len(factors) - 1) + ["total"],
        x=factors,
        y=values,
        text=[f"{v:.2f}x" for v in values],
        textposition="outside",
        connector={"line": {"color": "rgb(63, 63, 63)"}},
    ))
    
    fig.update_layout(
        title="Yield Factor Breakdown",
        showlegend=False,
        height=400
    )
    
    return fig

def create_stress_radar(stress_levels: dict) -> go.Figure:
    """
    Create stress radar chart
    """
    categories = list(stress_levels.keys())
    
    # Extract multiplier values
    values = []
    for cat in categories:
        if isinstance(stress_levels[cat], dict) and 'multiplier' in stress_levels[cat]:
            values.append(stress_levels[cat]['multiplier'] * 100)
        else:
            # Default value if multiplier not found
            values.append(80)
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values + [values[0]],  # Close the polygon
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(255, 107, 107, 0.3)',
        line=dict(color='red', width=2),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        title='Stress Impact on Yield',
        height=400
    )
    
    return fig

def create_yield_comparison_chart(
    current_yield: float,
    national_average: float,
    expected_yield: float
) -> go.Figure:
    """
    Create yield comparison bar chart
    """
    labels = ['Current Estimate', 'National Average', 'Expected Potential']
    values = [current_yield, national_average, expected_yield]
    
    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=values,
            text=[f'{v:,.0f} kg/ha' for v in values],
            textposition='auto',
            marker_color=['#4CAF50', '#2196F3', '#FF9800']
        )
    ])
    
    fig.update_layout(
        title='Yield Comparison',
        yaxis_title='Yield (kg/ha)',
        template='plotly_white',
        height=400
    )
    
    return fig

def create_ndvi_timeseries_plot(dates, ndvi_values):
    """Create NDVI timeseries plot"""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=ndvi_values,
        mode='lines+markers',
        name='NDVI',
        line=dict(color='green', width=3),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title='NDVI Time Series',
        xaxis_title='Date',
        yaxis_title='NDVI Value',
        yaxis_range=[0, 1],
        template='plotly_white',
        height=300
    )
    
    return fig

def create_score_radar_chart(scores):
    """Create radar chart for scores"""
    categories = list(scores.keys())
    values = list(scores.values())
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(144, 238, 144, 0.5)',
        line=dict(color='green', width=2),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        title='Performance Components',
        height=400
    )
    
    return fig