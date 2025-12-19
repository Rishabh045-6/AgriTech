// screens/ResultsScreen.tsx
import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  Alert,
  Platform
} from 'react-native';

type ResultsScreenProps = {
  route: any;
  navigation: any;
};

export default function ResultsScreen({ route, navigation }: ResultsScreenProps) {
  const { farmerId } = route.params;
  const [plotData, setPlotData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch plot data on mount
  useEffect(() => {
    const fetchPlotData = async () => {
      try {
        // ✅ Use correct IP for Android
        const API_URL = Platform.OS === 'android' 
          ? 'http://192.168.31.20:3001'  // Your PC's IP
          : 'http://localhost:3001';
        
        const response = await fetch(`${API_URL}/api/plot-data/${farmerId}`);
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        const data = await response.json();
        setPlotData(data);
      } catch (error: any) {
        console.error('Fetch error:', error);
        setError(error.message || 'Failed to load plot data');
      } finally {
        setLoading(false);
      }
    };

    fetchPlotData();
  }, [farmerId]);

  if (loading) {
    return (
      <View style={styles.container}>
        <Text>Loading analysis...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.container}>
        <Text>Error: {error}</Text>
      </View>
    );
  }

  // Mock data for agritech dashboards (replace with real ML output later)
  const mockData = {
    cropHealth: {
      healthy: 78,
      stressed: 15,
      diseased: 7,
      total: 100
    },
    soilHealth: {
      overall: 'Good',
      nitrogen: { current: 25, optimal: 30, status: 'Low' },
      phosphorus: { current: 18, optimal: 20, status: 'Adequate' },
      potassium: { current: 10, optimal: 15, status: 'Low' },
      ph: { current: 6.2, optimal: 6.5, status: 'Adequate' },
      composition: { sand: 45, silt: 30, clay: 25 }
    },
    pestStatus: {
      detected: true,
      riskProbability: 65,
      threats: [
        { name: 'Fall Armyworm', probability: 45 },
        { name: 'Corn Borer', probability: 30 },
        { name: 'Aphids', probability: 25 }
      ]
    },
    recommendations: [
      "Apply nitrogen fertilizer at 50 kg/acre to address deficiency",
      "Use neem oil spray to control Fall Armyworm infestation",
      "Maintain soil pH by adding lime if drops below 6.0",
      "Rotate crops with legumes to improve soil structure"
    ]
  };

  return (
    <ScrollView style={styles.container}>
      {/* 1. Overview Dashboard */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Overview Dashboard</Text>
        <View style={styles.statsGrid}>
          <StatCard 
            title="Healthy Crops" 
            value={`${mockData.cropHealth.healthy}%`} 
            color="#4CAF50" 
          />
          <StatCard 
            title="Stressed Crops" 
            value={`${mockData.cropHealth.stressed}%`} 
            color="#FF9800" 
          />
          <StatCard 
            title="Diseased Crops" 
            value={`${mockData.cropHealth.diseased}%`} 
            color="#F44336" 
          />
          <StatCard 
            title="Acres Analyzed" 
            value={`${plotData?.areaAcres || 0} ac`} 
            color="#2196F3" 
          />
        </View>
      </View>

      {/* 2. Soil Health Report */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Soil Health Report</Text>
        <Text style={styles.subtitle}>Overall Soil Health: <Text style={{ fontWeight: 'bold' }}>{mockData.soilHealth.overall}</Text></Text>
        
        <Text style={styles.subsectionTitle}>Nutrient Breakdown</Text>
        <NutrientRow nutrient="Nitrogen" data={mockData.soilHealth.nitrogen} />
        <NutrientRow nutrient="Phosphorus" data={mockData.soilHealth.phosphorus} />
        <NutrientRow nutrient="Potassium" data={mockData.soilHealth.potassium} />
        <NutrientRow nutrient="pH Level" data={mockData.soilHealth.ph} />
        
        <Text style={styles.subsectionTitle}>Soil Composition</Text>
        <CompositionBar label="Sand" value={mockData.soilHealth.composition.sand} color="#D7CCC8" />
        <CompositionBar label="Silt" value={mockData.soilHealth.composition.silt} color="#A1887F" />
        <CompositionBar label="Clay" value={mockData.soilHealth.composition.clay} color="#5D4037" />
      </View>

      {/* 3. Pest Status Dashboard */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Pest Status Dashboard</Text>
        <Text style={styles.subtitle}>
          Pests Detected: <Text style={{ fontWeight: 'bold', color: mockData.pestStatus.detected ? '#F44336' : '#4CAF50' }}>
            {mockData.pestStatus.detected ? 'Yes' : 'No'}
          </Text>
        </Text>
        
        {mockData.pestStatus.detected && (
          <>
            <Text style={styles.riskLabel}>Pest Risk Probability</Text>
            <RiskMeter percentage={mockData.pestStatus.riskProbability} />
            
            <Text style={styles.subsectionTitle}>Threat Analysis</Text>
            {mockData.pestStatus.threats.map((threat, index) => (
              <ThreatItem 
                key={index}
                name={threat.name}
                probability={threat.probability}
              />
            ))}
          </>
        )}
      </View>

      {/* 4. Smart Solutions Dashboard */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Smart Solutions Dashboard</Text>
        <Text style={styles.subtitle}>AI-Powered Recommendations</Text>
        {mockData.recommendations.map((rec, index) => (
          <RecommendationItem key={index} text={rec} />
        ))}
      </View>
    </ScrollView>
  );
}

// Helper Components
const StatCard = ({ title, value, color }: { title: string; value: string; color: string }) => (
  <View style={[styles.statCard, { borderColor: color }]}>
    <Text style={styles.statValue}>{value}</Text>
    <Text style={styles.statLabel}>{title}</Text>
  </View>
);

const NutrientRow = ({ nutrient, data }: { nutrient: string; data: any }) => (
  <View style={styles.nutrientRow}>
    <Text style={styles.nutrientLabel}>{nutrient}</Text>
    <Text>{data.current} (Optimal: {data.optimal})</Text>
    <Text style={{ 
      color: data.status === 'Low' ? '#F44336' : 
             data.status === 'High' ? '#FF9800' : '#4CAF50'
    }}>
      {data.status}
    </Text>
  </View>
);

const CompositionBar = ({ label, value, color }: { label: string; value: number; color: string }) => (
  <View style={styles.compositionRow}>
    <Text>{label}</Text>
    <View style={styles.compositionBar}>
      <View style={[styles.compositionFill, { width: `${value}%`, backgroundColor: color }]} />
    </View>
    <Text>{value}%</Text>
  </View>
);

const RiskMeter = ({ percentage }: { percentage: number }) => (
  <View style={styles.riskMeter}>
    <View style={styles.riskFill} style={{ width: `${percentage}%` }} />
    <Text style={styles.riskText}>{percentage}%</Text>
  </View>
);

const ThreatItem = ({ name, probability }: { name: string; probability: number }) => (
  <View style={styles.threatItem}>
    <Text>{name}</Text>
    <Text>{probability}%</Text>
  </View>
);

const RecommendationItem = ({ text }: { text: string }) => (
  <View style={styles.recommendationItem}>
    <Text>• {text}</Text>
  </View>
);

// Styles
const styles = StyleSheet.create({
  container: { 
    flex: 1, 
    padding: 16, 
    backgroundColor: '#F5F5F5' 
  },
  section: { 
    backgroundColor: 'white', 
    padding: 16, 
    marginBottom: 16, 
    borderRadius: 8 
  },
  sectionTitle: { 
    fontSize: 20, 
    fontWeight: 'bold', 
    marginBottom: 12,
    color: '#333'
  },
  subtitle: { 
    fontSize: 16, 
    marginBottom: 12,
    color: '#666'
  },
  subsectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginTop: 12,
    marginBottom: 8
  },
  statsGrid: { 
    flexDirection: 'row', 
    flexWrap: 'wrap', 
    justifyContent: 'space-between' 
  },
  statCard: { 
    width: '48%', 
    padding: 12, 
    borderWidth: 2, 
    borderRadius: 8,
    marginBottom: 8
  },
  statValue: { 
    fontSize: 24, 
    fontWeight: 'bold' 
  },
  statLabel: { 
    fontSize: 12, 
    color: '#666' 
  },
  nutrientRow: { 
    flexDirection: 'row', 
    justifyContent: 'space-between', 
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#EEE'
  },
  nutrientLabel: { 
    fontWeight: '500' 
  },
  compositionRow: { 
    flexDirection: 'row', 
    alignItems: 'center', 
    paddingVertical: 6 
  },
  compositionBar: { 
    flex: 1, 
    height: 12, 
    backgroundColor: '#EEE', 
    marginLeft: 12, 
    marginRight: 12,
    borderRadius: 6
  },
  compositionFill: { 
    height: '100%', 
    borderRadius: 6 
  },
  riskLabel: {
    fontWeight: '600',
    marginBottom: 8
  },
  riskMeter: {
    height: 24,
    backgroundColor: '#EEE',
    borderRadius: 12,
    marginBottom: 12,
    position: 'relative'
  },
  riskFill: {
    height: '100%',
    backgroundColor: '#F44336',
    borderRadius: 12,
    width: '65%' // Will be dynamic later
  },
  riskText: {
    position: 'absolute',
    top: 2,
    right: 8,
    fontWeight: 'bold',
    color: 'white'
  },
  threatItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6
  },
  recommendationItem: {
    paddingVertical: 8,
    paddingLeft: 12,
    borderLeftWidth: 3,
    borderLeftColor: '#4CAF50',
    marginBottom: 8
  }
});