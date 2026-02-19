// src/components/RecommendationsSystem.tsx
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ActivityIndicator,
    TouchableOpacity,
    Platform,
} from 'react-native';

const API_URL =
    Platform.OS === 'android'
        ? 'http://10.67.11.81:3001' // Make sure this IP is correct for your backend server
        : 'http://localhost:3001';

interface RecommendationItemProps {
    title: string;
    description: string;
    priority: number; // 1–4
    status: string;
    details?: string;
}

const getPriorityBadgeText = (priorityLevel: number): string => {
    const map: Record<number, string> = {
        1: 'CRITICAL',
        2: 'HIGH',
        3: 'MEDIUM',
        4: 'ADVISORY',
    };
    return map[priorityLevel] || 'UNKNOWN';
};

const RecommendationItem: React.FC<RecommendationItemProps> = ({
    title,
    description,
    priority,
    status,
    details,
}) => {
    const getPriorityColor = (p: number) => {
        switch (p) {
            case 1:
                return '#f44336';
            case 2:
                return '#ff9800';
            case 3:
                return '#4caf50';
            case 4:
                return '#9e9e9e';
            default:
                return '#64748b';
        }
    };

    return (
        <View style={styles.card}>
            <View style={styles.cardHeader}>
                <Text style={styles.cardTitle}>{title}</Text>
                <View
                    style={[
                        styles.priorityBadge,
                        { backgroundColor: getPriorityColor(priority) },
                    ]}
                >
                    <Text style={styles.priorityText}>
                        {getPriorityBadgeText(priority)}
                    </Text>
                </View>
            </View>

            <Text style={styles.status}>{status}</Text>
            {details ? <Text style={styles.details}>{details}</Text> : null}
            <Text style={styles.description}>{description}</Text>
        </View>
    );
};

interface RecommendationsSystemProps {
    plotId: string;
    farmerId: string;
    plotFeatures: any;
    directRecommendations?: any;
    recommendationDetails?: any;
}

const RecommendationsSystem: React.FC<RecommendationsSystemProps> = ({
    plotId,
    farmerId,
    plotFeatures,
    directRecommendations,
    recommendationDetails,
}) => {
    const [recommendations, setRecommendations] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expanded, setExpanded] = useState(false);

    // Update recommendations when direct recommendations prop changes
    useEffect(() => {
        if (directRecommendations) {
            console.log('Setting recommendations from directRecommendations:', directRecommendations);
            console.log('Recommendation details from prop:', recommendationDetails);
            setRecommendations({
                recommendations: directRecommendations,
                recommendation_details: recommendationDetails
            });
        }
    }, [directRecommendations, recommendationDetails]);

    const fetchRecommendations = useCallback(async () => {
        if (!plotId || !farmerId || !plotFeatures) {
            setError('Plot ID, Farmer ID, or Features data is missing.');
            return;
        }

        try {
            setLoading(true);
            setError(null);

            const response = await fetch(`${API_URL}/api/generate-recommendations`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plotId,
                    farmerId,
                    plotFeatures,
                }),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.error || 'Failed to fetch recommendations');
            }

            const data = await response.json();
            console.log('Fetched full response from backend:', data);
            console.log('Recommendations object from backend:', data.recommendations);
            console.log('Recommendation details from backend:', data.recommendation_details);
            setRecommendations(data);
        } catch (err: any) {
            setError(err.message || 'Unknown error');
        } finally {
            setLoading(false);
        }
    }, [plotId, farmerId, plotFeatures]);

    useEffect(() => {
        // If we have direct recommendations, don't fetch separately
        if (directRecommendations) {
            return;
        }

        if (expanded && plotId && farmerId && plotFeatures) {
            fetchRecommendations();
        }
    }, [expanded, plotId, farmerId, plotFeatures, fetchRecommendations, directRecommendations]);

    // Calculate 'recs' using useMemo to optimize and only re-calculate when 'recommendations' changes
    const recs = useMemo(() => {
        console.log('Recalculating recs based on new recommendations object...');
        if (
            recommendations?.recommendations &&
            typeof recommendations.recommendations === 'object' &&
            Object.keys(recommendations.recommendations).length > 0
        ) {
            console.log('Found non-empty recommendations object:', recommendations.recommendations);
            return recommendations.recommendations;
        } else {
             console.log('Recommendations object is empty or not an object:', recommendations?.recommendations);
        }
        return null;
    }, [recommendations]);

    // Debug useEffect - runs AFTER recs is recalculated (due to useMemo dependency)
    useEffect(() => {
        console.log('--- DEBUG START ---');
        console.log('Full recommendations state:', JSON.stringify(recommendations, null, 2));
        console.log('Direct recommendations prop:', directRecommendations);
        console.log('Recommendation details prop:', recommendationDetails);
        console.log('Calculated recs (using useMemo):', recs);
        console.log('Expanded state:', expanded);

        if (recs) {
            console.log('Keys in recs object:', Object.keys(recs));
            console.log('Value for "disease_detection" in recs:', recs['disease_detection']);
            console.log('Value for "pest_risk" in recs:', recs['pest_risk']);
            console.log('Value for "water_stress" in recs:', recs['water_stress']);
            console.log('Value for "nutrient_deficiency" in recs:', recs['nutrient_deficiency']);

            // Check recommendation details as well
            console.log('Full recommendation_details:', recommendations?.recommendation_details);
            console.log('Disease details:', recommendations?.recommendation_details?.disease_detection);
            console.log('Pest details:', recommendations?.recommendation_details?.pest_risk);
        }

        console.log('Has recommendations (recs exists and has keys):', !!recs && Object.keys(recs).length > 0);
        console.log('--- DEBUG END ---');
    }, [recommendations, directRecommendations, recommendationDetails, recs, expanded]); // Add 'recs' to the dependency array


    if (!plotId || !farmerId) return null;

    return (
        <View style={styles.container}>
            <TouchableOpacity style={styles.header} onPress={() => setExpanded(!expanded)}>
                <Text style={styles.headerTitle}>Next Recommended Steps</Text>
                {recs && Object.keys(recs).length > 0 && (
                    <View style={styles.badge}>
                        <Text style={styles.badgeText}>{Object.keys(recs).length}</Text>
                    </View>
                )}
                <Text style={styles.chevron}>{expanded ? '▲' : '▼'}</Text>
            </TouchableOpacity>

            {(expanded || recs) && ( // Consider expanding if recs are available from props
                <View style={styles.content}>
                    {loading && (
                        <View style={styles.center}>
                            <ActivityIndicator size="large" color="#0d9f5f" />
                            <Text style={styles.loadingText}>
                                Generating recommendations...
                            </Text>
                        </View>
                    )}

                    {error && (
                        <View style={styles.center}>
                            <Text style={styles.errorText}>{error}</Text>
                        </View>
                    )}

                    {!loading &&
                        !error &&
                        recs &&
                        Object.entries(recs).map(
                            ([key, value]: any) => {
                                console.log(`Rendering item for key: ${key}, value:`, value); // Log each item being rendered
                                let title = key.replace(/_/g, ' ').toUpperCase();
                                let priority = 4;
                                let status =
                                    recommendations.recommendation_details?.[key]?.level || 'N/A';
                                let details = '';

                                if (key === 'disease_detection') {
                                    title = 'Disease Management';
                                    priority =
                                        status === 'high' ? 1 : status === 'medium' ? 2 : 4;
                                    details = `Probability: ${(recommendations.recommendations?.[key]?.probability ||
                                            0) * 100
                                        }%`;
                                }

                                if (key === 'water_stress') {
                                    title = 'Water Management';
                                    priority =
                                        status === 'severe'
                                            ? 1
                                            : status === 'moderate'
                                                ? 2
                                                : status === 'mild'
                                                    ? 3
                                                    : 4;
                                    details = `Score: ${recommendations.recommendation_details?.[key]?.score
                                        }`;
                                }

                                if (key === 'pest_risk') {
                                    title = 'Pest Management';
                                    priority =
                                        status === 'high' ? 1 : status === 'medium' ? 2 : 4;
                                    details = `Confidence: ${(recommendations.recommendation_details?.[key]?.confidence ||
                                            0) * 100
                                        }%`;
                                }

                                // Add condition for nutrient deficiency if needed
                                if (key === 'nutrient_deficiency') {
                                    title = 'Nutrient Management';
                                    priority = status === 'high' ? 2 : status === 'moderate' ? 3 : 4; // Adjust priority logic as needed
                                    details = `Nitrogen Level: ${recommendations.recommendation_details?.[key]?.nitrogen_level || 'N/A'}`;
                                }

                                return (
                                    <RecommendationItem
                                        key={key}
                                        title={title}
                                        description={value}
                                        priority={priority}
                                        status={`Risk Level: ${status.toUpperCase()}`}
                                        details={details}
                                    />
                                );
                            }
                        )}

                    {!loading && !error && !recs && (
                        <Text style={styles.emptyText}>
                            {directRecommendations === undefined || directRecommendations === null
                                ? 'No recommendations available.'
                                : Object.keys(directRecommendations || {}).length === 0
                                    ? 'Analysis complete. No critical recommendations at this time.'
                                    : 'No recommendations could be extracted.'}
                        </Text>
                    )}
                </View>
            )}
        </View>
    );
};

export default RecommendationsSystem;

const styles = StyleSheet.create({
    container: {
        marginHorizontal: 0,
        marginVertical: 0,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: '#f0f0f0',
        padding: 14,
        borderRadius: 8,
    },
    headerTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#0d9f5f',
    },
    badge: {
        backgroundColor: '#0d9f5f',
        borderRadius: 12,
        paddingHorizontal: 8,
        paddingVertical: 3,
        marginHorizontal: 8,
    },
    badgeText: {
        color: '#fff',
        fontSize: 12,
        fontWeight: 'bold',
    },
    chevron: {
        fontSize: 18,
        color: '#0d9f5f',
    },
    content: {
        marginTop: 8,
        backgroundColor: '#fafafa',
        padding: 8,
        borderRadius: 8,
    },
    center: {
        alignItems: 'center',
        paddingVertical: 16,
    },
    loadingText: {
        marginTop: 8,
        color: '#64748b',
    },
    errorText: {
        color: '#ef4444',
    },
    card: {
        backgroundColor: '#ffffff',
        borderRadius: 8,
        padding: 12,
        marginVertical: 6,
        elevation: 2,
    },
    cardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    cardTitle: {
        fontSize: 14,
        fontWeight: 'bold',
        color: '#0f172a',
        flex: 1,
    },
    priorityBadge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 12,
        marginLeft: 8,
    },
    priorityText: {
        fontSize: 10,
        fontWeight: 'bold',
        color: '#fff',
    },
    status: {
        fontSize: 12,
        color: '#64748b',
        marginTop: 4,
    },
    details: {
        fontSize: 11,
        color: '#475569',
        marginTop: 2,
    },
    description: {
        fontSize: 13,
        color: '#1e293b',
        marginTop: 6,
        lineHeight: 16,
    },
    emptyText: {
        textAlign: 'center',
        color: '#64748b',
        paddingVertical: 12,
    },
});
