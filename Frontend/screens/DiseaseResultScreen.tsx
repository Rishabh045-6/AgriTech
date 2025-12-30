// screens/DiseaseResultScreen.tsx
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Dimensions,
  Alert,
  Platform,
  ActivityIndicator
} from 'react-native';

type DiseaseResultScreenProps = {
  route: any;
  navigation: any;
};

export default function DiseaseResultScreen({ route, navigation }: DiseaseResultScreenProps) {
  const { results, cropType } = route.params;

  const { disease, recommendations, penalties, diseaseAdvice, window_df, ndvi_stats, ndviTrend } = results;

  // State for loading and error handling
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get disease advice from the results
  const getDiseaseAdvice = () => {
    if (diseaseAdvice) {
      return diseaseAdvice;
    }
    
    // Fallback to basic info if no detailed advice
    return {
      title: disease.prediction,
      symptoms: [`Symptom: ${disease.prediction} detected`],
      recommendations: [
        "Monitor crop closely",
        "Consult agricultural expert",
        "Take preventive measures"
      ],
      severity: disease.risk_level,
      chemical_control: ["Follow standard treatment protocol"],
      organic_control: ["Maintain field hygiene"],
      preventive_measures: ["Regular monitoring", "Crop rotation"]
    };
  };

  const advice = getDiseaseAdvice();

  // Get confidence level color
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return '#4CAF50'; // High confidence - Green
    if (confidence >= 0.6) return '#FF9800'; // Medium confidence - Orange
    return '#F44336'; // Low confidence - Red
  };

  // Get severity color
  const getSeverityColor = (severity: string) => {
    const severityColors: Record<string, string> = {
      'High': '#F44336',
      'Medium': '#FF9800',
      'Low': '#4CAF50',
      'None': '#2196F3',
      'Healthy': '#4CAF50'
    };
    return severityColors[severity] || '#666';
  };

  // Calculate economic impact
  const calculateEconomicImpact = () => {
    if (disease.risk_level === 'HIGH') {
      return {
        yield_loss: '15-25%',
        treatment_cost: '$50-80/ha',
        expected_benefit: '$200-400/ha',
        roi: '250-500%'
      };
    } else if (disease.risk_level === 'MEDIUM') {
      return {
        yield_loss: '5-15%',
        treatment_cost: '$30-50/ha',
        expected_benefit: '$100-200/ha',
        roi: '150-300%'
      };
    } else {
      return {
        yield_loss: '0-5%',
        treatment_cost: '$10-20/ha',
        expected_benefit: '$50-100/ha',
        roi: '100-200%'
      };
    }
  };

  const economicImpact = calculateEconomicImpact();

  // Get weather considerations (simulated from NDVI data)
  const getWeatherConsiderations = () => {
    if (ndvi_stats) {
      const avg_ndvi = ndvi_stats.mean;
      const trend = ndvi_stats.trend;
      
      return {
        rainfall: avg_ndvi > 0.6 ? '25mm (Good for treatment)' : '10-15mm (Monitor moisture)',
        temperature: avg_ndvi > 0.5 ? '22-28°C (Optimal conditions)' : '18-25°C (Suboptimal)',
        expected_rainfall: trend > 0 ? '10-15mm expected (Plan timing)' : '5-10mm expected (Act quickly)'
      };
    }
    
    return {
      rainfall: '25mm (Good for treatment)',
      temperature: '22-28°C (Optimal conditions)',
      expected_rainfall: '10-15mm expected (Plan timing)'
    };
  };

  const weatherInfo = getWeatherConsiderations();

  // Get action timeline
  const getActionTimeline = () => {
    if (disease.risk_level === 'HIGH') {
      return [
        'Immediate (1-3 days): Apply recommended treatment',
        'Weekly: Monitor disease progression',
        'Bi-weekly: Assess treatment effectiveness',
        'Monthly: Update farm records'
      ];
    } else if (disease.risk_level === 'MEDIUM') {
      return [
        'Within 1 week: Apply recommended treatment',
        'Bi-weekly: Monitor disease progression',
        'Monthly: Assess treatment effectiveness',
        'Quarterly: Update farm records'
      ];
    } else {
      return [
        'Monitor regularly: Every 2 weeks',
        'Monthly: Check for any changes',
        'Seasonal: Update records',
        'Annual: Plan prevention strategies'
      ];
    }
  };

  const timelineItems = getActionTimeline();

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>🦠 Disease Analysis</Text>
        <Text style={styles.subtitle}>{cropType.toUpperCase()}</Text>
      </View>

      {/* Loading Indicator */}
      {loading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#2E8B57" />
          <Text style={styles.loadingText}>Analyzing disease data...</Text>
        </View>
      )}

      {/* Error Message */}
      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {/* Disease Detection Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Disease Detection</Text>
        <View style={styles.diseaseContainer}>
          <Text style={styles.diseaseText}>
            {disease.prediction}
          </Text>
          <Text style={[styles.confidenceText, { color: getConfidenceColor(disease.confidence) }]}>
            {(disease.confidence * 100).toFixed(1)}% confidence
          </Text>
        </View>
        <View style={styles.riskContainer}>
          <Text style={[
            styles.riskText,
            { color: getSeverityColor(disease.risk_level) }
          ]}>
            {disease.risk_level} Risk
          </Text>
          <Text style={styles.probabilityText}>
            {(disease.probability * 100).toFixed(1)}% probability
          </Text>
        </View>
      </View>

      {/* Disease Level Information */}
      {penalties && penalties.disease_level && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Disease Level</Text>
          <View style={styles.diseaseLevelContainer}>
            <Text style={styles.diseaseLevel}>Level: {penalties.disease_level.label}</Text>
            <Text style={styles.diseaseMultiplier}>Multiplier: {(penalties.disease_level.multiplier * 100).toFixed(0)}%</Text>
          </View>
        </View>
      )}

      {/* Disease Details Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Disease Information</Text>
        <View style={styles.diseaseDetails}>
          <Text style={styles.diseaseTitle}>Disease: {advice.title}</Text>
          <Text style={[styles.severity, { color: getSeverityColor(advice.severity) }]}>
            Severity: {advice.severity}
          </Text>
        </View>
      </View>

      {/* Symptoms Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🔍 Symptoms</Text>
        <View style={styles.symptomsContainer}>
          {advice.symptoms.map((symptom: string, index: number) => (
            <View key={`symptom-${index}`} style={styles.symptomItem}>
              <Text style={styles.symptomText}>• {symptom}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Recommendations Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🌱 Management Recommendations</Text>
        <View style={styles.recommendationsContainer}>
          {advice.recommendations.map((rec: string, index: number) => (
            <View key={`rec-${index}`} style={styles.recommendationItem}>
              <Text style={styles.recommendationText}>• {rec}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Chemical Control Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🧪 Chemical Control</Text>
        <View style={styles.controlContainer}>
          {advice.chemical_control.map((control: string, index: number) => (
            <View key={`chem-${index}`} style={styles.controlItem}>
              <Text style={styles.controlText}>• {control}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Organic Control Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🌿 Organic Control</Text>
        <View style={styles.controlContainer}>
          {advice.organic_control.map((control: string, index: number) => (
            <View key={`org-${index}`} style={styles.controlItem}>
              <Text style={styles.controlText}>• {control}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Preventive Measures Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🛡️ Preventive Measures</Text>
        <View style={styles.preventiveContainer}>
          {advice.preventive_measures.map((measure: string, index: number) => (
            <View key={`prevention-${index}`} style={styles.measureItem}>
              <Text style={styles.measureText}>• {measure}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Urgent Actions Card */}
      {advice.severity === 'High' && (
        <View style={[styles.card, styles.urgentCard]}>
          <Text style={styles.sectionTitle}>🚨 Urgent Action Required</Text>
          <View style={styles.urgentContainer}>
            <Text style={styles.urgentText}>
              This disease poses a high risk to your crop. Immediate action is recommended:
            </Text>
            <Text style={styles.urgentText}>
              1. Isolate affected areas
            </Text>
            <Text style={styles.urgentText}>
              2. Apply recommended treatment within 24-48 hours
            </Text>
            <Text style={styles.urgentText}>
              3. Monitor surrounding plants
            </Text>
          </View>
        </View>
      )}

      {/* Economic Impact Card */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>💰 Economic Impact</Text>
        <View style={styles.economicContainer}>
          <Text style={styles.economicText}>
            • Potential yield loss without treatment: {economicImpact.yield_loss}
          </Text>
          <Text style={styles.economicText}>
            • Estimated treatment cost: {economicImpact.treatment_cost}
          </Text>
          <Text style={styles.economicText}>
            • Expected benefit: {economicImpact.expected_benefit}
          </Text>
          <Text style={styles.roiText}>
            ROI: {economicImpact.roi} if treated promptly
          </Text>
        </View>
      </View>

      {/* Weather Considerations */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🌤️ Weather Considerations</Text>
        <View style={styles.weatherContainer}>
          <Text style={styles.weatherText}>• {weatherInfo.rainfall}</Text>
          <Text style={styles.weatherText}>• {weatherInfo.temperature}</Text>
          <Text style={styles.weatherText}>• {weatherInfo.expected_rainfall}</Text>
        </View>
      </View>

      {/* Action Timeline */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>⏰ Action Timeline</Text>
        <View style={styles.timelineContainer}>
          {timelineItems.map((item, index) => (
            <Text key={`timeline-${index}`} style={styles.timelineText}>• {item}</Text>
          ))}
        </View>
      </View>

      {/* NDVI Trend Analysis */}
      {ndviTrend && ndviTrend.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>📊 NDVI Trend Analysis</Text>
          <View style={styles.trendContainer}>
            <Text style={styles.trendText}>
              • Current NDVI: {ndvi_stats.mean.toFixed(3)}
            </Text>
            <Text style={styles.trendText}>
              • Trend: {ndvi_stats.trend > 0 ? 'Improving' : 'Declining'} ({ndvi_stats.trend.toFixed(3)})
            </Text>
            <Text style={styles.trendText}>
              • Min: {ndvi_stats.min.toFixed(3)}, Max: {ndvi_stats.max.toFixed(3)}
            </Text>
          </View>
        </View>
      )}

      {/* Confidence Meter */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Confidence Level</Text>
        <View style={styles.confidenceContainer}>
          <ConfidenceMeter 
            label="Disease" 
            value={disease.probability} 
            color={disease.risk_level === 'LOW' ? '#4CAF50' : 
                   disease.risk_level === 'MEDIUM' ? '#FF9800' : '#F44336'} 
          />
        </View>
      </View>

      {/* Disease Recommendations */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Disease Recommendations</Text>
        <View style={styles.recommendationsContainer}>
          {recommendations.disease && recommendations.disease.map((rec: string, index: number) => (
            <View key={`disease-${index}`} style={styles.recommendationItem}>
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
        <Text style={styles.backButtonText}>← Back to Results</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

// Reusable Components
const ConfidenceMeter = ({ label, value, color }: { label: string, value: number, color: string }) => (
  <View style={styles.confidenceItem}>
    <Text style={styles.confidenceLabel}>{label}</Text>
    <View style={styles.confidenceMeter}>
      <View style={[styles.confidenceFill, { width: `${value * 100}%`, backgroundColor: color }]} />
      <Text style={styles.confidenceOverlayText}>{(value * 100).toFixed(1)}%</Text>
    </View>
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
  errorContainer: {
    backgroundColor: '#FCE4EC',
    padding: 15,
    borderRadius: 8,
    marginBottom: 16
  },
  errorText: {
    fontSize: 16,
    color: '#F44336',
    textAlign: 'center'
  },
  header: {
    alignItems: 'center',
    marginBottom: 20
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 5
  },
  subtitle: {
    fontSize: 16,
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
  urgentCard: {
    backgroundColor: '#FFEBEE',
    borderLeftColor: '#F44336',
    borderLeftWidth: 5
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 15,
    color: '#333',
    textAlign: 'center'
  },
  diseaseContainer: {
    alignItems: 'center',
    padding: 20,
    backgroundColor: '#FFF3CD',
    borderRadius: 10,
    marginBottom: 10
  },
  diseaseText: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 5
  },
  confidenceText: {
    fontSize: 16,
    fontWeight: '600'
  },
  riskContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: 10
  },
  riskText: {
    fontSize: 16,
    fontWeight: 'bold'
  },
  probabilityText: {
    fontSize: 14,
    color: '#666'
  },
  diseaseLevelContainer: {
    paddingVertical: 10
  },
  diseaseLevel: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 5
  },
  diseaseMultiplier: {
    fontSize: 14,
    color: '#666'
  },
  diseaseDetails: {
    paddingVertical: 10
  },
  diseaseTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 5
  },
  severity: {
    fontSize: 14,
    fontWeight: '600'
  },
  symptomsContainer: {
    paddingVertical: 10
  },
  symptomItem: {
    backgroundColor: '#F8F9FA',
    padding: 10,
    borderRadius: 8,
    marginBottom: 8
  },
  symptomText: {
    fontSize: 14,
    color: '#333',
    lineHeight: 18
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
  controlContainer: {
    paddingVertical: 10
  },
  controlItem: {
    backgroundColor: '#E3F2FD',
    padding: 10,
    borderRadius: 8,
    marginBottom: 8
  },
  controlText: {
    fontSize: 14,
    color: '#1976D2'
  },
  preventiveContainer: {
    paddingVertical: 10
  },
  measureItem: {
    backgroundColor: '#F3E5F5',
    padding: 10,
    borderRadius: 8,
    marginBottom: 8
  },
  measureText: {
    fontSize: 14,
    color: '#7B1FA2'
  },
  urgentContainer: {
    paddingVertical: 10
  },
  urgentText: {
    fontSize: 14,
    color: '#F44336',
    fontWeight: 'bold',
    marginBottom: 5
  },
  economicContainer: {
    paddingVertical: 10
  },
  economicText: {
    fontSize: 14,
    color: '#333',
    marginBottom: 5
  },
  roiText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#4CAF50',
    marginTop: 10
  },
  weatherContainer: {
    paddingVertical: 10
  },
  weatherText: {
    fontSize: 14,
    color: '#333',
    marginBottom: 5
  },
  timelineContainer: {
    paddingVertical: 10
  },
  timelineText: {
    fontSize: 14,
    color: '#333',
    marginBottom: 5
  },
  trendContainer: {
    paddingVertical: 10
  },
  trendText: {
    fontSize: 14,
    color: '#333',
    marginBottom: 5
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
  confidenceOverlayText: {
    position: 'absolute',
    right: 10,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
    fontSize: 12,
    fontWeight: 'bold',
    color: 'white'
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