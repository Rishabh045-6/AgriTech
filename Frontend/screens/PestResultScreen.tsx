// screens/PestResultScreen.tsx
import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Dimensions
} from 'react-native';

type PestResultScreenProps = {
  route: any;
  navigation: any;
};

export default function PestResultScreen({ route, navigation }: PestResultScreenProps) {
  const { results, cropType } = route.params;
  const { pest, recommendations, penalties } = results;

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>🐛 Pest Analysis</Text>
        <Text style={styles.subtitle}>{cropType.toUpperCase()}</Text>
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

      {/* Pest Level Information */}
      {penalties && penalties.pest_level && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Pest Level</Text>
          <View style={styles.pestLevelContainer}>
            <Text style={styles.pestLevel}>Level: {penalties.pest_level.label}</Text>
            <Text style={styles.pestMultiplier}>Multiplier: {(penalties.pest_level.multiplier * 100).toFixed(0)}%</Text>
          </View>
        </View>
      )}

      {/* Confidence Meter */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Confidence Level</Text>
        <View style={styles.confidenceContainer}>
          <ConfidenceMeter 
            label="Pest" 
            value={pest.confidence} 
            color={pest.risk_level === 'Low' ? '#4CAF50' : 
                   pest.risk_level === 'Medium' ? '#FF9800' : '#F44336'} 
          />
        </View>
      </View>

      {/* Pest Recommendations */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Pest Recommendations</Text>
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

const { width } = Dimensions.get('window');

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
  pestLevelContainer: {
    paddingVertical: 10
  },
  pestLevel: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 5
  },
  pestMultiplier: {
    fontSize: 14,
    color: '#666'
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
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 15,
    color: '#333',
    textAlign: 'center'
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
  recommendationsContainer: {
    paddingVertical: 10
  },
  recommendationItem: {
    backgroundColor: '#FCE4EC',
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