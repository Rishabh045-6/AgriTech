import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
import torch
import torch.nn as nn
import joblib
import folium
from streamlit_folium import folium_static
import sys
import os

# Local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from data_fetcher import fetch_data_for_demo, CROP_CONFIG

# ===============================
# CORRECT TRANSFORMER MODEL (Matches trained model exactly)
# ===============================
class TransformerClassifier(nn.Module):
    def __init__(self, input_dim, seq_len, d_model=64, nhead=4, num_layers=3, dropout=0.1):
        super().__init__()
        
        # Input projection
        self.input_proj = nn.Linear(input_dim, d_model)
        
        # Positional encoding
        self.pos_encoder = nn.Parameter(torch.zeros(1, seq_len, d_model))
        
        # Transformer encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=128,
            dropout=dropout,
            batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # CORRECT Classification head - Based on your saved model structure
        self.classifier = nn.Sequential(
            nn.LayerNorm(d_model),       # layer 0
            nn.Dropout(dropout),         # layer 1
            nn.Linear(d_model, 32),      # layer 2 - 32 hidden units
            nn.ReLU(),                   # layer 3
            nn.Dropout(dropout),         # layer 4
            nn.Linear(32, 1)             # layer 5 - 32 to 1
        )
        
    def forward(self, x):
        # x shape: (batch_size, seq_len, input_dim)
        x = self.input_proj(x)
        x = x + self.pos_encoder
        x = self.transformer_encoder(x)
        x = x.mean(dim=1)
        x = self.classifier(x)
        return x.squeeze(-1)

# ===============================
# PAGE CONFIG
# ===============================
st.set_page_config(
    page_title="Crop Disease Detection Demo",
    page_icon="🦠",
    layout="wide"
)

# ===============================
# CONSTANTS
# ===============================
CLASS_NAMES = ["Healthy", "Diseased"]
DISEASE_THRESHOLD = 0.5

# ===============================
# LOADERS
# ===============================
@st.cache_resource
def load_model(model_path, num_features, seq_len):
    # Create model with CORRECT architecture (32 hidden units)
    model = TransformerClassifier(
        input_dim=num_features,
        seq_len=seq_len,
        d_model=64,
        nhead=4,
        num_layers=3
    )
    
    try:
        state = torch.load(model_path, map_location="cpu")
        model.load_state_dict(state)
        st.success(f"✓ Model loaded successfully from {model_path}")
    except Exception as e:
        st.error(f"✗ Error loading model: {e}")
        st.stop()
    
    model.eval()
    return model

@st.cache_resource
def load_scaler(path):
    try:
        scaler = joblib.load(path)
        return scaler
    except Exception as e:
        st.error(f"Error loading scaler from {path}: {e}")
        return None

# ===============================
# SIDEBAR
# ===============================
with st.sidebar:
    st.markdown("## 🌱 Crop Selection")
    selected_crop = st.selectbox(
        "Select Crop",
        list(CROP_CONFIG.keys()),
        format_func=lambda x: x.replace("_", " ").title()
    )

    st.markdown("## 📅 Date")
    selected_date = st.date_input("Analysis date", datetime.now())

    st.markdown("## 📍 Field Coordinates")

    default_coords = [
        [75.0, 30.0],
        [75.0, 30.1],
        [75.1, 30.1],
        [75.1, 30.0]
    ]

    corners = []
    for i in range(4):
        col1, col2 = st.columns(2)
        lon = col1.number_input(f"Lon {i+1}", value=default_coords[i][0])
        lat = col2.number_input(f"Lat {i+1}", value=default_coords[i][1])
        corners.append([lon, lat])
    corners.append(corners[0])

    analyze = st.button("🧪 Detect Disease", use_container_width=True)

# ===============================
# MAIN HEADER
# ===============================
st.markdown(
    "<h1 style='text-align:center'>🦠 Crop Disease Detection Demo</h1>",
    unsafe_allow_html=True
)

# ===============================
# RUN ANALYSIS
# ===============================
if analyze:
    with st.spinner("Fetching satellite data..."):
        result = fetch_data_for_demo(
            corners=corners,
            crop_type=selected_crop,
            current_date=selected_date
        )

    if result is None:
        st.error("Data fetch failed. Please check coordinates and try again.")
        st.stop()

    # ===============================
    # VISUALIZATION
    # ===============================
    st.subheader("📈 NDVI Trend")
    fig = px.line(
        result["window_df"],
        x="date",
        y="NDVI",
        markers=True,
        title=f"NDVI Trend for {selected_crop.replace('_', ' ').title()}",
        labels={"NDVI": "NDVI Value", "date": "Date"}
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="NDVI",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    # ===============================
    # DEBUG: SHOW DATA QUALITY
    # ===============================
    with st.expander("🔍 Debug Data Quality"):
        st.write("**Raw NDVI values:**")
        st.dataframe(result["window_df"][["date", "NDVI"]].round(3))
        
        st.write("**NDVI Statistics:**")
        st.write(f"Mean: {result['window_df']['NDVI'].mean():.3f}")
        st.write(f"Min: {result['window_df']['NDVI'].min():.3f}")
        st.write(f"Max: {result['window_df']['NDVI'].max():.3f}")
        st.write(f"Std: {result['window_df']['NDVI'].std():.3f}")
        
        # Check if NDVI values are reasonable
        if result['window_df']['NDVI'].mean() < -1 or result['window_df']['NDVI'].mean() > 1:
            st.warning("⚠️ NDVI values outside typical range [-1, 1]")

    # ===============================
    # MODEL INFERENCE
    # ===============================
    st.subheader("🤖 Disease Prediction")

    # Define model and scaler paths
    model_path = f"models/{selected_crop}_transformer_model.pth"
    scaler_path = f"scalers/{selected_crop}_scaler.pkl"
    
    # Check if files exist
    if not os.path.exists(model_path):
        st.error(f"Model file not found: {model_path}")
        st.info(f"Expected path: {os.path.abspath(model_path)}")
        st.stop()
    
    if not os.path.exists(scaler_path):
        st.error(f"Scaler file not found: {scaler_path}")
        st.info(f"Expected path: {os.path.abspath(scaler_path)}")
        st.stop()

    # Load scaler
    scaler = load_scaler(scaler_path)
    if scaler is None:
        st.stop()
    
    # Prepare features
    features = result["window_features"]
    
    # Debug: Show feature statistics
    with st.expander("📊 Feature Statistics"):
        feature_names = [
            'B2', 'B3', 'B4', 'B5', 'B8', 'B11', 'B12',
            'NDVI', 'GNDVI', 'SAVI', 'NDMI', 'MSI', 'NDWI', 'NMDI',
            'NDRE', 'CIredEdge', 'CIgreen', 'PSRI', 'SIPI'
        ]
        
        # Show first time step
        st.write("**First time step values:**")
        first_sample = features[0, 0, :]
        for i, (name, value) in enumerate(zip(feature_names, first_sample)):
            st.write(f"{name}: {value:.4f}")
        
        # Check for extreme values
        st.write("**Data quality check:**")
        if np.any(np.isnan(features)):
            st.error("❌ NaN values detected!")
        else:
            st.success("✓ No NaN values")
            
        if np.any(np.abs(features) > 100):
            st.warning("⚠️ Extreme values detected (|value| > 100)")
    
    # Scale features
    original_shape = features.shape
    features_flat = features.reshape(-1, features.shape[2])
    features_scaled_flat = scaler.transform(features_flat)
    features_scaled = features_scaled_flat.reshape(original_shape)
    
    # Debug: Show scaled statistics
    with st.expander("⚖️ Scaled Feature Statistics"):
        st.write("**After scaling (first time step):**")
        first_sample_scaled = features_scaled[0, 0, :]
        for i, (name, value) in enumerate(zip(feature_names, first_sample_scaled)):
            st.write(f"{name}: {value:.4f}")
        
        st.write(f"\n**Overall scaled statistics:**")
        st.write(f"Mean: {features_scaled.mean():.4f}")
        st.write(f"Std: {features_scaled.std():.4f}")
        st.write(f"Min: {features_scaled.min():.4f}")
        st.write(f"Max: {features_scaled.max():.4f}")
    
    # Load model
        # Load model
    model = load_model(
        model_path,
        num_features=features.shape[2],
        seq_len=features.shape[1]
    )

    # Make prediction
    with torch.no_grad():
        x = torch.tensor(features_scaled, dtype=torch.float32)
        logit = model(x)
        raw_prob = torch.sigmoid(logit).item()
    
    # CALIBRATION: Adjust probability based on NDVI
    ndvi_mean = result["window_df"]["NDVI"].mean()
    ndvi_trend = result["window_df"]["NDVI"].iloc[-1] - result["window_df"]["NDVI"].iloc[0]
    
    # Simple rule-based calibration
    if raw_prob < 0.01:
        # Extremely low probability
        if ndvi_mean > 0.5:
            # Healthy NDVI - adjust probability upward
            prob = 0.05 + (ndvi_mean - 0.5) * 0.1  # 5-15% for healthy
            st.info(f"🌱 Adjusted: Healthy NDVI ({ndvi_mean:.2f}) suggests low disease risk")
        elif ndvi_mean < 0.2:
            # Low NDVI - might actually be diseased
            prob = 0.3 + (0.2 - ndvi_mean) * 1.0  # 30-50% for stressed
            st.info(f"⚠️ Adjusted: Low NDVI ({ndvi_mean:.2f}) suggests possible stress")
        else:
            # Moderate NDVI
            prob = max(0.01, raw_prob * 5)  # Slight boost
    elif raw_prob > 0.99:
        # Extremely high probability
        if ndvi_mean > 0.6:
            # Healthy NDVI - adjust downward
            prob = 0.7 - (ndvi_mean - 0.6) * 0.5  # 70-20% range
            st.info(f"🌱 Adjusted: Healthy NDVI ({ndvi_mean:.2f}) suggests lower risk")
        else:
            prob = 0.8  # Still high but not extreme
    else:
        # Reasonable probability
        prob = raw_prob
    
    # Ensure probability is in valid range
    prob = max(0.01, min(0.99, prob))
    
    # Show results
    st.subheader("📊 Prediction Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if prob < 0.3:
            st.success(f"**Prediction:** Healthy")
            st.metric("Risk Level", "LOW")
        elif prob < 0.7:
            st.warning(f"**Prediction:** Uncertain")
            st.metric("Risk Level", "MEDIUM")
        else:
            st.error(f"**Prediction:** Diseased")
            st.metric("Risk Level", "HIGH")
    
    with col2:
        st.metric("Disease Probability", f"{prob*100:.1f}%")
    
    with col3:
        st.metric("NDVI Health", f"{ndvi_mean:.3f}", 
                  delta=f"{ndvi_trend:+.3f} trend")
    
    # Visual gauge
    st.progress(prob)
    st.caption(f"Disease probability: {prob:.3f} ({prob*100:.1f}%)")
    
    # Detailed output
    with st.expander("🔍 Technical Details"):
        st.write(f"**Raw Model Output:**")
        st.write(f"- Logit: {logit.item():.6f}")
        st.write(f"- Raw probability: {raw_prob:.6f} ({raw_prob*100:.4f}%)")
        st.write(f"- Calibrated probability: {prob:.6f} ({prob*100:.4f}%)")
        st.write(f"- NDVI mean: {ndvi_mean:.3f}")
        st.write(f"- NDVI trend: {ndvi_trend:+.3f}")
        
        if raw_prob < 0.01 or raw_prob > 0.99:
            st.info("Note: Probability was calibrated based on vegetation health indicators")
    
    # Interpretation
    st.subheader("💡 Interpretation & Recommendations")
    
    if prob < 0.2:
        st.success("""
        **✅ Low Disease Risk Detected**
        
        **Indicators:**
        - Good vegetation health (NDVI > 0.5)
        - No strong disease signals
        - Crop appears to be growing well
        
        **Recommendations:**
        1. Continue current management practices
        2. Next check in 10-14 days
        3. Monitor weather conditions
        """)
    elif prob < 0.5:
        st.warning("""
        **⚠️ Moderate Disease Risk Detected**
        
        **Indicators:**
        - Some vegetation stress detected
        - Possible early disease signs
        - Monitor closely
        
        **Recommendations:**
        1. Increase monitoring frequency
        2. Consider ground verification
        3. Check for other stress factors
        4. Next check in 5-7 days
        """)
    else:
        st.error("""
        **🔴 High Disease Risk Detected**
        
        **Indicators:**
        - Significant vegetation stress
        - Strong disease indicators
        - Immediate attention needed
        
        **Recommendations:**
        1. **Conduct ground verification immediately**
        2. Isolate affected areas if possible
        3. Consult agricultural expert
        4. Consider treatment options
        5. Daily monitoring advised
        """)
    # ===============================
    # DATA SUMMARY
    # ===============================
    with st.expander("📋 Complete Data Summary"):
        st.write("**Analysis Details:**")
        st.write(f"- Crop: {selected_crop.replace('_', ' ').title()}")
        st.write(f"- Analysis Date: {selected_date}")
        st.write(f"- Window Size: {result['date_info']['window_size']} days")
        st.write(f"- Valid Data Points: {result['raw_data_count']}")
        
        st.write("\n**Date Range:**")
        dates = result["window_df"]["date"]
        st.write(f"- Start: {dates.iloc[0].strftime('%Y-%m-%d')}")
        st.write(f"- End: {dates.iloc[-1].strftime('%Y-%m-%d')}")
        
        st.write("\n**Key Indices:**")
        latest = result["window_df"].iloc[-1]
        cols = st.columns(4)
        indices = ["NDVI", "GNDVI", "NDMI", "MSI"]
        for col, idx in zip(cols, indices):
            with col:
                st.metric(idx, f"{latest[idx]:.3f}")
        
        st.write("\n**Full Dataset:**")
        st.dataframe(result["window_df"].round(3))

else:
    st.info(
        """
        ## 🌾 Crop Disease Detection System
        
        This tool uses satellite data and AI to detect potential crop diseases.
        
        ### How it works:
        1. **Select a crop** from the sidebar
        2. **Choose analysis date** (defaults to today)
        3. **Enter field coordinates** or use defaults
        4. **Click 'Detect Disease'** to analyze
        
        ### The system will:
        - Fetch satellite data for the selected period
        - Analyze 19 spectral features
        - Run AI model for disease prediction
        - Provide recommendations
        
        ### Currently supported crops:
        - Rice, Wheat, Maize, Chickpea
        - Pigeon Pea, Beans, Lentils
        
        **Note:** Ensure model files are in the `models/` folder and scaler files in `scalers/` folder.
        """
    )

# ===============================
# FOOTER
# ===============================
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:gray;font-size:small'>"
    "Crop Disease Detection Demo • Uses Sentinel-2 satellite data • AI-powered analysis"
    "</div>",
    unsafe_allow_html=True
)