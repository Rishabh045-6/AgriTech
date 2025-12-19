import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import torch
import joblib
import folium
from streamlit_folium import folium_static
import sys
import os
import requests
from urllib.parse import quote

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_fetcher import fetch_data_for_demo, CROP_CONFIG

# ===============================
# PAGE CONFIGURATION
# ===============================
st.set_page_config(
    page_title="Crop Stage Classification",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================
# CUSTOM CSS
# ===============================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #228B22;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #F0FFF0;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #32CD32;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #D4EDDA;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #28A745;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #FFF3CD;
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid #FFC107;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #F8F9FA;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# MODEL LOADING FUNCTIONS
# ===============================
@st.cache_resource
def load_model(crop_type):
    """Load Transformer model for specific crop"""
    model_path = CROP_CONFIG[crop_type]['model_path']
    
    try:
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        
        # Get model parameters
        num_features = checkpoint.get('num_features', 19)
        window_size = checkpoint.get('window_size', 
                                     CROP_CONFIG.get(crop_type, {}).get('window_size', 7))
        
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
        
        print(f"✓ Loaded {crop_type} model: {model_path}")
        return model, checkpoint
        
    except Exception as e:
        st.error(f"Error loading {crop_type} model: {e}")
        return None, None
    # ===============================

# ===============================
# BACKEND INTEGRATION
# ===============================
def get_latest_plot_data():
    """Fetch latest plot from backend"""
    try:
        # Replace with your actual backend URL
        response = requests.get('http://localhost:3001/api/latest-plot')
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def get_plots_by_farmer(farmer_id):
    """Get all plots for a specific farmer"""
    try:
        response = requests.get(f'http://localhost:3001/api/plot-data/{farmer_id}')
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

# ===============================
# MAIN APP
# ===============================
st.markdown('<h1 class="main-header">🌾 Crop Growth Stage Classification</h1>', unsafe_allow_html=True)

# Session state for crop selection
if 'selected_crop' not in st.session_state:
    st.session_state.selected_crop = None

if 'plot_coordinates' not in st.session_state:
    st.session_state.plot_coordinates = None

if 'farmer_id' not in st.session_state:
    st.session_state.farmer_id = None

# Step 1: Get Farmer ID (from React Native)
st.markdown('<h2 class="sub-header">👤 Enter Farmer Information</h2>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    st.session_state.farmer_id = st.text_input(
        "Farmer ID", 
        value=st.session_state.farmer_id or "farmer_123456789"
    )

if st.session_state.farmer_id:
    # Step 2: Fetch Plot Coordinates from Backend
    plots = get_plots_by_farmer(st.session_state.farmer_id)
    
    if plots:
        st.markdown('<h2 class="sub-header">📍 Select Plot</h2>', unsafe_allow_html=True)
        
        plot_options = [f"Plot {i+1} (ID: {p['plotId']})" for i, p in enumerate(plots)]
        selected_plot_idx = st.selectbox("Choose a plot", range(len(plot_options)), format_func=lambda x: plot_options[x])
        
        selected_plot = plots[selected_plot_idx]
        st.session_state.plot_coordinates = selected_plot['coordinates']
        
        # Show plot on map
        center_lat = np.mean([p['latitude'] for p in st.session_state.plot_coordinates])
        center_lon = np.mean([p['longitude'] for p in st.session_state.plot_coordinates])
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
        folium.Polygon(
            locations=[(p['latitude'], p['longitude']) for p in st.session_state.plot_coordinates],
            color='#3388ff',
            weight=2,
            fill=True,
            fill_color='#3388ff',
            fill_opacity=0.4
        ).add_to(m)
        
        folium.Marker(
            [center_lat, center_lon],
            popup=f"Plot Area: {selected_plot.get('areaAcres', 'N/A')} acres",
            icon=folium.Icon(color='green', icon='info-sign')
        ).add_to(m)
        
        folium_static(m, width=700, height=400)
        
        st.info(f"Selected plot: {selected_plot['plotId']}, Area: {selected_plot.get('areaAcres', 'N/A')} acres")
    else:
        st.warning("No plots found for this farmer. Draw a plot in the mobile app first.")
        st.stop()

# Step 3: Crop Selection
if st.session_state.plot_coordinates:
    st.markdown('<h2 class="sub-header">🌾 Select Crop Type</h2>', unsafe_allow_html=True)
    
    crop_options = list(CROP_CONFIG.keys())
    st.session_state.selected_crop = st.selectbox(
        "What crop is grown in this field?",
        crop_options,
        format_func=lambda x: x.title().replace("_", " ")
    )
    
    if st.session_state.selected_crop:
        # Show crop info
        config = CROP_CONFIG[st.session_state.selected_crop]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📅 Growing Season</h3>
                <p>Month {config['sowing_start']['month']} - {config['season_end']['month']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h3>🪟 Analysis Window</h3>
                <p>{config['window_size']} days</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h3>📊 Features</h3>
                <p>19 spectral indices</p>
            </div>
            """, unsafe_allow_html=True)

# Step 4: Analyze Button
if st.session_state.selected_crop and st.session_state.plot_coordinates:
    st.markdown("---")
    if st.button("🚀 Analyze Crop Stage", type="primary", use_container_width=True):
        with st.spinner("Processing satellite data..."):
            try:
                # Convert coordinates for data fetcher (lon, lat format)
                corners = [(p['longitude'], p['latitude']) for p in st.session_state.plot_coordinates]
                
                # Fetch data
                result = fetch_data_for_demo(
                    corners=corners,
                    crop_type=st.session_state.selected_crop,
                    current_date=datetime.now()
                )
                
                if result is None:
                    st.error("Failed to fetch satellite data. Check coordinates and API keys.")
                    st.stop()
                
                # Load model
                model, checkpoint = load_model(st.session_state.selected_crop)
                
                if model is None:
                    st.error("Model not found. Please check model paths.")
                    st.stop()
                
                # Make prediction
                with torch.no_grad():
                    features_tensor = torch.FloatTensor(result['window_features'])
                    logits = model(features_tensor)
                    probabilities = torch.softmax(logits, dim=1).numpy()[0]
                    predicted_stage = np.argmax(probabilities)
                
                # Get stage names
                if checkpoint and 'class_names' in checkpoint:
                    stage_names = checkpoint['class_names']
                else:
                    stage_names = ["Vegetative", "Reproductive", "Ripening"]
                
                # Store results
                st.session_state.analysis_result = {
                    'result': result,
                    'probabilities': probabilities,
                    'predicted_stage': predicted_stage,
                    'stage_names': stage_names
                }
                
                st.success("✅ Analysis complete!")
            
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.exception(e)

# Step 5: Show Results
if hasattr(st.session_state, 'analysis_result'):
    result = st.session_state.analysis_result['result']
    probabilities = st.session_state.analysis_result['probabilities']
    predicted_stage = st.session_state.analysis_result['predicted_stage']
    stage_names = st.session_state.analysis_result['stage_names']
    
    # Show prediction
    st.markdown('<h2 class="sub-header">🎯 Analysis Results</h2>', unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="success-box">
        <h3>Crop Growth Stage: <strong>{stage_names[predicted_stage]}</strong></h3>
        <p>Confidence: <strong>{probabilities[predicted_stage]*100:.1f}%</strong></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show probabilities
    col1, col2 = st.columns(2)
    
    with col1:
        df_probs = pd.DataFrame({
            "Stage": stage_names,
            "Probability": probabilities
        })
        
        fig = px.bar(
            df_probs,
            x="Stage",
            y="Probability",
            title="Stage Probabilities",
            color="Probability",
            color_continuous_scale="Greens"
        )
        
        fig.update_layout(
            yaxis_range=[0, 1],
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Show NDVI trend
        fig = px.line(
            result['window_df'],
            x='date',
            y='NDVI',
            title='NDVI Trend Over Time',
            markers=True
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="NDVI Value",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Show data visualization
    st.markdown('<h3>📊 Data Visualization</h3>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📈 NDVI Trend", "🌾 All Features", "🗓️ Data Overview"])
    
    with tab1:
        fig = px.line(
            result['window_df'],
            x='date',
            y='NDVI',
            title='NDVI Trend Over Time',
            markers=True
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="NDVI Value",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        feature_cols = ['NDVI', 'GNDVI', 'SAVI', 'NDMI', 'NDWI']
        feature_df = result['window_df'][['date'] + feature_cols].melt(
            id_vars=['date'], var_name='Feature', value_name='Value'
        )
        
        fig = px.line(
            feature_df,
            x='date',
            y='Value',
            color='Feature',
            title='Vegetation Indices Over Time',
            markers=True
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Value",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.dataframe(
            result['window_df'][['date', 'NDVI', 'GNDVI', 'SAVI', 'B2', 'B3', 'B4']].round(4),
            use_container_width=True
        )
    
    # Show recommendations
    st.markdown('<h2 class="sub-header">💡 Recommendations</h2>', unsafe_allow_html=True)
    
    recommendations = {
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
    
    rec_list = recommendations.get(stage_names[predicted_stage], ["Monitor crop health regularly"])
    
    for rec in rec_list:
        st.markdown(f"• {rec}")
    
    # Export options
    st.markdown("---")
    st.markdown('<h2 class="sub-header">📥 Export Results</h2>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Download data
        csv = result['window_df'].to_csv(index=False)
        st.download_button(
            label="📄 Download Data as CSV",
            data=csv,
            file_name=f"{st.session_state.selected_crop}_field_data.csv",
            mime="text/csv"
        )
    
    with col2:
        # Download report
        report = f"""
        Crop Stage Classification Report
        =================================
        
        Crop: {st.session_state.selected_crop.title()}
        Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}
        Field Area: {selected_plot.get('areaAcres', 'N/A')} acres
        
        Data Summary:
        - Valid days found: {result['raw_data_count']}
        - Window size used: {result['crop_config']['window_size']}
        - Date range: {result['date_info']['window_start'].strftime('%Y-%m-%d')} to {result['date_info']['window_end'].strftime('%Y-%m-%d')}
        
        Prediction:
        - Growth Stage: {stage_names[predicted_stage]}
        - Confidence: {probabilities[predicted_stage]*100:.1f}%
        
        NDVI Statistics:
        - Average: {result['window_df']['NDVI'].mean():.3f}
        - Trend: {'Increasing' if result['window_df']['NDVI'].iloc[-1] > result['window_df']['NDVI'].iloc[0] else 'Decreasing'}
        
        Model Input Shape: {result['window_features'].shape}
        """
        
        st.download_button(
            label="📋 Download Report",
            data=report,
            file_name=f"{st.session_state.selected_crop}_analysis_report.txt",
            mime="text/plain"
        )

# Default welcome message
if not st.session_state.farmer_id:
    st.markdown("""
    <div class="info-box">
        <h3>👋 Welcome to Crop Stage Classification!</h3>
        <p>This system analyzes satellite data to determine crop growth stages.</p>
        
        <h4>How to use:</h4>
        <ol>
            <li>Draw a plot using the mobile app</li>
            <li>Enter your Farmer ID above</li>
            <li>Select the plot and crop type</li>
            <li>Click "Analyze Crop Stage"</li>
        </ol>
        
        <p><strong>Note:</strong> This connects to your PostGIS backend to get plot coordinates.</p>
    </div>
    """, unsafe_allow_html=True)