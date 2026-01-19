import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Platform,
  ActivityIndicator
} from 'react-native';

type LoginScreenProps = {
  navigation: any;
};

export default function LoginScreen({ navigation }: LoginScreenProps) {
  const [username, setUsername] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    if (!username.trim()) {
      Alert.alert('⚠️ Required', 'Please enter a username');
      return;
    }

    setIsLoading(true);

    try {
      const API_URL = Platform.OS === 'android'
        ? 'http://10.67.9.194:3001'
        : 'http://localhost:3001';

      const response = await fetch(`${API_URL}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: username.trim() }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();

      if (data.success) {
        // Navigate to form screen with farmerId and username
        navigation.navigate('PlotForm', {
          farmerId: data.farmerId,
          username: data.username
        });
      } else {
        throw new Error(data.error || 'Login failed');
      }
    } catch (error: any) {
      console.error('Login error:', error);
      Alert.alert('❌ Error', error.message || 'Failed to login');
    } finally {
      setIsLoading(false);
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
    backgroundColor: '#2E8B57',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
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
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 5
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 30,
    textAlign: 'center'
  },
  label: {
    fontSize: 16,
    color: '#333',
    alignSelf: 'flex-start',
    marginBottom: 10
  },
  input: {
    width: '100%',
    height: 50,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    paddingHorizontal: 15,
    fontSize: 16,
    color: '#333',
    marginBottom: 20
  },
  loginButton: {
    backgroundColor: '#2E8B57',
    width: '100%',
    height: 50,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 10
  },
  loginButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold'
  },
  infoText: {
    color: 'white',
    marginTop: 20,
    textAlign: 'center',
    fontSize: 14,
    opacity: 0.8
  }
});