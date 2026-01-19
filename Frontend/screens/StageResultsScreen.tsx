// screens/StageResultScreen.tsx
import React, { useEffect, useState } from 'react';
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

type StageResultScreenProps = {
  route: any;
  navigation: any;
};

const EMPTY_VEGETATION_INDICES: Record<string, string> = {
  NDVI: 'N/A',
  GNDVI: 'N/A',
  SAVI: 'N/A',
  NDMI: 'N/A',
  MSI: 'N/A',
  NDWI: 'N/A',
  NMDI: 'N/A',
  NDRE: 'N/A',
  CIredEdge: 'N/A',
  CIgreen: 'N/A',
  PSRI: 'N/A',
  SIPI: 'N/A',
};

export default function StageResultScreen({ route, navigation }: StageResultScreenProps) {
  const { results, cropType } = route.params;

  // Extract data from results (matches growth_performance.py structure)
  const {
    stage,
    scores,
    report,
    ndviTrend,
    recommendations,
    data_summary: dataSummary,
    window_df,
    yield: yieldData,
    waterStress,
    nutrientDeficiency
  } = results;

  const getVegetationIndices = (): Record<string, string> => {
    if (window_df && window_df.length > 0) {
      const latestData = window_df[window_df.length - 1];
      return {
        NDVI: latestData.NDVI?.toFixed(3) ?? 'N/A',
        GNDVI: latestData.GNDVI?.toFixed(3) ?? 'N/A',
        SAVI: latestData.SAVI?.toFixed(3) ?? 'N/A',
        NDMI: latestData.NDMI?.toFixed(3) ?? 'N/A',
        MSI: latestData.MSI?.toFixed(3) ?? 'N/A',
        NDWI: latestData.NDWI?.toFixed(3) ?? 'N/A',
        NMDI: latestData.NMDI?.toFixed(3) ?? 'N/A',
        NDRE: latestData.NDRE?.toFixed(3) ?? 'N/A',
        CIredEdge: latestData.CIredEdge?.toFixed(3) ?? 'N/A',
        CIgreen: latestData.CIgreen?.toFixed(3) ?? 'N/A',
        PSRI: latestData.PSRI?.toFixed(3) ?? 'N/A',
        SIPI: latestData.SIPI?.toFixed(3) ?? 'N/A',
      };
    }
    return EMPTY_VEGETATION_INDICES;
  };

  const vegetationIndices = getVegetationIndices();

  // Format NDVI trend data with proper dates
  const formattedNdviTrend = ndviTrend?.map((point: any) => ({
    date: new Date(point.date).toLocaleDateString(),
    ndvi: point.ndvi
  })) || [];

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>🌱 Stage Analysis</Text>
        <Text style={styles.subtitle}>{cropType.toUpperCase()}</Text>
      </View>

      {/* Yield */}
      {yieldData && <YieldCard yieldData={yieldData} />}

      {/* Growth Performance */}
      {scores && report && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Growth Performance</Text>
          <View style={styles.growthContainer}>
            <Text style={styles.growthScore}>Overall Score: {scores?.overall_score?.toFixed(1) ?? 'N/A'}</Text>
            <Text style={styles.growthStatus}>Status: {report?.status ?? 'N/A'}</Text>
            <Text style={styles.growthRecommendation}>Recommendation: {report?.recommendation ?? 'N/A'}</Text>
          </View>

          <View style={styles.growthMetricsContainer}>
            <GrowthMetricCard
              name="Growth Rate"
              score={scores?.growth_rate ?? 0}
              status={report?.status ?? 'Unknown'}
            />
            <GrowthMetricCard
              name="Biomass"
              score={scores?.biomass ?? 0}
              status={report?.status ?? 'Unknown'}
            />
            <GrowthMetricCard
              name="Stability"
              score={scores?.stability ?? 0}
              status={report?.status ?? 'Unknown'}
            />
          </View>
        </View>
      )}

      {/* Water Stress Analysis */}
      {waterStress && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>💧 Water Stress Analysis</Text>
          <View style={styles.waterStressContainer}>
            <Text style={styles.waterStressScore}>
              Stress Score: {waterStress?.score?.toFixed(1) ?? 'N/A'}
            </Text>
            <Text style={styles.waterStressStatus}>
              Status: {waterStress?.stress_level ?? 'N/A'}
            </Text>
            {waterStress?.recommendations && waterStress.recommendations.length > 0 && (
              <View style={styles.waterStressRecommendations}>
                <Text style={styles.waterStressLabel}>Recommendations:</Text>
                {waterStress.recommendations.map((rec: string, idx: number) => (
                  <Text key={idx} style={styles.waterStressAdvice}>
                    • {rec}
                  </Text>
                ))}
              </View>
            )}
          </View>
        </View>
      )}

      {/* Nutrient Deficiency Analysis */}
      {nutrientDeficiency && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>🧪 Nutrient Deficiency Analysis</Text>

          {/* Nitrogen */}
          {nutrientDeficiency.nitrogen && (
            <View style={[styles.nutrientItem, { borderColor: nutrientDeficiency.nitrogen.color }]}>
              <Text style={[styles.nutrientTitle, { color: nutrientDeficiency.nitrogen.color }]}>
                🌿 Nitrogen ({(nutrientDeficiency.nitrogen.score / 5 * 100).toFixed(0)}%)
              </Text>
              <Text style={[styles.nutrientLevel, { color: nutrientDeficiency.nitrogen.color }]}>
                {nutrientDeficiency.nitrogen.level}
              </Text>
              <Text style={styles.nutrientScore}>
                Score: {nutrientDeficiency.nitrogen.score}/5 | Threshold: {nutrientDeficiency.nitrogen.threshold_used}
              </Text>
              <Text style={styles.nutrientRecommendation}>
                {nutrientDeficiency.nitrogen.recommendation}
              </Text>
            </View>
          )}

          {/* Chlorophyll */}
          {nutrientDeficiency.chlorophyll && (
            <View style={[styles.nutrientItem, { borderColor: nutrientDeficiency.chlorophyll.color }]}>
              <Text style={[styles.nutrientTitle, { color: nutrientDeficiency.chlorophyll.color }]}>
                🟢 Chlorophyll ({(nutrientDeficiency.chlorophyll.value * 100).toFixed(0)}%)
              </Text>
              <Text style={[styles.nutrientLevel, { color: nutrientDeficiency.chlorophyll.color }]}>
                {nutrientDeficiency.chlorophyll.level}
              </Text>
              <Text style={styles.nutrientScore}>
                Value: {nutrientDeficiency.chlorophyll.value?.toFixed(3)} | Threshold: {nutrientDeficiency.chlorophyll.threshold?.toFixed(2)}
              </Text>
              <Text style={styles.nutrientRecommendation}>
                {nutrientDeficiency.chlorophyll.recommendation}
              </Text>
            </View>
          )}

          {/* Phosphorus */}
          {nutrientDeficiency.phosphorus && (
            <View style={[styles.nutrientItem, { borderColor: nutrientDeficiency.phosphorus.color }]}>
              <Text style={[styles.nutrientTitle, { color: nutrientDeficiency.phosphorus.color }]}>
                🪨 Phosphorus
              </Text>
              <Text style={[styles.nutrientLevel, { color: nutrientDeficiency.phosphorus.color }]}>
                {nutrientDeficiency.phosphorus.level}
              </Text>
              <Text style={styles.nutrientRecommendation}>
                {nutrientDeficiency.phosphorus.recommendation}
              </Text>
            </View>
          )}

          {/* Potassium */}
          {nutrientDeficiency.potassium && (
            <View style={[styles.nutrientItem, { borderColor: nutrientDeficiency.potassium.color }]}>
              <Text style={[styles.nutrientTitle, { color: nutrientDeficiency.potassium.color }]}>
                ⚡ Potassium
              </Text>
              <Text style={[styles.nutrientLevel, { color: nutrientDeficiency.potassium.color }]}>
                {nutrientDeficiency.potassium.level}
              </Text>
              <Text style={styles.nutrientRecommendation}>
                {nutrientDeficiency.potassium.recommendation}
              </Text>
            </View>
          )}

          {/* General Stress */}
          {nutrientDeficiency.general_stress && (
            <View style={[styles.nutrientItem, { borderColor: nutrientDeficiency.general_stress.color }]}>
              <Text style={[styles.nutrientTitle, { color: nutrientDeficiency.general_stress.color }]}>
                ⚠️ General Stress ({(nutrientDeficiency.general_stress.score / 4 * 100).toFixed(0)}%)
              </Text>
              <Text style={[styles.nutrientLevel, { color: nutrientDeficiency.general_stress.color }]}>
                {nutrientDeficiency.general_stress.level}
              </Text>
              <Text style={styles.nutrientScore}>
                Score: {nutrientDeficiency.general_stress.score}/4 | Threshold: {nutrientDeficiency.general_stress.threshold}
              </Text>
              <Text style={styles.nutrientRecommendation}>
                {nutrientDeficiency.general_stress.recommendation}
              </Text>
            </View>
          )}
        </View>
      )}

      {/* Vegetation Indices */}
      {Object.keys(vegetationIndices).length > 0 && (
        <VegetationIndicesCard vegetationIndices={vegetationIndices} />
      )}

      {/* Stage Probabilities */}
      {stage && <StageProbabilitiesCard stage={stage} />}

      {/* Stage Prediction */}
      {stage && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>Growth Stage Prediction</Text>
          <View style={styles.predictionContainer}>
            <Text style={styles.stageText}>{stage?.prediction ?? 'N/A'}</Text>
            <Text style={styles.confidenceOverlayText}>
              {(stage?.confidence * 100)?.toFixed(1) ?? '0'}% confidence
            </Text>
          </View>
        </View>
      )}

      {/* NDVI Trend */}
      {formattedNdviTrend.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>NDVI Trend Over Time</Text>
          <View style={styles.trendChart}>
            {formattedNdviTrend.map((point: any, index: number) => (
              <View key={index} style={styles.trendPoint}>
                <Text style={styles.trendDate}>{point.date}</Text>
                <View style={[styles.trendBar, { height: point.ndvi * 100 }]} />
                <Text style={styles.trendValue}>{point.ndvi.toFixed(2)}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* NDVI Statistics */}
      {dataSummary && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>NDVI Statistics</Text>
          <View style={styles.statsContainer}>
            <StatItem label="Mean" value={dataSummary?.mean_ndvi?.toFixed(3) ?? 'N/A'} />
            <StatItem label="Min" value={dataSummary?.min_ndvi?.toFixed(3) ?? 'N/A'} />
            <StatItem label="Max" value={dataSummary?.max_ndvi?.toFixed(3) ?? 'N/A'} />
            <StatItem label="Std Dev" value={dataSummary?.std_ndvi?.toFixed(3) ?? 'N/A'} />
          </View>
        </View>
      )}

      {/* Stage Recommendations */}
      {recommendations?.stage && (
        <View style={styles.card}>
          <Text style={styles.sectionTitle}>🌱 Stage Recommendations</Text>
          {recommendations.stage.map((rec: string, index: number) => (
            <View key={`stage-${index}`} style={styles.recommendationItem}>
              <Text style={styles.recommendationText}>• {rec}</Text>
            </View>
          ))}
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
const IndexCard = ({ label, value }: { label: string; value: string }) => (
  <View style={styles.indexCard}>
    <Text style={styles.indexLabel}>{label}</Text>
    <Text style={styles.indexValue}>{value}</Text>
  </View>
);

const VegetationIndicesCard = ({ vegetationIndices }: { vegetationIndices: Record<string, string> }) => (
  <View style={styles.card}>
    <Text style={styles.sectionTitle}>🌿 Vegetation Indices</Text>
    <View style={styles.indicesContainer}>
      <View style={styles.indexRow}>
        <IndexCard label="NDVI" value={vegetationIndices.NDVI} />
        <IndexCard label="GNDVI" value={vegetationIndices.GNDVI} />
        <IndexCard label="SAVI" value={vegetationIndices.SAVI} />
      </View>
      <View style={styles.indexRow}>
        <IndexCard label="NDMI" value={vegetationIndices.NDMI} />
        <IndexCard label="MSI" value={vegetationIndices.MSI} />
        <IndexCard label="NDWI" value={vegetationIndices.NDWI} />
      </View>
      <View style={styles.indexRow}>
        <IndexCard label="NMDI" value={vegetationIndices.NMDI} />
        <IndexCard label="NDRE" value={vegetationIndices.NDRE} />
        <IndexCard label="CIredEdge" value={vegetationIndices.CIredEdge} />
      </View>
      <View style={styles.indexRow}>
        <IndexCard label="CIgreen" value={vegetationIndices.CIgreen} />
        <IndexCard label="PSRI" value={vegetationIndices.PSRI} />
        <IndexCard label="SIPI" value={vegetationIndices.SIPI} />
      </View>
    </View>
  </View>
);

const StageProbabilitiesCard = ({ stage }: { stage: any }) => {
  if (!stage?.all_probabilities) return null;

  const sorted = Object.entries(stage.all_probabilities).sort(
    (a: any, b: any) => b[1] - a[1]
  );

  return (
    <View style={styles.card}>
      <Text style={styles.sectionTitle}>📊 Stage Probabilities</Text>

      {sorted.map(([stageName, probability]: any) => (
        <View key={stageName} style={styles.stageProbItem}>
          <Text style={styles.stageProbName}>{stageName}</Text>
          <Text style={styles.stageProbValue}>
            {(probability * 100).toFixed(1)}%
          </Text>
        </View>
      ))}
    </View>
  );
};

const GrowthMetricCard = ({ name, score, status }: any) => (
  <View style={styles.growthMetricCard}>
    <Text style={styles.growthMetricName}>{name}</Text>
    <Text style={styles.growthMetricValue}>{score.toFixed(1)}</Text>
    <Text style={styles.growthMetricStatus}>{status}</Text>
  </View>
);

const YieldCard = ({ yieldData }: any) => (
  <View style={styles.card}>
    <Text style={styles.sectionTitle}>🌾 Yield Prediction</Text>
    <Text style={styles.yieldScore}>
      Yield Score: {yieldData?.score?.toFixed(1) ?? 'N/A'}/100
    </Text>
    <Text style={styles.yieldCategory}>
      Category: {yieldData?.category?.label ?? 'N/A'}
    </Text>
    <Text style={styles.yieldEstimate}>
      Estimated: {yieldData?.estimated_yield_kg_ha?.toFixed(0) ?? 'N/A'} kg/ha
    </Text>
  </View>
);

const StatItem = ({ label, value }: any) => (
  <View style={styles.statItem}>
    <Text style={styles.statLabel}>{label}</Text>
    <Text style={styles.statValue}>{value}</Text>
  </View>
);

// Add these styles to your existing styles
const { width } = Dimensions.get('window');

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F8F9FA', padding: 16 },
  header: { alignItems: 'center', marginBottom: 20 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#2E8B57' },
  subtitle: { fontSize: 16, color: '#666' },
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
  growthContainer: {
    paddingVertical: 10
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
    width: (width - 52) / 3,
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
  confidenceText: {
    fontSize: 16,
    color: '#666'
  },
  stageContainer: {
    paddingVertical: 10
  },
  stageItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#eee'
  },
  stageName: {
    fontSize: 16,
    color: '#333',
    fontWeight: '500'
  },
  stageConfidence: {
    fontSize: 16,
    color: '#2E8B57',
    fontWeight: 'bold'
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
  yieldScore: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2E8B57',
    marginBottom: 4,
  },
  yieldCategory: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  yieldEstimate: {
    fontSize: 14,
    color: '#666',
  },
  waterStressContainer: {
    paddingVertical: 10
  },
  waterStressScore: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#1976D2',
    marginBottom: 5
  },
  waterStressStatus: {
    fontSize: 14,
    color: '#666',
    marginBottom: 5
  },
  waterStressAdvice: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
    marginTop: 5
  },
  waterStressLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginTop: 10,
    marginBottom: 5
  },
  waterStressRecommendations: {
    marginTop: 10,
    paddingLeft: 10
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
  confidenceOverlayText: {
    position: 'absolute',
    right: 10,
    top: 0,
    bottom: 0,
    justifyContent: 'center',
    fontSize: 12,
    fontWeight: 'bold',
    color: 'white',
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
  },
  indicesContainer: {
    padding: 10
  },
  indexRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10
  },
  indexCard: {
    width: (width - 60) / 3,
    backgroundColor: '#F8F9FA',
    padding: 10,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center'
  },
  indexLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#333',
    marginBottom: 5
  },
  indexValue: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#2E8B57'
  },
  stageProbabilitiesContainer: {
    paddingVertical: 10
  },
  stageProbItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 5
  },
  stageProbName: {
    fontSize: 14,
    color: '#333'
  },
  stageProbValue: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#2E8B57'
  },
  nutrientItem: {
    marginBottom: 15,
    padding: 15,
    backgroundColor: '#F8F9FA',
    borderRadius: 8,
    borderWidth: 2,
    borderStyle: 'solid'
  },
  nutrientTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 5
  },
  nutrientLevel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 3
  },
  nutrientScore: {
    fontSize: 13,
    color: '#666',
    marginBottom: 3
  },
  nutrientRecommendation: {
    fontSize: 13,
    color: '#666',
    fontStyle: 'italic'
  },
  // ... rest of your styles ...
});