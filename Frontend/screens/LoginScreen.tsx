import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

type LoginScreenProps = {
  navigation: any;
};

export default function LoginScreen({ navigation }: LoginScreenProps) {
  const [username, setUsername] = useState('');
  const [isLoading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!username.trim()) {
      Alert.alert('Error', 'Please enter a username');
      return;
    }

    setLoading(true);

    try {
      // Production API URL - FIXED: No process usage
      const isDevelopment = __DEV__;
      const API_BASE_URL = !isDevelopment
        ? 'https://database-personal012-6ab6673d.koyeb.app'  // Your Azure URL
        : 'http://192.168.31.20:3001';  // Local dev

      const response = await fetch(`${API_BASE_URL}/api/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: username.trim() }),
      });

      const data = await response.json();

      if (data.success) {
        // Store token securely
        await AsyncStorage.setItem('userToken', data.token || 'temp-token');

        // ✅ FIXED: Navigate to PlotForm with proper params (not reset)
        navigation.navigate('PlotForm', {
          farmerId: data.farmerId || 'temp-farmer-id',
          username: data.username || username,
          cropType: 'rice' // Default crop type for demo
        });
      } else {
        Alert.alert('Login Failed', data.error || 'Invalid credentials');
      }
    } catch (error) {
      console.error('Login error:', error);
      Alert.alert('Error', 'Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.loginCard}>
        <Text style={styles.title}>🌾 Agritech</Text>
        <Text style={styles.subtitle}>Crop Analysis System</Text>

        <Text style={styles.label}>Enter Your Name</Text>
        <TextInput
          style={styles.input}
          value={username}
          onChangeText={setUsername}
          placeholder="John Doe"
          placeholderTextColor="#999"
          autoCapitalize="words"
          autoCorrect={false}
          maxLength={50}
        />

        <TouchableOpacity
          style={styles.loginButton}
          onPress={handleLogin}
          disabled={isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.loginButtonText}>Continue →</Text>
          )}
        </TouchableOpacity>
      </View>

      <Text style={styles.infoText}>
        Your unique farmer ID will be saved for future use
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#2a8444ff',
    justifyContent: 'center',
    padding: 20
  },
  header: {
    alignItems: 'center',
    marginBottom: 40
  },
  title: {
    fontSize: 38,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 10
  },
  subtitle: {
    fontSize: 18,
    color: '#666'
  },
  form: {
    textAlign: 'left',
    width: '100%',
    backgroundColor: 'white',
    padding: 30,
    borderRadius: 12,
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4
  },
  label: {
    textAlign: 'left',
    paddingVertical: 10,
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10
  },
  input: {
    textAlign: 'left',
    width: '100%', height: 50, borderWidth: 1, borderColor: '#ddd', borderRadius: 8, paddingHorizontal: 15, fontSize: 16, color: '#333', marginBottom: 20
  },
  loginButton: {
    backgroundColor: '#2196F3',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 15
  },
  loginButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16
  },
  loginCard: {
    backgroundColor: 'white',
    padding: 30,
    borderRadius: 15,
    width: '100%',
    alignItems: 'center',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8
  },
  infoText: {
    marginTop: 20,
    fontSize: 14,
    color: '#000000ff',
    textAlign: 'center',
    opacity: 0.8
  },
  note: {
    fontSize: 12,
    color: '#2499a6ff',
    textAlign: 'center',
    fontStyle: 'italic'
  }
});