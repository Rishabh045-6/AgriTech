import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Platform,
  ActivityIndicator
} from 'react-native';

type PlotFormScreenProps = {
  route: any;
  navigation: any;
};

export default function PlotFormScreen({ route, navigation }: PlotFormScreenProps) {
  const { farmerId, username } = route.params || {};
  
  const [selectedCrop, setSelectedCrop] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const CROPS = [
    { name: 'rice', label: 'Rice' },
    { name: 'wheat', label: 'Wheat' },
    { name: 'maize', label: 'Maize' },
    { name: 'chickpea', label: 'Chickpea' },
    { name: 'pigeon_pea', label: 'Pigeon Pea' },
    { name: 'bean', label: 'Bean' },
    { name: 'lentils', label: 'Lentils' }
  ];

  const handleStartPlotting = () => {
    if (!selectedCrop) {
      Alert.alert('⚠️ Select Crop', 'Please select a crop type before starting');
      return;
    }

    // Navigate to map screen with selected crop
    navigation.navigate('Map', {
      farmerId,
      username,
      selectedCrop
    });
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🌾 Crop Analysis</Text>
        <Text style={styles.farmerInfo}>Farmer: {username || 'Unknown'}</Text>
        <Text style={styles.farmerId}>ID: {farmerId || 'N/A'}</Text>
      </View>

      {/* Form Content */}
      <View style={styles.formContainer}>
        <Text style={styles.title}>Start New Plot Analysis</Text>
        
        <Text style={styles.sectionTitle}>Select Crop Type:</Text>
        <View style={styles.cropGrid}>
          {CROPS.map((crop) => (
            <TouchableOpacity
              key={crop.name}
              style={[
                styles.cropButton,
                selectedCrop === crop.name ? styles.selectedCropButton : {}
              ]}
              onPress={() => setSelectedCrop(crop.name)}
            >
              <Text style={[
                styles.cropButtonText,
                selectedCrop === crop.name ? styles.selectedCropButtonText : {}
              ]}>
                {crop.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        <TouchableOpacity
          style={[styles.startButton, !selectedCrop && styles.startButtonDisabled]}
          onPress={handleStartPlotting}
          disabled={!selectedCrop}
        >
          <Text style={styles.startButtonText}>
            Start Plotting →
          </Text>
        </TouchableOpacity>
      </View>

      {/* Footer */}
      <View style={styles.footer}>
        <Text style={styles.footerText}>
          Tap "Start Plotting" to begin drawing your plot on the map
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    backgroundColor: '#2E8B57',
    padding: 15,
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: 'white',
    marginBottom: 5,
  },
  farmerInfo: {
    fontSize: 14,
    color: '#e0e0e0',
  },
  farmerId: {
    fontSize: 12,
    color: '#b0b0b0',
  },
  formContainer: {
    flex: 1,
    padding: 20,
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    textAlign: 'center',
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 10,
  },
  cropGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  cropButton: {
    backgroundColor: '#e0e0e0',
    paddingVertical: 10,
    paddingHorizontal: 15,
    borderRadius: 8,
    margin: 5,
  },
  selectedCropButton: {
    backgroundColor: '#2E8B57',
  },
  cropButtonText: {
    color: '#333',
    fontSize: 14,
  },
  selectedCropButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  startButton: {
    backgroundColor: '#4CAF50',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 20,
  },
  startButtonDisabled: {
    backgroundColor: '#8BC34A',
  },
  startButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: 'bold',
  },
  footer: {
    backgroundColor: '#2E8B57',
    padding: 15,
    alignItems: 'center',
  },
  footerText: {
    color: 'white',
    fontSize: 14,
  },
});