import React, { useEffect, useState, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Platform,
  TouchableOpacity,
  ActivityIndicator
} from 'react-native';
// Import the RecommendationsSystem component
import RecommendationsSystem from './RecommendationsSystem';

/* =========================
   Helper functions
========================= */
const getDiseaseExplanation = (risk: string) => {
  if (risk === 'LOW') return 'Crop shows no visible disease stress.';
  if (risk === 'MEDIUM') return 'Early disease signs possible. Monitor closely.';
  return 'High disease stress detected. Immediate action recommended.';
};

const getPestExplanation = (risk: string) => {
  if (risk === 'Low') return 'Pest pressure is minimal.';
  if (risk === 'Medium') return 'Moderate pest activity. Increase monitoring.';
  return 'High pest pressure detected. Control measures advised.';
};

const getYieldExplanation = (category: string) => {
  if (category === 'high') return 'Yield potential is strong compared to average.';
  if (category === 'medium') return 'Yield is near expected average.';
  return 'Yield is below average. Stress factors are limiting production.';
};

/* =========================
   Summary Section
========================= */
const SummarySection = ({ results }: { results: any }) => {
  const [showDetails, setShowDetails] = useState(false);

  const { stage, disease, pest, yield: yieldData } = results;

  return (
    <View style={styles.resultCard}>
      <Text style={styles.sectionTitle}>📊 Crop Summary</Text>

      {/* Stage */}
      <Text style={styles.summaryText}>
        🌱 Stage: <Text style={styles.bold}>{stage.prediction}</Text>
      </Text>
      <Text style={styles.subText}>
        Confidence: {(stage.confidence * 100).toFixed(1)}%
      </Text>

      {/* Disease */}
      <Text style={styles.summaryText}>
        🦠 Disease Risk: <Text style={styles.bold}>{disease.risk_level}</Text>
      </Text>
      <Text style={styles.subText}>
        Probability: {(disease.probability * 100).toFixed(1)}%
      </Text>

      {/* Pest */}
      <Text style={styles.summaryText}>
        🐛 Pest Risk: <Text style={styles.bold}>{pest.risk_level}</Text>
      </Text>
      <Text style={styles.subText}>
        Confidence: {(pest.confidence * 100).toFixed(1)}%
      </Text>

      {/* Yield */}
      {yieldData && (
        <>
          <Text style={styles.summaryText}>
            🌾 Estimated Yield:{' '}
            <Text style={styles.bold}>
              {yieldData.estimated_yield_kg_ha.toFixed(0)} kg/ha
            </Text>
          </Text>
          <Text style={styles.subText}>
            Category: {yieldData.category?.label}
          </Text>
        </>
      )}

      {/* Toggle */}
      <TouchableOpacity
        style={styles.toggleButton}
        onPress={() => setShowDetails(!showDetails)}
      >
        <Text style={styles.toggleText}>
          {showDetails ? 'Hide details ▲' : 'Show details ▼'}
        </Text>
      </TouchableOpacity>

      {/* Details */}
      {showDetails && (
        <View style={styles.detailsBox}>
          <Text style={styles.detailText}>
            🌱 Stage Insight: Crop is currently in a critical growth phase.
          </Text>
          <Text style={styles.detailText}>
            🦠 Disease Insight: {getDiseaseExplanation(disease.risk_level)}
          </Text>
          <Text style={styles.detailText}>
            🐛 Pest Insight: {getPestExplanation(pest.risk_level)}
          </Text>
          {yieldData && (
            <Text style={styles.detailText}>
              🌾 Yield Insight:{' '}
              {getYieldExplanation(yieldData.category?.name)}
            </Text>
          )}
        </View>
      )}
    </View>
  );
};

type WaterStressLevel =
  | 'Optimal'
  | 'Mild Stress'
  | 'Moderate Stress'
  | 'Severe Stress';

const WaterStressCard = ({ waterStress }: { waterStress: any }) => {
  if (!waterStress || !waterStress.current_status) return null;

  const WATER_STRESS_COLORS: Record<WaterStressLevel, string> = {
    Optimal: '#4CAF50',
    'Mild Stress': '#FFC107',
    'Moderate Stress': '#FF9800',
    'Severe Stress': '#F44336'
  };

  const level = waterStress.current_status.moisture_status as WaterStressLevel;
  const statusColor = WATER_STRESS_COLORS[level] ?? '#666';

  return (
    <View style={styles.resultCard}>
      <Text style={styles.sectionTitle}>💧 Water Stress Analysis</Text>

      <View style={styles.waterStressContainer}>
        <Text style={styles.waterStressScore}>Stress Score: {waterStress.current_status.water_stress.toFixed(1)}/100</Text>
        <Text style={[styles.waterStressStatus, { color: statusColor }]}>
          Status: {waterStress.current_status.moisture_status}
        </Text>
        <Text style={styles.irrigationAdvice}>
          {waterStress.current_status.irrigation_advice}
        </Text>
      </View>

      {/* Stress Drivers */}
      {waterStress.current_status.stress_drivers && waterStress.current_status.stress_drivers.length > 0 && (
        <View style={styles.stressDriversContainer}>
          <Text style={styles.driversTitle}>🔍 Stress Drivers:</Text>
          {waterStress.current_status.stress_drivers.map((driver: any, index: number) => (
            <View key={index} style={styles.driverItem}>
              <Text style={styles.driverFactor}>• {driver.factor}</Text>
              <Text style={styles.driverDescription}>{driver.description}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
};

// Add this component after your SummarySection component
const ConfidenceMeterCard = ({ stage, disease, pest }: { stage: any; disease: any; pest: any }) => (
  <View style={styles.confidenceCard}>
    <Text style={styles.sectionTitle}>📊 Confidence Levels</Text>

    <View style={styles.confidenceRow}>
      <Text style={styles.confidenceLabel}>Stage</Text>
      <View style={styles.confidenceBarContainer}>
        <View
          style={[
            styles.confidenceBar,
            {
              width: `${stage.confidence * 100}%`,
              backgroundColor: '#4CAF50'
            }
          ]}
        />
        <Text style={styles.confidenceValue}>{(stage.confidence * 100).toFixed(1)}%</Text>
      </View>
    </View>

    <View style={styles.confidenceRow}>
      <Text style={styles.confidenceLabel}>Disease</Text>
      <View style={styles.confidenceBarContainer}>
        <View
          style={[
            styles.confidenceBar,
            {
              width: `${disease.probability * 100}%`,
              backgroundColor: disease.risk_level === 'LOW' ? '#4CAF50' : disease.risk_level === 'MEDIUM' ? '#FF9800' : '#F44336'
            }
          ]}
        />
        <Text style={styles.confidenceValue}>{(disease.probability * 100).toFixed(1)}%</Text>
      </View>
    </View>

    <View style={styles.confidenceRow}>
      <Text style={styles.confidenceLabel}>Pest</Text>
      <View style={styles.confidenceBarContainer}>
        <View
          style={[
            styles.confidenceBar,
            {
              width: `${pest.confidence * 100}%`,
              backgroundColor: pest.risk_level === 'Low' ? '#4CAF50' : pest.risk_level === 'Medium' ? '#FF9800' : '#F44336'
            }
          ]}
        />
        <Text style={styles.confidenceValue}>{(pest.confidence * 100).toFixed(1)}%</Text>
      </View>
    </View>
  </View>
);

/* =========================
   Main Screen
========================= */
export default function ResultsScreen({ route, navigation }: any) {
  const { farmerId, cropType, modelResults, plotId } = route.params; // Add plotId to params

  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchResults = useCallback(async () => {
    try {
      const API_URL =
        Platform.OS === 'android'
          ? 'http://10.67.1.211:3001'
          : 'http://localhost:3001';

      const response = await fetch(`${API_URL}/api/run-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ farmerId, cropType })
      });

      const data = await response.json();
      setResults(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load results');
    } finally {
      setLoading(false);
    }
  }, [farmerId, cropType]);

  useEffect(() => {
    if (modelResults) {
      setResults(modelResults);
      setLoading(false);
    } else {
      fetchResults();
    }
  }, [modelResults, fetchResults]);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#2E8B57" />
        <Text style={styles.loadingText}>Analyzing crop data…</Text>
      </View>
    );
  }

  if (error || !results?.success) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>
          {error || 'No results available'}
        </Text>
      </View>
    );
  }

  // Aggregate features from the results for the RecommendationsSystem
  const aggregatedFeatures = {
    // Example mapping - adjust based on your actual modelResults structure
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
    nutrient_deficiency: results.nutrientDeficiency || {}, // Assuming this comes from results
    stage_classifier: {
      stage: results.stage?.prediction || "unknown"
    },
    // Add other features if available in results
  };

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>🌾 Crop Analysis Results</Text>
        <Text style={styles.subtitle}>{cropType.toUpperCase()}</Text>
      </View>

      {/* Summary Section */}
      <SummarySection results={results} />

      {results && results.stage && results.disease && results.pest && (
        <ConfidenceMeterCard
          stage={results.stage}
          disease={results.disease}
          pest={results.pest}
        />
      )}


      <View style={{ marginBottom: 16 }}>
        <RecommendationsSystem
          farmerId={farmerId}
          plotId={plotId}
          plotFeatures={aggregatedFeatures}
          directRecommendations={results?.recommendations}
          recommendationDetails={results?.recommendation_details}
        />
      </View>


      {/* Add this to your main component after the confidence meter*/}
      {results && results.waterStress && (
        <WaterStressCard waterStress={results.waterStress} />
      )}


      {/* Navigation Cards */}
      <ResultNavCard
        title="🌱 Stage Analysis"
        subtitle={`Stage: ${results.stage.prediction}`}
        onPress={() =>
          navigation.navigate('StageResult', { results, cropType })
        }
      />

      <ResultNavCard
        title="🦠 Disease Analysis"
        subtitle={`Risk: ${results.disease.risk_level}`}
        onPress={() =>
          navigation.navigate('DiseaseResult', { results, cropType, recommendations: results?.recommendations, recommendationDetails: results?.recommendation_details, plotId, farmerId })
        }
      />

      <ResultNavCard
        title="🐛 Pest Analysis"
        subtitle={`Risk: ${results.pest.risk_level}`}
        onPress={() =>
          navigation.navigate('PestResult', { results, cropType, recommendations: results?.recommendations, recommendationDetails: results?.recommendation_details, plotId, farmerId })
        }
      />

      <TouchableOpacity
        style={styles.backButton}
        onPress={() => navigation.goBack()}
      >
        <Text style={styles.backButtonText}>← Back to Map</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

/* =========================
   Navigation Card
========================= */
const ResultNavCard = ({
  title,
  subtitle,
  onPress
}: {
  title: string;
  subtitle: string;
  onPress: () => void;
}) => (
  <TouchableOpacity style={styles.resultCard} onPress={onPress}>
    <View style={styles.cardHeader}>
      <Text style={styles.cardTitle}>{title}</Text>
      <Text style={styles.arrow}>→</Text>
    </View>
    <Text style={styles.cardText}>{subtitle}</Text>
  </TouchableOpacity>
);

/* =========================
   Styles
========================= */
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FA', padding: 16 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { marginTop: 20, fontSize: 18, color: '#2E8B57' },
  errorText: { fontSize: 16, color: '#F44336', textAlign: 'center' },

  header: { alignItems: 'center', marginBottom: 20 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#2E8B57' },
  subtitle: { fontSize: 16, color: '#666' },

  resultCard: {
    backgroundColor: '#FFF',
    padding: 20,
    borderRadius: 12,
    marginBottom: 16,
    elevation: 3
  },
  waterStressContainer: {
    paddingVertical: 10
  },
  waterStressScore: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 5
  },
  waterStressStatus: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 5
  },
  irrigationAdvice: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
    marginBottom: 10
  },
  stressDriversContainer: {
    marginTop: 10
  },
  driversTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 5
  },
  driverItem: {
    marginBottom: 5
  },
  driverFactor: {
    fontWeight: 'bold',
    color: '#333'
  },
  driverDescription: {
    fontSize: 12,
    color: '#666',
    marginLeft: 10
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10
  },
  summaryText: { fontSize: 15, marginBottom: 4 },
  subText: { fontSize: 13, color: '#666', marginBottom: 6 },
  bold: { fontWeight: 'bold' },

  toggleButton: { marginTop: 10 },
  toggleText: {
    color: '#2196F3',
    fontWeight: 'bold',
    textAlign: 'center'
  },
  detailsBox: {
    marginTop: 12,
    backgroundColor: '#F1F8E9',
    padding: 10,
    borderRadius: 8
  },
  detailText: { fontSize: 13, marginBottom: 6 },

  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 6
  },
  cardTitle: { fontSize: 18, fontWeight: 'bold' },
  arrow: { fontSize: 18, color: '#2E8B57' },
  cardText: { fontSize: 14, color: '#666' },

  backButton: {
    backgroundColor: '#2196F3',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
    marginVertical: 20
  },
  backButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: 'bold'
  },

  // Confidence Meter Styles
  confidenceCard: {
    backgroundColor: '#FFF',
    padding: 20,
    borderRadius: 12,
    marginBottom: 16,
    elevation: 3
  },
  confidenceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12
  },
  confidenceLabel: {
    fontSize: 14,
    color: '#333',
    width: 80
  },
  confidenceBarContainer: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    height: 20,
    backgroundColor: '#E0E0E0',
    borderRadius: 10,
    overflow: 'hidden',
    marginLeft: 10
  },
  confidenceBar: {
    height: '100%',
    borderRadius: 10
  },
  confidenceValue: {
    position: 'absolute',
    right: 10,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
    fontSize: 12,
    fontWeight: 'bold',
    color: 'white'
  }
});
