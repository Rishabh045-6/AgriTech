// screens/MapScreen.tsx
import React, { useState, useEffect } from 'react';
import {
  View,
  StyleSheet,
  Alert,
  TouchableOpacity,
  Text,
  Platform,
} from 'react-native';
import MapView, { Polygon, Marker } from 'react-native-maps';
import Geolocation from '@react-native-community/geolocation';
import { request, PERMISSIONS, RESULTS } from 'react-native-permissions';
import { useNavigation } from '@react-navigation/native'; // ← Add this

type Point = {
  latitude: number;
  longitude: number;
};

type MapScreenProps = {
  navigation: any;
};

export default function MapScreen({ navigation }: MapScreenProps) {
  const [points, setPoints] = useState<Point[]>([]);
  const [region, setRegion] = useState({
    latitude: 20.5937,
    longitude: 78.9629,
    latitudeDelta: 8,
    longitudeDelta: 8,
  });
  const [loadingLocation, setLoadingLocation] = useState(false);

  const requestLocationPermission = async () => {
    const permission =
      Platform.OS === 'android'
        ? PERMISSIONS.ANDROID.ACCESS_FINE_LOCATION
        : PERMISSIONS.IOS.LOCATION_WHEN_IN_USE;

    const result = await request(permission);
    return result === RESULTS.GRANTED;
  };

  const getCurrentLocation = async () => {
    setLoadingLocation(true);

    const granted = await requestLocationPermission();
    if (!granted) {
      Alert.alert('Permission Required', 'Enable location permission');
      setLoadingLocation(false);
      return;
    }

    Geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setRegion({
          latitude,
          longitude,
          latitudeDelta: 0.02,
          longitudeDelta: 0.02,
        });
        setLoadingLocation(false);
      },
      () => {
        Alert.alert('Location Error', 'Unable to fetch GPS location');
        setLoadingLocation(false);
      },
      { enableHighAccuracy: true, timeout: 20000 }
    );
  };

  useEffect(() => {
    getCurrentLocation();
  }, []);

  const handleMapPress = (e: any) => {
    const { latitude, longitude } = e.nativeEvent.coordinate;
    setPoints((prev) => [...prev, { latitude, longitude }]);
  };

  const handleSavePlot = async () => {
    if (points.length < 3) {
      Alert.alert('⚠️ Not enough points', 'Draw at least 3 points');
      return;
    }

    // ✅ Generate farmerId
    const farmerId = `farmer_${Date.now()}`;

    try {
      const API_URL =
        Platform.OS === 'android'
          ? 'http://192.168.31.20:3001'  // Your PC's IP
          : 'http://localhost:3001';

      // ✅ Save plot to backend (PostGIS)
      const response = await fetch(`${API_URL}/api/save-plot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmerId,
          plotCoordinates: points.map(p => [p.latitude, p.longitude])
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      // ✅ Navigate to Crop Selection screen (NEW)
      navigation.navigate('CropSelection', {
        farmerId,
        plotCoordinates: points.map(p => [p.latitude, p.longitude])
      });

    } catch (error: any) {
      console.error('❌ FULL SAVE ERROR:', error);

      let errorMessage = 'Failed to save plot';
      if (error.message?.includes('Network')) {
        errorMessage = 'Cannot connect to backend. Is it running?';
      } else if (error.message?.includes('HTTP')) {
        errorMessage = `Backend error: ${error.message}`;
      }

      Alert.alert('❌ Error', errorMessage);
    }
  };

  const handleClear = () => setPoints([]);

  return (
    <View style={styles.container}>
      <MapView
        style={styles.map}
        region={region}
        onPress={handleMapPress}
        showsUserLocation
        showsMyLocationButton
      >
        {points.map((point, index) => (
          <Marker key={index} coordinate={point} />
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

      <View style={styles.controls}>
        <TouchableOpacity
          onPress={handleClear}
          style={[styles.button, styles.clearBtn]}
        >
          <Text style={styles.buttonText}>Clear</Text>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={handleSavePlot}
          style={[styles.button, styles.saveBtn]}
        >
          <Text style={styles.buttonText}>Save Plot</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
  controls: {
    position: 'absolute',
    bottom: 40,
    left: 20,
    right: 20,
    flexDirection: 'row',
    gap: 10,
  },
  button: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  clearBtn: { backgroundColor: '#f44336' },
  saveBtn: { backgroundColor: '#4CAF50' },
  buttonText: { color: '#fff', fontWeight: 'bold', fontSize: 16 },
});