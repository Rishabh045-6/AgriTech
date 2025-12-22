// screens/ResultsScreen.tsx
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Alert,
  Platform,
  TouchableOpacity,
  Dimensions,
  ActivityIndicator
} from 'react-native';

type ResultsScreenProps = {
  route: any;
  navigation: any;
};

export default function ResultsScreen({ route, navigation }: ResultsScreenProps) {
  const { farmerId, cropType, plotCoordinates, modelResults } = route.params;
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (modelResults) {
      setResults(modelResults);
      setLoading(false);
    } else {
      fetchResults();
    }
  }, [farmerId, cropType]);

  const fetchResults = async () => {
    setLoading(true); // ✅ Start loading
    try {
      const API_URL = Platform.OS === 'android'
        ? 'http://192.168.31.20:3001'
        : 'http://localhost:3001';

      const response = await fetch(`${API_URL}/api/run-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmerId,
          cropType
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (error: any) {
      console.error('Fetch error:', error);
      setError(error.message || 'Failed to load analysis');
    } finally {
      setLoading(false); // ✅ Stop loading
    }
  };

  // ✅ Show loading screen
  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#2E8B57" />
        <Text style={styles.loadingText}>Analyzing crop data...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>Error: {error}</Text>
      </View>
    );
  }

  if (!results || !results.success) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>No results available</Text>
      </View>
    );
  }

  const { stage, confidence, ndviTrend, recommendations, healthMetrics } = results;

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>🌾 Crop Analysis Results</Text>
        <Text style={styles.subtitle}>{cropType.toUpperCase()}</Text>
      </View>

      {/* Stage Prediction Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Growth Stage Prediction</Text>
        <View style={styles.predictionContainer}>
          <Text style={styles.stageText}>{stage}</Text>
          <Text style={styles.confidenceText}>{(confidence * 100).toFixed(1)}% confidence</Text>
        </View>
      </View>

      {/* Confidence Meter */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Confidence Level</Text>
        <View style={styles.meterContainer}>
          <View style={[styles.meterFill, { width: `${confidence * 100}%` }]} />
          <Text style={styles.meterText}>{(confidence * 100).toFixed(1)}%</Text>
        </View>
      </View>

      {/* NDVI Trend Chart */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>NDVI Trend Over Time</Text>
        <View style={styles.chartContainer}>
          {ndviTrend && ndviTrend.length > 0 && (
            <View style={styles.linearChart}>
              {/* Chart line */}
              <View style={styles.chartLine}>
                {ndviTrend.map((point: any, index: number) => (
                  <View key={index} style={styles.chartPoint}>
                    <Text style={styles.chartValue}>{point.ndvi.toFixed(2)}</Text>
                    <View style={[styles.chartBar, { height: point.ndvi * 100 }]} />
                    <Text style={styles.chartDate}>{new Date(point.date).toLocaleDateString()}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}
        </View>
      </View>

      {/* Health Metrics */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Soil Health Metrics</Text>
        <View style={styles.healthMetricsContainer}>
          {healthMetrics && Object.entries(healthMetrics).map(([key, value]: [string, any]) => (
            <View key={key} style={styles.healthMetricCard}>
              <Text style={styles.healthMetricName}>{key.charAt(0).toUpperCase() + key.slice(1)}</Text>
              <Text style={styles.healthMetricValue}>{value.level}</Text>
              <Text style={styles.healthMetricStatus}>{value.status}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Recommendations */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>💡 Recommendations</Text>
        <View style={styles.recommendationsContainer}>
          {recommendations && recommendations.map((rec: string, index: number) => (
            <View key={index} style={styles.recommendationItem}>
              <Text style={styles.recommendationText}>• {rec}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Back Button */}
      <TouchableOpacity
        style={styles.backButton}
        onPress={() => navigation.goBack()}
      >
        <Text style={styles.backButtonText}>← Back to Map</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const { width } = Dimensions.get('window');

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F8F9FA',
    padding: 16
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
  errorText: {
    fontSize: 16,
    color: '#f44336',
    textAlign: 'center',
    marginTop: 50
  },
  header: {
    alignItems: 'center',
    marginBottom: 20
  },
  title: {
    fontSize: 26,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 5
  },
  subtitle: {
    fontSize: 18,
    color: '#666'
  },
  card: {
    backgroundColor: 'white',
    padding: 20,
    marginBottom: 16,
    borderRadius: 12,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 15,
    color: '#333',
    textAlign: 'center'
  },
  predictionContainer: {
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#E8F5E8',
    borderRadius: 10
  },
  stageText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 5
  },
  confidenceText: {
    fontSize: 16,
    color: '#666'
  },
  meterContainer: {
    height: 20,
    backgroundColor: '#E0E0E0',
    borderRadius: 10,
    overflow: 'hidden',
    position: 'relative'
  },
  meterFill: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 10
  },
  meterText: {
    position: 'absolute',
    right: 10,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
    fontSize: 12,
    fontWeight: 'bold',
    color: 'white'
  },
  chartContainer: {
    padding: 10
  },
  linearChart: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    height: 150,
    backgroundColor: '#F0F0F0',
    borderRadius: 8,
    padding: 10
  },
  chartLine: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'flex-end',
    width: '100%',
    height: '100%'
  },
  chartPoint: {
    alignItems: 'center',
    marginHorizontal: 5
  },
  chartValue: {
    fontSize: 10,
    color: '#666',
    marginBottom: 5
  },
  chartBar: {
    backgroundColor: '#2196F3',
    width: 12,
    borderRadius: 2,
    marginBottom: 5
  },
  chartDate: {
    fontSize: 8,
    color: '#666',
    textAlign: 'center'
  },
  healthMetricsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-around'
  },
  healthMetricCard: {
    width: (width - 60) / 2, // Two cards per row
    backgroundColor: '#F8F9FA',
    padding: 12,
    borderRadius: 8,
    marginBottom: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E0E0E0'
  },
  healthMetricName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 5
  },
  healthMetricValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 3
  },
  healthMetricStatus: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center'
  },
  recommendationsContainer: {
    paddingVertical: 10
  },
  recommendationItem: {
    backgroundColor: '#E8F5E8',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8
  },
  recommendationText: {
    fontSize: 14,
    lineHeight: 20
  },
  backButton: {
    backgroundColor: '#2196F3',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 20,
    marginBottom: 20
  },
  backButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16
  }
});