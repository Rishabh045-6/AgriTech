// screens/CropSelectionScreen.tsx
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator
} from 'react-native';

type CropSelectionScreenProps = {
  route: any;
  navigation: any;
};

export default function CropSelectionScreen({ route, navigation }: CropSelectionScreenProps) {
  const { farmerId, plotCoordinates } = route.params;
  const [selectedCrop, setSelectedCrop] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const crops = [
    { value: 'rice', label: 'Rice', color: '#FF9800' },
    { value: 'wheat', label: 'Wheat', color: '#FFC107' },
    { value: 'maize', label: 'Maize', color: '#FFEB3B' },
    { value: 'chickpea', label: 'Chickpea', color: '#4CAF50' },
    { value: 'pigeon_pea', label: 'Pigeon Pea', color: '#8BC34A' },
    { value: 'beans', label: 'Beans', color: '#CDDC39' },
    { value: 'lentils', label: 'Lentils', color: '#FF9800' }
  ];

  const handleCropSelect = (crop: string) => {
    setSelectedCrop(crop);
  };

  const handleConfirm = async () => {
    if (!selectedCrop) {
      Alert.alert('⚠️ Select Crop', 'Please select a crop type');
      return;
    }

    setLoading(true); // ✅ Start loading

    try {
      const API_URL = 'http://10.67.1.211:3001';

      const response = await fetch(`${API_URL}/api/run-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmerId,
          cropType: selectedCrop
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const results = await response.json();

      navigation.navigate('Results', {
        farmerId,
        cropType: selectedCrop,
        plotCoordinates,
        modelResults: results
      });

    } catch (error: any) {
      console.error('Model error:', error);
      Alert.alert('❌ Error', 'Failed to analyze crop');
    } finally {
      setLoading(false); // ✅ Stop loading
    }
  };

  // ✅ Show loading screen
  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#2E8B57" />
        <Text style={styles.loadingText}>Analyzing using satellite data...</Text>
        <Text style={styles.subLoadingText}>Processing NDVI trends and crop health metrics</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Select Crop Type</Text>
      <Text style={styles.subtitle}>What crop is grown in this field?</Text>

      <ScrollView style={styles.cropsContainer}>
        {crops.map((crop) => (
          <TouchableOpacity
            key={crop.value}
            style={[
              styles.cropOption,
              selectedCrop === crop.value && { 
                backgroundColor: crop.color,
                borderColor: crop.color
              }
            ]}
            onPress={() => handleCropSelect(crop.value)}
          >
            <Text style={[
              styles.cropText,
              selectedCrop === crop.value && styles.selectedCropText
            ]}>
              {crop.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <TouchableOpacity
        style={[
          styles.confirmButton,
          !selectedCrop && styles.confirmButtonDisabled
        ]}
        onPress={handleConfirm}
        disabled={!selectedCrop}
      >
        <Text style={styles.confirmButtonText}>
          Analyze {selectedCrop ? selectedCrop.toUpperCase() : 'Crop'}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
    padding: 20
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#F5F5F5'
  },
  loadingText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginTop: 20,
    textAlign: 'center'
  },
  subLoadingText: {
    fontSize: 14,
    color: '#666',
    marginTop: 10,
    textAlign: 'center',
    paddingHorizontal: 20
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
    color: '#2E8B57'
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 30,
    color: '#666'
  },
  cropsContainer: {
    flex: 1,
    marginBottom: 20
  },
  cropOption: {
    backgroundColor: 'white',
    padding: 15,
    marginVertical: 5,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#E0E0E0'
  },
  selectedCropText: {
    color: 'white',
    fontWeight: 'bold'
  },
  cropText: {
    fontSize: 18,
    textAlign: 'center'
  },
  confirmButton: {
    backgroundColor: '#4CAF50',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center'
  },
  confirmButtonDisabled: {
    backgroundColor: '#BDBDBD'
  },
  confirmButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold'
  }
});