import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Platform,
  ActivityIndicator,
  Modal,
  Dimensions
} from 'react-native';
import MapView, { Polygon, Marker } from 'react-native-maps';
import Geolocation from '@react-native-community/geolocation';
import { PermissionsAndroid } from 'react-native';
import { apiFetch } from '../config/api';

type MapScreenProps = {
  route: any;
  navigation: any;
};



export default function MapScreen({ route, navigation }: MapScreenProps) {

  
  const { farmerId, selectedCrop } = route.params || {};

  const getCurrentLocation = useCallback(() => {
    Geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setRegion({
          latitude,
          longitude,
          latitudeDelta: 0.01,
          longitudeDelta: 0.01,
        });
      },
      (error) => {
        console.log('Location error:', error);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 10000 }
    );
  }, []);

  const requestLocationPermission = useCallback(async () => {
    if (Platform.OS === 'android') {
      try {
        const granted = await PermissionsAndroid.request(
          PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION,
          {
            title: 'Location Permission',
            message: 'This app needs access to location to help with crop analysis.',
            buttonNeutral: 'Ask Me Later',
            buttonNegative: 'Cancel',
            buttonPositive: 'OK',
          }
        );

        if (granted === PermissionsAndroid.RESULTS.GRANTED) {
          getCurrentLocation();
        }
      } catch (err) {
        console.warn(err);
      }
    } else {
      // iOS
      getCurrentLocation();
    }
  }, [getCurrentLocation]);

  useEffect(() => {
    if (!farmerId || !selectedCrop) {
      navigation.navigate('PlotForm');
      return;
    }

    requestLocationPermission();
  }, [farmerId, selectedCrop, navigation, requestLocationPermission]);

  const [region, setRegion] = useState({
    latitude: 26.163054622, // Default to your area
    longitude: 91.738211922,
    latitudeDelta: 0.01,
    longitudeDelta: 0.01,
  });


  const [points, setPoints] = useState<{ latitude: number; longitude: number }[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('Analyzing crop data...');
  const mapRef = useRef<MapView>(null);

  useEffect(() => {
    if (!farmerId || !selectedCrop) {
      setTimeout(() => {
        navigation.navigate('PlotForm');
      }, 0);
      return;
    }

    requestLocationPermission();
  }, [farmerId, selectedCrop, navigation, requestLocationPermission]);

  // Optimized map press handler
  const handleMapPress = useCallback((e: any) => {
    const { latitude, longitude } = e.nativeEvent.coordinate;
    setPoints(prev => [...prev, { latitude, longitude }]);
  }, []);

  const clearPoints = useCallback(() => {
    setPoints([]);
  }, []);

  const handleConfirm = useCallback(async () => {
    if (points.length < 3) {
      Alert.alert('⚠️ Not enough points', 'Draw at least 3 points to create a plot');
      return;
    }

    setIsLoading(true);
    setLoadingMessage('Loading results using satellite data...');

    try {
      // Get unique coordinates
      const uniqueCoordinates = points.map(p => ({
        latitude: p.latitude,
        longitude: p.longitude
      }));

      // Close polygon if not already closed
      if (uniqueCoordinates.length >= 3) {
        const firstPoint = uniqueCoordinates[0];
        const lastPoint = uniqueCoordinates[uniqueCoordinates.length - 1];

        if (firstPoint.latitude !== lastPoint.latitude || firstPoint.longitude !== lastPoint.longitude) {
          uniqueCoordinates.push(firstPoint);
        }
      }

      // Save plot to database
      const saveResponse = await apiFetch(`/api/save-plot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmerId,
          plotCoordinates: uniqueCoordinates.map(p => [p.latitude, p.longitude]),
          cropType: selectedCrop
        }),
      });

      if (!saveResponse.ok) {
        const errorText = await saveResponse.text();
        throw new Error(`HTTP ${saveResponse.status}: ${errorText}`);
      }

      // Get model results from backend
      // model prediction may take a while, give it up to 60 seconds
      const response = await apiFetch(
        `/api/run-model`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            farmerId,
            cropType: selectedCrop,
          }),
        },
        60000 // 60 second timeout
      );

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const results = await response.json();

      navigation.navigate('Results', {
        farmerId,
        cropType: selectedCrop,
        plotCoordinates: uniqueCoordinates,
        modelResults: results
      });

    } catch (error: any) {
      console.error('Model error:', error);
      // show a more helpful error message if available
      Alert.alert(
        '❌ Analysis failed',
        error?.message || 'Failed to analyze crop. Please try again.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [points, farmerId, selectedCrop, navigation]);

  // Optimized region change handler
  const handleRegionChange = useCallback((newRegion: any) => {
    // Only update if region changed significantly to avoid performance issues
    setRegion(newRegion);
  }, []);

  const { height } = Dimensions.get('window');
  const mapHeight = height * 0.8;

  if (!farmerId || !selectedCrop) {
    return (
      <View style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#2E8B57" />
          <Text style={styles.loadingText}>Loading...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Simple Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Draw Your Plot</Text>
        <Text style={styles.cropInfo}>Crop: {selectedCrop.toUpperCase()}</Text>
      </View>

      {/* Optimized Map */}
      <MapView
        ref={mapRef}
        style={[styles.map, { height: mapHeight }]}
        initialRegion={region}
        onRegionChange={handleRegionChange}
        onPress={handleMapPress}
        showsUserLocation={true}
        showsMyLocationButton={true}
        scrollEnabled={true}
        zoomEnabled={true}
        pitchEnabled={false}
        rotateEnabled={false}
      // Remove unnecessary props that cause re-renders
      >
        {points.map((point, index) => (
          <Marker
            key={index.toString()}
            coordinate={point}
            pinColor="red"
          />
        ))}

        {points.length >= 3 && (
          <Polygon
            coordinates={points}
            strokeColor="#9708cc"
            fillColor="#9708cc30"
            strokeWidth={3}
          />
        )}
      </MapView>

      {/* Simple Controls */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={styles.clearButton}
          onPress={clearPoints}
        >
          <Text style={styles.clearButtonText}>Clear</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.confirmButton}
          onPress={handleConfirm}
          disabled={points.length < 3}
        >
          <Text style={styles.confirmButtonText}>
            Analyze ({points.length} points)
          </Text>
        </TouchableOpacity>
      </View>

      {/* Loading Modal */}
      <Modal
        transparent={true}
        visible={isLoading}
        animationType="fade"
      >
        <View style={styles.loadingModal}>
          <View style={styles.loadingContent}>
            <ActivityIndicator size="large" color="#2E8B57" />
            <Text style={styles.loadingText}>{loadingMessage}</Text>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#333',
  },
  header: {
    backgroundColor: '#2E8B57',
    padding: 15,
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: 'white',
  },
  cropInfo: {
    fontSize: 14,
    color: 'white',
    marginTop: 5,
  },
  map: {
    flex: 1,
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 15,
    backgroundColor: 'white',
    elevation: 2,
  },
  clearButton: {
    backgroundColor: '#f44336',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
  },
  clearButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  confirmButton: {
    backgroundColor: '#4CAF50',
    paddingVertical: 12,
    paddingHorizontal: 20,
    borderRadius: 8,
  },
  confirmButtonDisabled: {
    backgroundColor: '#8BC34A',
  },
  confirmButtonText: {
    color: 'white',
    fontWeight: 'bold',
  },
  loadingModal: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingContent: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 10,
    alignItems: 'center',
    width: '80%',
  },
});