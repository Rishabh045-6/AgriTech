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

  const requestLocationPermission = async () => {
    const permission =
      Platform.OS === 'android'
        ? PERMISSIONS.ANDROID.ACCESS_FINE_LOCATION
        : PERMISSIONS.IOS.LOCATION_WHEN_IN_USE;
    return (await request(permission)) === RESULTS.GRANTED;
  };

  useEffect(() => {
    requestLocationPermission().then(granted => {
      if (!granted) return;
      Geolocation.getCurrentPosition(pos => {
        setRegion({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          latitudeDelta: 0.02,
          longitudeDelta: 0.02,
        });
      });
    });
  }, []);

  const handleMapPress = (e: any) => {
    const { latitude, longitude } = e.nativeEvent.coordinate;
    setPoints(p => [...p, { latitude, longitude }]);
  };

  const handleSavePlot = async () => {
    if (points.length < 3) {
      Alert.alert('⚠️ Not enough points', 'Draw at least 3 points');
      return;
    }

    const farmerId = `farmer_${Date.now()}`;
    const API_URL =
      Platform.OS === 'android'
        ? 'http://192.168.31.20:3001'
        : 'http://localhost:3001';

    try {
      const res = await fetch(`${API_URL}/api/save-plot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmerId,
          plotCoordinates: points.map(p => [p.latitude, p.longitude]),
        }),
      });

      if (!res.ok) throw new Error('Save failed');

      navigation.navigate('Results', { farmerId });

    } catch {
      Alert.alert('❌ Error', 'Failed to save plot');
    }
  };

  return (
    <View style={styles.container}>
      <MapView style={styles.map} region={region} onPress={handleMapPress}>
        {points.map((p, i) => <Marker key={i} coordinate={p} />)}
        {points.length >= 3 && (
          <Polygon coordinates={points} strokeColor="#9708cc" fillColor="#9708cc30" />
        )}
      </MapView>

      <View style={styles.controls}>
        <TouchableOpacity onPress={() => setPoints([])} style={[styles.button, styles.clearBtn]}>
          <Text style={styles.buttonText}>Clear</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={handleSavePlot} style={[styles.button, styles.saveBtn]}>
          <Text style={styles.buttonText}>Save Plot</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },
  controls: { position: 'absolute', bottom: 40, left: 20, right: 20, flexDirection: 'row', gap: 10 },
  button: { flex: 1, paddingVertical: 12, borderRadius: 8, alignItems: 'center' },
  clearBtn: { backgroundColor: '#f44336' },
  saveBtn: { backgroundColor: '#4CAF50' },
  buttonText: { color: '#fff', fontWeight: 'bold' },
});
