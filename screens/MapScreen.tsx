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
import {
  request,
  PERMISSIONS,
  RESULTS,
} from 'react-native-permissions';
import axios from 'axios';

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

  // Request location permission
  const requestLocationPermission = async () => {
    const permission =
      Platform.OS === 'android'
        ? PERMISSIONS.ANDROID.ACCESS_FINE_LOCATION
        : PERMISSIONS.IOS.LOCATION_WHEN_IN_USE;

    const result = await request(permission);
    return result === RESULTS.GRANTED;
  };

  // Get current location
  const getCurrentLocation = async () => {
    setLoadingLocation(true);

    const granted = await requestLocationPermission();
    if (!granted) {
      Alert.alert(
        'Permission Required',
        'Please enable location permission in settings'
      );
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
      (error) => {
        console.log('GPS ERROR:', error);
        Alert.alert(
          'Location Error',
          'Unable to fetch location. Make sure GPS is enabled.'
        );
        setLoadingLocation(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 20000,
        maximumAge: 1000,
      }
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

    try {
      const API_URL =
        Platform.OS === 'android'
          ? 'http://192.168.31.20:3001'
          : 'http://localhost:3001'; // your local IP

      const response = await fetch(`${API_URL}/api/save-plot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmerId: 'farmer_' + new Date().getTime(), // Unique ID
          plotCoordinates: points.map(p => [p.latitude, p.longitude]),
        }),
      });

      Alert.alert('✅ Success', 'Plot saved to PostGIS!');
      console.log('Response:', response.data);
    } catch (error: any) {
      console.error('❌ FULL SAVE ERROR:', error); // ← ADD THIS
      Alert.alert(
        '❌ Error',
        error.response?.data?.error ||
          'Could not connect to backend'
      );
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
