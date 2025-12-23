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
    setLoading(true);
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
      setLoading(false);
    }
  };

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

  const { stage, disease, pest, growthPerformance, ndviTrend, recommendations, healthMetrics, ndvi_stats } = results;

  // Calculate plot area (simple approximation)
  const calculatePlotArea = () => {
    if (plotCoordinates && plotCoordinates.length >= 3) {
      // Simple area calculation using coordinates
      let area = 0;
      for (let i = 0; i < plotCoordinates.length - 1; i++) {
        const p1 = plotCoordinates[i];
        const p2 = plotCoordinates[i + 1];
        area += (p1.longitude * p2.latitude - p2.longitude * p1.latitude);
      }
      area = Math.abs(area) / 2;
      {/* Convert to acres (approximate)*/}
      return (area * 247.105).toFixed(2);
    }
    return 'N/A';
  };

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>🌾 Crop Analysis Results</Text>
        <Text style={styles.subtitle}>{cropType.toUpperCase()}</Text>
      </View>

      {/* Plot Information */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Plot Information</Text>
        <View style={styles.plotInfoContainer}>
          <Text style={styles.plotInfoText}>Farmer ID: {farmerId}</Text>
          <Text style={styles.plotInfoText}>Plot Area: {calculatePlotArea()} acres</Text>
          <Text style={styles.plotInfoText}>Coordinates: {plotCoordinates.length} points</Text>
        </View>
      </View>

      {/* Growth Performance Card */}
      {growthPerformance && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>🌱 Growth Performance</Text>
          <View style={styles.growthContainer}>
            <Text style={styles.growthScore}>Overall Score: {growthPerformance.report.overall_score.toFixed(1)}</Text>
            <Text style={styles.growthStatus}>Status: {growthPerformance.report.status}</Text>
            <Text style={styles.growthRecommendation}>Recommendation: {growthPerformance.report.recommendation}</Text>
          </View>
          
          <View style={styles.growthMetricsContainer}>
            <GrowthMetricCard 
              name="Growth Rate" 
              score={growthPerformance.scores.growth_rate} 
              status={growthPerformance.healthMetrics.growth_rate.status} 
            />
            <GrowthMetricCard 
              name="Biomass" 
              score={growthPerformance.scores.biomass} 
              status={growthPerformance.healthMetrics.biomass.status} 
            />
            <GrowthMetricCard 
              name="Stability" 
              score={growthPerformance.scores.stability} 
              status={growthPerformance.healthMetrics.stability.status} 
            />
          </View>
        </View>
      )}

      {/* Stage Prediction Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Growth Stage Prediction</Text>
        <View style={styles.predictionContainer}>
          <Text style={styles.stageText}>{stage.prediction}</Text>
          <Text style={styles.confidenceeText}>{(stage.confidence * 100).toFixed(1)}% confidence</Text>
        </View>
      </View>

      {/* Disease Detection Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Disease Detection</Text>
        <View style={styles.diseaseContainer}>
          <Text style={[
            styles.diseaseText,
            { color: disease.risk_level === 'LOW' ? '#4CAF50' : 
                     disease.risk_level === 'MEDIUM' ? '#FF9800' : '#F44336' }
          ]}>
            {disease.risk_level} Risk
          </Text>
          <Text style={styles.diseaseProbText}>{(disease.probability * 100).toFixed(1)}% probability</Text>
        </View>
      </View>

      {/* Pest Risk Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Pest Risk Assessment</Text>
        <View style={styles.pestContainer}>
          <Text style={[
            styles.pestText,
            { color: pest.risk_level === 'Low' ? '#4CAF50' : 
                     pest.risk_level === 'Medium' ? '#FF9800' : '#F44336' }
          ]}>
            {pest.risk_level} Risk
          </Text>
          <Text style={styles.pestConfidenceText}>{(pest.confidence * 100).toFixed(1)}% confidence</Text>
        </View>
      </View>

      {/* Confidence Meters */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Confidence Levels</Text>
        <View style={styles.confidenceContainer}>
          <ConfidenceMeter 
            label="Stage" 
            value={stage.confidence} 
            color="#4CAF50" 
          />
          <ConfidenceMeter 
            label="Disease" 
            value={disease.probability} 
            color={disease.risk_level === 'LOW' ? '#4CAF50' : 
                   disease.risk_level === 'MEDIUM' ? '#FF9800' : '#F44336'} 
          />
          <ConfidenceMeter 
            label="Pest" 
            value={pest.confidence} 
            color={pest.risk_level === 'Low' ? '#4CAF50' : 
                   pest.risk_level === 'Medium' ? '#FF9800' : '#F44336'} 
          />
        </View>
      </View>

      {/* NDVI Trend Chart */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>NDVI Trend Over Time</Text>
        <View style={styles.chartContainer}>
          {ndviTrend && ndviTrend.length > 0 && (
            <View style={styles.trendChart}>
              {ndviTrend.map((point: any, index: number) => (
                <View key={index} style={styles.trendPoint}>
                  <Text style={styles.trendDate}>{new Date(point.date).toLocaleDateString()}</Text>
                  <View style={[styles.trendBar, { height: point.ndvi * 100 }]} />
                  <Text style={styles.trendValue}>{point.ndvi.toFixed(2)}</Text>
                </View>
              ))}
            </View>
          )}
        </View>
      </View>

      {/* NDVI Statistics */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>NDVI Statistics</Text>
        <View style={styles.statsContainer}>
          <StatItem label="Mean" value={ndvi_stats.mean.toFixed(3)} />
          <StatItem label="Min" value={ndvi_stats.min.toFixed(3)} />
          <StatItem label="Max" value={ndvi_stats.max.toFixed(3)} />
          <StatItem label="Trend" value={ndvi_stats.trend.toFixed(3)} />
        </View>
      </View>

      {/* Health Metrics */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Soil Health Metrics</Text>
        <View style={styles.healthMetricsContainer}>
          {healthMetrics && Object.entries(healthMetrics).map(([key, value]: [string, any]) => (
            <HealthMetricCard 
              key={key} 
              name={key.charAt(0).toUpperCase() + key.slice(1)} 
              level={value.level} 
              status={value.status} 
            />
          ))}
        </View>
      </View>

      {/* Stage Recommendations */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🌱 Stage Recommendations</Text>
        <View style={styles.recommendationsContainer}>
          {recommendations.stage && recommendations.stage.map((rec: string, index: number) => (
            <View key={`stage-${index}`} style={styles.recommendationItem}>
              <Text style={styles.recommendationText}>• {rec}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Disease Recommendations */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🦠 Disease Recommendations</Text>
        <View style={styles.recommendationsContainer}>
          {recommendations.disease && recommendations.disease.map((rec: string, index: number) => (
            <View key={`disease-${index}`} style={styles.recommendationItem}>
              <Text style={styles.recommendationText}>• {rec}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Pest Recommendations */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🐛 Pest Recommendations</Text>
        <View style={styles.recommendationsContainer}>
          {recommendations.pest && recommendations.pest.map((rec: string, index: number) => (
            <View key={`pest-${index}`} style={styles.recommendationItem}>
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

// Confidence Meter Component
const ConfidenceMeter = ({ label, value, color }: { label: string, value: number, color: string }) => (
  <View style={styles.confidenceItem}>
    <Text style={styles.confidenceLabel}>{label}</Text>
    <View style={styles.confidenceMeter}>
      <View style={[styles.confidenceFill, { width: `${value * 100}%`, backgroundColor: color }]} />
      <Text style={styles.confidenceText}>{(value * 100).toFixed(1)}%</Text>
    </View>
  </View>
);

// Health Metric Card Component
const HealthMetricCard = ({ name, level, status }: { name: string, level: string, status: string }) => {
  const getStatusColor = () => {
    if (status.toLowerCase().includes('good') || status.toLowerCase().includes('adequate')) return '#4CAF50';
    if (status.toLowerCase().includes('low') || status.toLowerCase().includes('needs')) return '#FF9800';
    if (status.toLowerCase().includes('high') || status.toLowerCase().includes('excess')) return '#F44336';
    return '#666';
  };

  return (
    <View style={styles.healthMetricCard}>
      <Text style={styles.healthMetricName}>{name}</Text>
      <Text style={styles.healthMetricValue}>{level}</Text>
      <Text style={[styles.healthMetricStatus, { color: getStatusColor() }]}>
        {status}
      </Text>
    </View>
  );
};

// Growth Metric Card Component
const GrowthMetricCard = ({ name, score, status }: { name: string, score: number, status: string }) => {
  const getStatusColor = () => {
    if (score >= 80) return '#4CAF50'; // Green
    if (score >= 60) return '#8BC34A'; // Light Green
    if (score >= 40) return '#FFC107'; // Amber
    return '#F44336'; // Red
  };

  return (
    <View style={styles.growthMetricCard}>
      <Text style={styles.growthMetricName}>{name}</Text>
      <Text style={styles.growthMetricValue}>{score.toFixed(1)}</Text>
      <Text style={[styles.growthMetricStatus, { color: getStatusColor() }]}>
        {status}
      </Text>
    </View>
  );
};

// Stat Item Component
const StatItem = ({ label, value }: { label: string, value: string }) => (
  <View style={styles.statItem}>
    <Text style={styles.statLabel}>{label}</Text>
    <Text style={styles.statValue}>{value}</Text>
  </View>
);

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
  plotInfoContainer: {
    paddingVertical: 10
  },
  plotInfoText: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5
  },
  growthContainer: {
    paddingVertical: 10,
    marginBottom: 10
  },
  growthScore: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 5
  },
  growthStatus: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5
  },
  growthRecommendation: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic'
  },
  growthMetricsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between'
  },
  growthMetricCard: {
    width: (width - 52) / 3, // Three cards per row
    backgroundColor: '#F8F9FA',
    padding: 12,
    borderRadius: 8,
    marginBottom: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E0E0E0'
  },
  growthMetricName: {
    fontSize: 12,
    fontWeight: '600',
    color: '#333',
    marginBottom: 3
  },
  growthMetricValue: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 2
  },
  growthMetricStatus: {
    fontSize: 10,
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
  confidenceeText: {
    fontSize: 16,
    color: '#666'
  },
  diseaseContainer: {
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#FFF3CD',
    borderRadius: 10
  },
  diseaseText: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 5
  },
  diseaseProbText: {
    fontSize: 16,
    color: '#666'
  },
  pestContainer: {
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#FCE4EC',
    borderRadius: 10
  },
  pestText: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 5
  },
  pestConfidenceText: {
    fontSize: 16,
    color: '#666'
  },
  confidenceContainer: {
    paddingVertical: 10
  },
  confidenceItem: {
    marginBottom: 15
  },
  confidenceLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 5
  },
  confidenceMeter: {
    height: 20,
    backgroundColor: '#E0E0E0',
    borderRadius: 10,
    overflow: 'hidden',
    position: 'relative'
  },
  confidenceFill: {
    height: '100%',
    borderRadius: 10
  },
  confidenceText: {
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
  trendChart: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'flex-end',
    height: 120,
    backgroundColor: '#F0F0F0',
    borderRadius: 8,
    padding: 8
  },
  trendPoint: {
    alignItems: 'center',
    width: 25
  },
  trendDate: {
    fontSize: 8,
    textAlign: 'center',
    marginBottom: 4
  },
  trendBar: {
    backgroundColor: '#2196F3',
    width: 15,
    borderRadius: 4,
    marginBottom: 4
  },
  trendValue: {
    fontSize: 10,
    textAlign: 'center'
  },
  statsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between'
  },
  statItem: {
    width: (width - 52) / 2,
    padding: 10,
    marginBottom: 10,
    backgroundColor: '#F8F9FA',
    borderRadius: 8,
    alignItems: 'center'
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 5
  },
  statValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2E8B57'
  },
  healthMetricsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between'
  },
  healthMetricCard: {
    width: (width - 52) / 2,
    backgroundColor: '#F8F9FA',
    padding: 15,
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