// screens/DiseaseResultScreen.tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Platform
} from 'react-native';

const API_URL =
  Platform.OS === 'android'
    ? 'http://10.67.1.211:3001'
    : 'http://localhost:3001';

type DiseaseResultScreenProps = {
  route: any;
  navigation: any;
};

export default function DiseaseResultScreen({ route, navigation }: DiseaseResultScreenProps) {
  const { results, cropType, recommendations: passedRecommendations, recommendationDetails: passedDetails, plotId, farmerId } = route.params;

  const { 
    disease, 
    recommendations, 
    penalties, 
    diseaseAdvice, 
    
    ndvi_stats, 
    ndviTrend 
  } = results || {};

  // State for loading and error handling
  const [loading, _setLoading] = useState(false);
  const [error, _setError] = useState<string | null>(null);
  const [fetchedRecommendations, setFetchedRecommendations] = useState<any>(null);

  // Fetch recommendations from backend if not passed
  const fetchRecommendations = useCallback(async () => {
    if (!plotId || !farmerId || !results) return;
    
    try {
      _setLoading(true);
      
      const aggregatedFeatures = {
        disease_detection: {
          risk_level: results.disease?.risk_level || "unknown",
          disease_prob: results.disease?.probability || 0
        },
        pest_risk: {
          risk_level: results.pest?.risk_level || "unknown",
          confidence: results.pest?.confidence || 0
        },
        water_stress: {
          stress: results.waterStress?.current_status?.moisture_status || "unknown",
          score: results.waterStress?.current_status?.water_stress || 0
        },
        stage_classifier: {
          stage: results.stage?.prediction || "unknown"
        }
      };

      const response = await fetch(`${API_URL}/api/generate-recommendations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plotId,
          farmerId,
          plotFeatures: aggregatedFeatures,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setFetchedRecommendations(data.recommendations);
      }
    } catch (err) {
      console.error('Error fetching recommendations:', err);
    } finally {
      _setLoading(false);
    }
  }, [plotId, farmerId, results]);

  useEffect(() => {
    if (!passedRecommendations && plotId && farmerId) {
      fetchRecommendations();
    }
  }, [passedRecommendations, plotId, farmerId, fetchRecommendations]);
  
  // Use passed recommendations first, then fetched, then fallback to old format
  const finalRecommendations = passedRecommendations || fetchedRecommendations || recommendations;

  // Get disease advice from the results
  const getDiseaseAdvice = () => {
    if (diseaseAdvice) {
      return diseaseAdvice;
    }
    
    // Fallback to basic info if no detailed advice
    return {
      title: disease?.prediction || 'Unknown Disease',
      symptoms: [`Symptom: ${(disease?.prediction || 'Unknown Disease')} detected`],
      recommendations: [
        "Monitor crop closely",
        "Consult agricultural expert",
        "Take preventive measures"
      ],
      severity: disease?.risk_level || 'Unknown',
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
      'Healthy': '#4CAF50',
      'Unknown': '#666'
    };
    return severityColors[severity] || '#666';
  };

  // Calculate economic impact
  const calculateEconomicImpact = () => {
    const riskLevel = disease?.risk_level?.toUpperCase() || 'LOW';
    
    if (riskLevel === 'HIGH') {
      return {
        yield_loss: '15-25%',
        treatment_cost: '$50-80/ha',
        expected_benefit: '$200-400/ha',
        roi: '250-500%'
      };
    } else if (riskLevel === 'MEDIUM') {
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
    const riskLevel = disease?.risk_level?.toUpperCase() || 'LOW';
    
    if (riskLevel === 'HIGH') {
      return [
        'Immediate (1-3 days): Apply recommended treatment',
        'Weekly: Monitor disease progression',
        'Bi-weekly: Assess treatment effectiveness',
        'Monthly: Update farm records'
      ];
    } else if (riskLevel === 'MEDIUM') {
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
        <Text style={styles.subtitle}>{cropType?.toUpperCase() || 'UNKNOWN'}</Text>
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
      {disease && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Disease Detection</Text>
          <View style={styles.diseaseContainer}>
            <Text style={styles.diseaseText}>
              {disease.prediction || 'Unknown Disease'}
            </Text>
            <Text style={[styles.confidenceText, { color: getConfidenceColor(disease.confidence || 0) }]}>
              {((disease.confidence || 0) * 100).toFixed(1)}% confidence
            </Text>
          </View>
          <View style={styles.riskContainer}>
            <Text style={[
              styles.riskText,
              { color: getSeverityColor(disease.risk_level || 'Unknown') }
            ]}>
              {disease.risk_level || 'Unknown'} Risk
            </Text>
            <Text style={styles.probabilityText}>
              {((disease.probability || 0) * 100).toFixed(1)}% probability
            </Text>
          </View>
        </View>
      )}

      {/* Disease Level Information */}
      {penalties && penalties.disease_level && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Disease Level</Text>
          <View style={styles.diseaseLevelContainer}>
            <Text style={styles.diseaseLevel}>Level: {penalties.disease_level.label || 'N/A'}</Text>
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
            <Text style={styles.trendHeaderText}>
              Current NDVI: {ndvi_stats?.mean?.toFixed(3) || (ndviTrend[ndviTrend.length - 1]?.ndvi?.toFixed(3) || 'N/A')}
            </Text>
            <Text style={styles.trendText}>
              • Trend: {ndvi_stats?.trend > 0 ? '📈 Improving' : '📉 Declining'} ({ndvi_stats?.trend?.toFixed(3) || 'N/A'})
            </Text>
            <Text style={styles.trendText}>
              • Min: {ndvi_stats?.min?.toFixed(3) || 'N/A'} | Max: {ndvi_stats?.max?.toFixed(3) || 'N/A'}
            </Text>
            
            {/* NDVI Timeline */}
            <View style={styles.ndviTimeline}>
              <Text style={styles.ndviTimelineTitle}>7-Day NDVI Values:</Text>
              {ndviTrend.map((point: any, idx: number) => (
                <View key={`ndvi-${idx}`} style={styles.ndviDataPoint}>
                  <Text style={styles.ndviDate}>
                    {new Date(point.date).toLocaleDateString('en-US', {month: 'short', day: 'numeric'})}
                  </Text>
                  <View style={styles.ndviBar}>
                    <View 
                      style={[
                        styles.ndviBarFill, 
                        { 
                          width: `${Math.min(point.ndvi * 100, 100)}%`,
                          backgroundColor: point.ndvi > 0.6 ? '#4CAF50' : point.ndvi > 0.4 ? '#FFC107' : '#F44336'
                        }
                      ]} 
                    />
                  </View>
                  <Text style={styles.ndviValue}>{point.ndvi?.toFixed(3)}</Text>
                </View>
              ))}
            </View>
            
            {/* Health Status */}
            <View style={[styles.healthStatus, { 
              backgroundColor: ndvi_stats?.mean > 0.6 ? '#E8F5E9' : ndvi_stats?.mean > 0.4 ? '#FFF8E1' : '#FFEBEE'
            }]}>
              <Text style={[styles.healthStatusText, {
                color: ndvi_stats?.mean > 0.6 ? '#2E7D32' : ndvi_stats?.mean > 0.4 ? '#F57F17' : '#C62828'
              }]}>
                {ndvi_stats?.mean > 0.6 ? '✓ Healthy Vegetation' : ndvi_stats?.mean > 0.4 ? '⚠ Moderate Vegetation' : '✗ Poor Vegetation'}
              </Text>
            </View>
          </View>
        </View>
      )}

      {/* Confidence Meter */}
      {disease && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Confidence Level</Text>
          <View style={styles.confidenceContainer}>
            <ConfidenceMeter 
              label="Disease" 
              value={disease.probability || 0} 
              color={disease.risk_level === 'Low' ? '#4CAF50' : 
                     disease.risk_level === 'Medium' ? '#FF9800' : '#F44336'} 
            />
          </View>
        </View>
      )}

      {/* Disease Recommendations */}
      {(finalRecommendations?.disease_detection || finalRecommendations?.disease) && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Next Steps to be taken  </Text>
          <View style={styles.recommendationsContainer}>
            {(() => {
              let recs = [];
              if (finalRecommendations?.disease_detection && typeof finalRecommendations.disease_detection === 'string') {
                recs = finalRecommendations.disease_detection
                  .split('\n\n')
                  .filter((rec: string) => rec.trim().length > 0)
                  .map((rec: string) => rec.trim());
              } else if (finalRecommendations?.disease && Array.isArray(finalRecommendations.disease)) {
                recs = finalRecommendations.disease;
              }
              return recs.map((rec: string, index: number) => (
                <View key={`disease-${index}`} style={styles.recommendationItem}>
                  <Text style={styles.recommendationText}>• {rec}</Text>
                </View>
              ));
            })()}
          </View>
        </View>
      )}

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

// width not used in this screen

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
  trendHeaderText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 10
  },
  trendText: {
    fontSize: 14,
    color: '#333',
    marginBottom: 5
  },
  ndviTimeline: {
    marginTop: 15,
    paddingTop: 15,
    borderTopWidth: 1,
    borderTopColor: '#E0E0E0'
  },
  ndviTimelineTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 10
  },
  ndviDataPoint: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
    gap: 10
  },
  ndviDate: {
    fontSize: 12,
    color: '#666',
    width: 50,
    fontWeight: '500'
  },
  ndviBar: {
    flex: 1,
    height: 20,
    backgroundColor: '#F0F0F0',
    borderRadius: 4,
    overflow: 'hidden'
  },
  ndviBarFill: {
    height: '100%',
    borderRadius: 4
  },
  ndviValue: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#333',
    width: 45,
    textAlign: 'right'
  },
  healthStatus: {
    marginTop: 15,
    padding: 12,
    borderRadius: 8,
    alignItems: 'center'
  },
  healthStatusText: {
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center'
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