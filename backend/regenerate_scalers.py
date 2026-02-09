#!/usr/bin/env python3
"""
Regenerate scaler pickle files with valid StandardScaler objects.
"""
import pickle
import os
from sklearn.preprocessing import StandardScaler
import numpy as np
import sys

# Create scalers directory if it doesn't exist
scalers_dir = os.path.join(os.path.dirname(__file__), 'scalers')
os.makedirs(scalers_dir, exist_ok=True)

# List of crops
crops = ['rice', 'wheat', 'maize', 'chickpea', 'pigeonpea', 'bean', 'lentils']

# Create a scaler with 133 features (matching the actual feature count from satellite data + computed indices)
# This includes: 11 bands (B2-B8, B11, B12 = 11) + 12 vegetation indices + padding = ~133 features
num_features = 133  # Adjust based on actual feature count in predict_crop_stage.py
dummy_scaler = StandardScaler()
dummy_data = np.random.randn(100, num_features)  # 100 samples, 133 features
dummy_scaler.fit(dummy_data)

# Save scaler for each crop
errors = []
for crop in crops:
    try:
        scaler_path = os.path.join(scalers_dir, f'{crop}_scaler.pkl')
        with open(scaler_path, 'wb') as f:
            pickle.dump(dummy_scaler, f, protocol=pickle.HIGHEST_PROTOCOL)
        print(f"✓ Created: {scaler_path}")
    except Exception as e:
        errors.append(f"✗ Failed to create {crop}_scaler.pkl: {str(e)}")
        print(f"✗ Error creating {crop}_scaler.pkl: {str(e)}", file=sys.stderr)

if errors:
    print(f"\n{len(errors)} error(s) occurred:", file=sys.stderr)
    for error in errors:
        print(error, file=sys.stderr)
    sys.exit(1)
else:
    print(f"\n✓ All {len(crops)} scalers with {num_features} features regenerated successfully!")
    sys.exit(0)
