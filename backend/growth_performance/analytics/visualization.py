import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import numpy as np

def create_ndvi_timeseries_plot(dates, ndvi_values, window_df=None):
    """Create NDVI timeseries plot with optional stats"""
    fig = go.Figure()
    
    # Add NDVI line
    fig.add_trace(go.Scatter(
        x=dates,
        y=ndvi_values,
        mode='lines+markers',
        name='NDVI',
        line=dict(color='green', width=3),
        marker=dict(size=8)
    ))
    
    # Add mean line
    mean_ndvi = np.mean(ndvi_values)
    fig.add_hline(
        y=mean_ndvi,
        line_dash="dash",
        line_color="blue",
        annotation_text=f"Mean: {mean_ndvi:.3f}",
        annotation_position="bottom right"
    )
    
    # Add threshold lines
    fig.add_hline(y=0.3, line_dash="dot", line_color="orange", 
                  annotation_text="Low threshold")
    fig.add_hline(y=0.8, line_dash="dot", line_color="red", 
                  annotation_text="High threshold")
    
    # Update layout
    fig.update_layout(
        title='NDVI Time Series',
        xaxis_title='Date',
        yaxis_title='NDVI Value',
        yaxis_range=[0, 1],
        template='plotly_white',
        height=400
    )
    
    return fig

def create_score_radar_chart(scores):
    """Create radar chart for component scores"""
    categories = ['Growth Rate', 'Biomass', 'Stability', 'Stage Progress']
    values = list(scores.values())
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values + [values[0]],  # Close the polygon
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
        title='Growth Performance Components',
        height=400
    )
    
    return fig

def create_score_bar_chart(scores, overall_score):
    """Create bar chart for scores"""
    categories = list(scores.keys())
    values = list(scores.values())
    
    # Add overall score
    categories.append('Overall')
    values.append(overall_score)
    
    # Define colors based on score
    colors = []
    for score in values:
        if score >= 80:
            colors.append('green')
        elif score >= 60:
            colors.append('blue')
        elif score >= 40:
            colors.append('orange')
        else:
            colors.append('red')
    
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
        title='Performance Scores',
        xaxis_title='Metric',
        yaxis_title='Score',
        yaxis_range=[0, 100],
        template='plotly_white',
        height=400
    )
    
    return fig

def create_metric_timeseries(window_df):
    """Create timeseries plots for multiple metrics"""
    metrics = ['NDVI', 'GNDVI', 'NDMI', 'NDRE']
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=metrics,
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    colors = px.colors.qualitative.Set2
    
    for i, metric in enumerate(metrics):
        row = i // 2 + 1
        col = i % 2 + 1
        
        fig.add_trace(
            go.Scatter(
                x=window_df['date'],
                y=window_df[metric],
                mode='lines+markers',
                name=metric,
                line=dict(color=colors[i], width=2),
                marker=dict(size=4)
            ),
            row=row, col=col
        )
        
        fig.update_yaxes(title_text=metric, row=row, col=col, range=[0, 1])
    
    fig.update_layout(
        title='Crop Health Metrics Over Time',
        height=600,
        showlegend=False,
        template='plotly_white'
    )
    
    return fig