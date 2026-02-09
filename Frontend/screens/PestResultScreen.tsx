// screens/PestResultScreen.tsx
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Platform
} from 'react-native';

const API_URL =
  Platform.OS === 'android'
    ? 'http://10.67.1.211:3001'
    : 'http://localhost:3001';

type PestResultScreenProps = {
  route: any;
  navigation: any;
};

export default function PestResultScreen({ route, navigation }: PestResultScreenProps) {
  const { results, cropType, recommendations: passedRecommendations, recommendationDetails: passedDetails, plotId, farmerId } = route.params;
  const { pest, recommendations, penalties } = results || {};
  
  const [fetchedRecommendations, setFetchedRecommendations] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  // Fetch recommendations from backend if not passed
  const fetchRecommendations = useCallback(async () => {
    if (!plotId || !farmerId || !results) return;
    
    try {
      setLoading(true);
      
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
      setLoading(false);
    }
  }, [plotId, farmerId, results]);

  useEffect(() => {
    if (!passedRecommendations && plotId && farmerId) {
      fetchRecommendations();
    }
  }, [passedRecommendations, plotId, farmerId, fetchRecommendations]);
  
  // Use passed recommendations first, then fetched, then fallback to old format
  const finalRecommendations = passedRecommendations || fetchedRecommendations || recommendations;

  // Get pest assessment text based on risk level and probabilities
  const getPestAssessment = () => {
    if (!pest) return 'No pest data available';
    
    const riskLevel = pest.risk_level || 'Low';
    const confidence = pest.confidence || 0;
    // probabilities are available on `pest.probabilities` if needed
    
    if (riskLevel === 'High') {
      return `HIGH PEST PRESSURE DETECTED: Significant pest infestation risk (${(confidence * 100).toFixed(1)}% confidence). Immediate action recommended. Multiple pest species likely present.`;
    } else if (riskLevel === 'Medium') {
      return `MODERATE PEST PRESSURE: Notable pest activity detected (${(confidence * 100).toFixed(1)}% confidence). Monitor closely and consider preventive treatments.`;
    } else {
      return `LOW PEST PRESSURE: Minimal pest activity detected (${(confidence * 100).toFixed(1)}% confidence). Continue regular monitoring for early signs of infestation.`;
    }
  };

  // Get pest recommendations based on risk level
  const getPestRecommendations = () => {
    // Check for backend recommendations (converted to array)
    if (finalRecommendations?.pest_risk && typeof finalRecommendations.pest_risk === 'string') {
      return finalRecommendations.pest_risk
        .split('\n\n')
        .filter((rec: string) => rec.trim().length > 0)
        .map((rec: string) => rec.trim());
    }
    
    if (finalRecommendations?.pest && finalRecommendations.pest.length > 0) {
      return finalRecommendations.pest;
    }
    
    // Fallback recommendations based on risk level
    const riskLevel = pest?.risk_level || 'Low';
    
    if (riskLevel === 'High') {
      return [
        'Immediate application of recommended pesticide',
        'Scout fields daily for pest presence',
        'Isolate affected areas to prevent spread',
        'Monitor neighboring fields for spillover',
        'Implement integrated pest management (IPM) strategies',
        'Consider biological control agents',
        'Document all pest activity and treatments'
      ];
    } else if (riskLevel === 'Medium') {
      return [
        'Apply pesticide within 3-5 days',
        'Scout fields every 2-3 days',
        'Implement cultural control practices',
        'Use pheromone traps for monitoring',
        'Maintain field sanitation',
        'Encourage natural predators',
        'Keep detailed records of pest activity'
      ];
    } else {
      return [
        'Continue regular field monitoring',
        'Maintain good field hygiene',
        'Scout for early signs of pest damage',
        'Use preventive measures if needed',
        'Monitor weather conditions',
        'Keep equipment and tools clean',
        'Maintain records for future reference'
      ];
    }
  };

  const pestAssessment = getPestAssessment();
  const pestRecommendations = getPestRecommendations();

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel?.toLowerCase()) {
      case 'high':
        return { bg: '#FFEBEE', text: '#F44336', border: '#F44336' };
      case 'medium':
        return { bg: '#FFF8E1', text: '#FF9800', border: '#FF9800' };
      case 'low':
      default:
        return { bg: '#E8F5E9', text: '#4CAF50', border: '#4CAF50' };
    }
  };

  const riskColors = getRiskColor(pest?.risk_level);

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>🐛 Pest Analysis</Text>
        <Text style={styles.subtitle}>{cropType?.toUpperCase() || 'UNKNOWN'}</Text>
      </View>

      {/* Pest Assessment Card */}
      {pest && (
        <View style={[styles.card, styles.assessmentCard, { backgroundColor: riskColors.bg }]}>
          <Text style={[styles.sectionTitle, { color: riskColors.text }]}>Pest Risk Assessment</Text>
          <Text style={[styles.assessmentText, { color: riskColors.text }]}>
            {pestAssessment}
          </Text>
        </View>
      )}

      {/* Pest Risk Level Card */}
      {pest && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Risk Level Overview</Text>
          <View style={[styles.riskLevelContainer, { borderLeftColor: riskColors.border }]}>
            <Text style={[
              styles.pestRiskText,
              { color: riskColors.text }
            ]}>
              {pest.risk_level || 'Unknown'} Risk
            </Text>
            <Text style={styles.pestConfidenceText}>
              Confidence: {(pest.confidence * 100 || 0).toFixed(1)}%
            </Text>
          </View>
        </View>
      )}

      {/* Pest Probability Distribution */}
      {pest?.probabilities && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Pest Level Distribution</Text>
          <View style={styles.probabilityContainer}>
            {Object.entries(pest.probabilities).map(([level, prob]: [string, any]) => (
              <View key={`prob-${level}`} style={styles.probabilityItem}>
                <Text style={styles.probabilityLabel}>{level}</Text>
                <View style={styles.probabilityBar}>
                  <View 
                    style={[
                      styles.probabilityFill,
                      { 
                        width: `${(prob * 100)}%`,
                        backgroundColor: level === 'High' ? '#F44336' : level === 'Medium' ? '#FF9800' : '#4CAF50'
                      }
                    ]}
                  />
                </View>
                <Text style={styles.probabilityValue}>{(prob * 100).toFixed(1)}%</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* Pest Level Information */}
      {penalties && penalties.pest_level && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Pest Impact Multiplier</Text>
          <View style={styles.pestLevelContainer}>
            <View style={styles.levelRow}>
              <Text style={styles.levelLabel}>Pest Level:</Text>
              <Text style={styles.levelValue}>{penalties.pest_level.label || 'N/A'}</Text>
            </View>
            <View style={styles.levelRow}>
              <Text style={styles.levelLabel}>Yield Impact:</Text>
              <Text style={styles.levelValue}>
                {(penalties.pest_level.multiplier * 100 || 0).toFixed(1)}%
              </Text>
            </View>
            <Text style={styles.levelExplain}>
              This multiplier represents the potential impact on your crop yield if pest pressure is not managed.
            </Text>
          </View>
        </View>
      )}

      {/* Pest Recommendations */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>🎯 Pest Management Recommendations</Text>
        <View style={styles.recommendationsContainer}>
          {pestRecommendations.map((rec: string, index: number) => (
            <View key={`pest-${index}`} style={styles.recommendationItem}>
              <View style={styles.bulletPoint}>
                <Text style={styles.bulletText}>{index + 1}</Text>
              </View>
              <Text style={styles.recommendationText}>{rec}</Text>
            </View>
          ))}
        </View>
      </View>

      {/* Monitoring Schedule */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>📅 Monitoring Schedule</Text>
        <View style={styles.monitoringContainer}>
          <Text style={styles.monitoringText}>
            {pest?.risk_level === 'High' 
              ? '🔴 Daily monitoring recommended (Morning and Evening)'
              : pest?.risk_level === 'Medium'
              ? '🟡 Every 2-3 days monitoring recommended'
              : '🟢 Weekly monitoring sufficient'}
          </Text>
          <Text style={styles.monitoringTip}>
            • Best time to scout: Early morning (6-8 AM) when temperatures are cool
          </Text>
          <Text style={styles.monitoringTip}>
            • Check 10 random plants per plot or 100 plants per field
          </Text>
          <Text style={styles.monitoringTip}>
            • Look for pest adults, nymphs, eggs, and damage symptoms
          </Text>
        </View>
      </View>

      {/* Economic Impact */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>💰 Economic Considerations</Text>
        <View style={styles.economicContainer}>
          <Text style={styles.economicText}>
            {pest?.risk_level === 'High'
              ? `Potential yield loss without treatment: 20-40%\n\nImmediate treatment is recommended to minimize losses.`
              : pest?.risk_level === 'Medium'
              ? `Potential yield loss without treatment: 5-15%\n\nTimely treatment within 3-5 days is advisable.`
              : `Potential yield loss without treatment: 0-5%\n\nPreventive monitoring is sufficient.`}
          </Text>
        </View>
      </View>

      {/* Confidence Meter */}
      {pest && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Detection Confidence</Text>
          <View style={styles.confidenceContainer}>
            <ConfidenceMeter 
              label="Pest Detection" 
              value={pest.confidence || 0} 
              color={pest.risk_level === 'Low' ? '#4CAF50' : 
                     pest.risk_level === 'Medium' ? '#FF9800' : '#F44336'} 
            />
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
      <Text style={styles.confidenceText}>{(value * 100).toFixed(1)}%</Text>
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
  assessmentCard: {
    borderRadius: 12
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 15,
    color: '#333',
    textAlign: 'center'
  },
  assessmentText: {
    fontSize: 14,
    lineHeight: 22,
    fontWeight: '500'
  },
  riskLevelContainer: {
    paddingVertical: 15,
    paddingHorizontal: 15,
    borderLeftWidth: 4,
    backgroundColor: '#F5F5F5',
    borderRadius: 8
  },
  pestRiskText: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 8
  },
  pestConfidenceText: {
    fontSize: 14,
    color: '#666',
    fontWeight: '500'
  },
  pestLevelContainer: {
    paddingVertical: 12
  },
  levelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0'
  },
  levelLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#555'
  },
  levelValue: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#2E8B57'
  },
  levelExplain: {
    fontSize: 12,
    color: '#999',
    fontStyle: 'italic',
    marginTop: 10
  },
  probabilityContainer: {
    paddingVertical: 10
  },
  probabilityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
    gap: 10
  },
  probabilityLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
    width: 60
  },
  probabilityBar: {
    flex: 1,
    height: 24,
    backgroundColor: '#E0E0E0',
    borderRadius: 12,
    overflow: 'hidden'
  },
  probabilityFill: {
    height: '100%',
    borderRadius: 12
  },
  probabilityValue: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#333',
    width: 50,
    textAlign: 'right'
  },
  recommendationsContainer: {
    paddingVertical: 10
  },
  recommendationItem: {
    flexDirection: 'row',
    marginBottom: 12,
    gap: 12
  },
  bulletPoint: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#E8F5E9',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 2
  },
  bulletText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#2E8B57'
  },
  recommendationText: {
    flex: 1,
    fontSize: 14,
    lineHeight: 20,
    color: '#333',
    paddingTop: 6
  },
  monitoringContainer: {
    paddingVertical: 10
  },
  monitoringText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2E8B57',
    marginBottom: 12,
    lineHeight: 24
  },
  monitoringTip: {
    fontSize: 13,
    color: '#555',
    marginBottom: 8,
    lineHeight: 18
  },
  economicContainer: {
    paddingVertical: 10
  },
  economicText: {
    fontSize: 14,
    lineHeight: 22,
    color: '#333'
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
    marginBottom: 8
  },
  confidenceMeter: {
    height: 24,
    backgroundColor: '#E0E0E0',
    borderRadius: 12,
    overflow: 'hidden',
    position: 'relative',
    justifyContent: 'center'
  },
  confidenceFill: {
    height: '100%',
    borderRadius: 12
  },
  confidenceText: {
    position: 'absolute',
    right: 12,
    fontSize: 12,
    fontWeight: 'bold',
    color: 'white',
    textShadowColor: '#000',
    textShadowOffset: { width: 1, height: 1 },
    textShadowRadius: 2
  },
  backButton: {
    backgroundColor: '#2196F3',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 10,
    marginBottom: 20
  },
  backButtonText: {
    color: 'white',
    fontWeight: 'bold',
    fontSize: 16
  }
});