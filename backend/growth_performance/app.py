import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Import modules
from config import DEMO_CONFIG, COLORS, CROPS, STAGES
from analytics.growth_scores import calculate_all_scores
from analytics.health_score import calculate_health_report
from analytics.visualization import (
    create_ndvi_timeseries_plot,
    create_score_radar_chart,
    create_score_bar_chart,
    create_metric_timeseries
)

# Mock data generator for demo
def generate_mock_ndvi_data(days=30, crop_type='wheat'):
    """Generate realistic mock NDVI data for demo"""
    np.random.seed(42)  # For reproducibility
    
    # Different patterns for different crops
    patterns = {
        'wheat': {'trend': 0.001, 'noise': 0.05, 'base': 0.4},
        'rice': {'trend': 0.002, 'noise': 0.06, 'base': 0.5},
        'maize': {'trend': 0.0015, 'noise': 0.04, 'base': 0.45}
    }
    
    pattern = patterns.get(crop_type, patterns['wheat'])
    
    dates = pd.date_range(end=DEMO_CONFIG['demo_date'], periods=days, freq='D')
    
    # Create trend with some noise
    trend = np.linspace(0, pattern['trend'] * days, days)
    noise = np.random.normal(0, pattern['noise'], days)
    seasonal = 0.1 * np.sin(np.linspace(0, 4 * np.pi, days))
    
    ndvi = pattern['base'] + trend + seasonal + noise
    ndvi = np.clip(ndvi, 0.1, 0.95)  # Keep in realistic range
    
    return dates, ndvi

def generate_mock_window_df(crop_type='wheat', window_size=8):
    """Generate mock window DataFrame with all features"""
    dates, ndvi = generate_mock_ndvi_data(window_size, crop_type)
    
    # Create DataFrame with realistic values
    df = pd.DataFrame({'date': dates, 'NDVI': ndvi})
    
    # Generate correlated features
    df['GNDVI'] = df['NDVI'] * 0.9 + np.random.normal(0, 0.05, len(df))
    df['NDMI'] = df['NDVI'] * 0.8 + np.random.normal(0, 0.03, len(df))
    df['NDRE'] = df['NDVI'] * 0.85 + np.random.normal(0, 0.04, len(df))
    df['SAVI'] = df['NDVI'] * 1.1 + np.random.normal(0, 0.02, len(df))
    
    # Raw bands (reflectance values)
    df['B2'] = 0.1 + np.random.normal(0, 0.02, len(df))
    df['B3'] = 0.08 + np.random.normal(0, 0.02, len(df))
    df['B4'] = 0.15 + np.random.normal(0, 0.03, len(df))
    df['B5'] = 0.25 + np.random.normal(0, 0.04, len(df))
    df['B8'] = 0.4 + np.random.normal(0, 0.05, len(df))
    df['B11'] = 0.3 + np.random.normal(0, 0.04, len(df))
    df['B12'] = 0.25 + np.random.normal(0, 0.03, len(df))
    
    # Additional indices
    df['MSI'] = df['B11'] / (df['B8'] + 1e-6)
    df['NDWI'] = (df['B3'] - df['B8']) / (df['B3'] + df['B8'] + 1e-6)
    df['CIredEdge'] = (df['B8'] / (df['B5'] + 1e-6)) - 1
    
    # Clip values to realistic ranges
    for col in df.columns:
        if col != 'date':
            if 'ND' in col or 'GDVI' in col or 'SAVI' in col:
                df[col] = df[col].clip(-1, 1)
            elif col in ['B2', 'B3', 'B4', 'B5', 'B8', 'B11', 'B12']:
                df[col] = df[col].clip(0, 1)
            elif col == 'MSI':
                df[col] = df[col].clip(0, 3)
    
    return df

def main():
    # Page configuration
    st.set_page_config(
        page_title="Crop Growth Performance Analyzer",
        page_icon="🌱",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown(f"""
    <style>
    .main {{
        background-color: #f9f9f9;
    }}
    .stApp {{
        max-width: 1200px;
        margin: 0 auto;
    }}
    .score-card {{
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .metric-card {{
        background-color: white;
        border-radius: 8px;
        padding: 15px;
        margin: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    .header {{
        color: {COLORS['primary']};
        text-align: center;
        padding: 20px 0;
    }}
    .subheader {{
        color: {COLORS['secondary']};
        margin-bottom: 20px;
    }}
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("<h1 class='header'>🌾 Crop Growth Performance Analyzer</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subheader'>Monitor crop health and growth performance using satellite data</p>", unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/3067/3067256.png", width=100)
        st.markdown("## 🎯 Configuration")
        
        # Crop selection
        crop_type = st.selectbox(
            "Select Crop Type",
            CROPS,
            index=CROPS.index(DEMO_CONFIG['default_crop'])
        )
        
        # Growth stage
        stage = st.selectbox(
            "Select Growth Stage",
            options=list(STAGES.keys()),
            format_func=lambda x: STAGES[x],
            index=1  # Default to middle stage
        )
        
        # Location selection
        location_option = st.radio(
            "Location",
            ["Demo Location (Punjab, India)", "Custom Location"]
        )
        
        if location_option == "Custom Location":
            st.warning("For demo purposes, using mock data. Real Sentinel Hub integration requires API keys.")
        
        # Data source
        use_real_data = st.checkbox("Use Real Satellite Data", value=False)
        
        if use_real_data:
            st.info("⚠️ Requires valid Sentinel Hub credentials in data_fetcher.py")
        
        # Date selection
        analysis_date = st.date_input(
            "Analysis Date",
            value=DEMO_CONFIG['demo_date']
        )
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            analyze_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)
        with col2:
            reset_btn = st.button("🔄 Reset", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📊 About")
        st.info("""
        This demo calculates growth performance scores based on:
        - **Growth Rate**: NDVI trend over time
        - **Biomass**: Average vegetation density
        - **Stability**: Consistency of growth
        - **Stage Progress**: Alignment with expected growth stage
        """)
    
    # Main content
    if analyze_btn:
        # Generate or fetch data
        with st.spinner("Fetching and analyzing crop data..."):
            if DEMO_CONFIG['use_mock_data'] and not use_real_data:
                # Use mock data for demo
                window_df = generate_mock_window_df(crop_type)
                st.success(f"✓ Using mock data for {crop_type}")
            else:
                # Try to use real data (would need API setup)
                try:
                    from fetchers.data_fetcher import fetch_data_for_demo
                    location = DEMO_CONFIG['default_location']['corners']
                    result = fetch_data_for_demo(location, crop_type, analysis_date)
                    window_df = result['window_df'] if result else generate_mock_window_df(crop_type)
                    st.success("✓ Fetched real satellite data")
                except:
                    st.warning("⚠️ Could not fetch real data. Using mock data instead.")
                    window_df = generate_mock_window_df(crop_type)
        
        # Calculate scores
        ndvi_series = window_df['NDVI'].values
        scores = calculate_all_scores(ndvi_series, stage)
        report = calculate_health_report(scores)
        
        # Display results in columns
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.markdown(f"### 📍 Location: **{DEMO_CONFIG['default_location']['name']}**")
            st.markdown(f"### 🌾 Crop: **{crop_type.replace('_', ' ').title()}**")
            st.markdown(f"### 📅 Stage: **{STAGES[stage]}**")
        
        with col2:
            # Overall score card
            score_color = report['color']
            st.markdown(f"""
            <div class='score-card' style='border-left: 5px solid {score_color};'>
                <h3 style='color: {score_color}; margin-top: 0;'>Overall Score</h3>
                <h1 style='color: {score_color}; font-size: 48px; text-align: center;'>{report['overall_score']}</h1>
                <p style='text-align: center; font-size: 20px;'>{report['status']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            # Recommendation
            st.markdown(f"""
            <div class='score-card' style='border-left: 5px solid {COLORS['secondary']};'>
                <h4 style='color: {COLORS['secondary']}; margin-top: 0;'>Recommendation</h4>
                <p>{report['recommendation']}</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Visualization section
        st.markdown("---")
        st.markdown("## 📈 Visualizations")
        
        # Row 1: NDVI timeseries and radar chart
        col1, col2 = st.columns(2)
        
        with col1:
            dates = window_df['date']
            ndvi_values = window_df['NDVI'].values
            fig1 = create_ndvi_timeseries_plot(dates, ndvi_values, window_df)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            fig2 = create_score_radar_chart(scores)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Row 2: Score bar chart and metrics
        col1, col2 = st.columns(2)
        
        with col1:
            fig3 = create_score_bar_chart(scores, report['overall_score'])
            st.plotly_chart(fig3, use_container_width=True)
        
        with col2:
            # Display individual scores
            st.markdown("### 📊 Component Scores")
            for name, score in scores.items():
                col_name = name.replace('_', ' ').title()
                progress = score / 100
                
                color = "green" if score >= 80 else "blue" if score >= 60 else "orange" if score >= 40 else "red"
                
                st.markdown(f"""
                <div class='metric-card'>
                    <div style='display: flex; justify-content: space-between;'>
                        <span><strong>{col_name}</strong></span>
                        <span style='color: {color};'><strong>{score:.1f}</strong></span>
                    </div>
                    <div style='background: #e0e0e0; border-radius: 10px; height: 10px; margin-top: 5px;'>
                        <div style='background: {color}; width: {progress*100}%; height: 10px; border-radius: 10px;'></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Row 3: Multiple metrics timeseries
        st.markdown("### 📊 Multiple Health Metrics")
        fig4 = create_metric_timeseries(window_df)
        st.plotly_chart(fig4, use_container_width=True)
        
        # Data table
        with st.expander("📋 View Raw Data"):
            st.dataframe(window_df.round(3), use_container_width=True)
            
            # Download button
            csv = window_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Data as CSV",
                data=csv,
                file_name=f"{crop_type}_growth_data.csv",
                mime="text/csv"
            )
        
        # Statistics section
        st.markdown("---")
        st.markdown("## 📊 Statistics Summary")
        
        stats_cols = st.columns(4)
        metrics_to_show = ['NDVI', 'GNDVI', 'NDMI', 'NDRE']
        
        for i, metric in enumerate(metrics_to_show):
            with stats_cols[i]:
                mean_val = window_df[metric].mean()
                std_val = window_df[metric].std()
                trend = (window_df[metric].iloc[-1] - window_df[metric].iloc[0]) / len(window_df)
                
                st.metric(
                    label=metric,
                    value=f"{mean_val:.3f}",
                    delta=f"{trend:.4f}/day" if abs(trend) > 0.0001 else "Stable"
                )
                st.caption(f"Std Dev: {std_val:.3f}")
        
    else:
        # Initial state - show instructions
        st.markdown("""
        ## 👋 Welcome to the Crop Growth Performance Analyzer
        
        This tool helps farmers monitor crop health and growth performance using satellite data.
        
        ### 🚀 How to Use:
        1. **Select your crop type** from the sidebar
        2. **Choose the growth stage** of your crops
        3. **Configure location** (demo or custom)
        4. **Click 'Analyze'** to generate performance scores
        
        ### 📊 What You'll Get:
        - **Overall Health Score** (0-100)
        - **Component Scores** for different growth aspects
        - **NDVI Time Series** visualization
        - **Detailed Recommendations** for crop management
        - **Raw Data** for further analysis
        
        ### 🌱 About the Scores:
        - **Growth Rate**: Measures how fast crops are growing
        - **Biomass**: Estimates vegetation density
        - **Stability**: Checks consistency of growth
        - **Stage Progress**: Compares with expected growth for the stage
        
        ---
        
        *Ready to start? Configure your settings in the sidebar and click **Analyze**!*
        """)
        
        # Show example visualization
        st.markdown("### 📈 Example Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("""
            **Example: Wheat Field in Punjab**
            - Crop: Wheat
            - Stage: Middle (Reproductive)
            - Location: Punjab, India
            - Analysis Date: Dec 19, 2024
            """)
        
        with col2:
            st.success("""
            **Expected Results:**
            - Overall Score: 75-85 (Good to Excellent)
            - Growth Rate: Improving
            - Biomass: Optimal
            - Stability: Consistent
            - Recommendation: Continue current practices
            """)

if __name__ == "__main__":
    main()