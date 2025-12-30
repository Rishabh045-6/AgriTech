"""
Generate disease-specific advice and recommendations
"""
import random

class DiseaseAdviceGenerator:
    def __init__(self):
        self.advice_templates = self._initialize_advice_templates()
    
    def _initialize_advice_templates(self):
        """Initialize disease-specific advice templates"""
        return {
            # Chickpea diseases
            'Fusarium': {
                'title': 'Fusarium Wilt',
                'symptoms': [
                    'Yellowing and wilting of leaves starting from lower leaves',
                    'Brown discoloration in stem cross-section',
                    'Stunted growth and premature death'
                ],
                'recommendations': [
                    'Use resistant varieties like Pusa 372, Pusa 256',
                    'Apply Trichoderma viride or Pseudomonas fluorescens as seed treatment',
                    'Practice crop rotation with non-host crops (cereals)',
                    'Avoid waterlogging in fields',
                    'Remove and destroy infected plants'
                ],
                'chemical_control': [
                    'Seed treatment with Carbendazim @ 2g/kg seed',
                    'Soil drenching with Carbendazim @ 0.1%'
                ],
                'organic_control': [
                    'Neem cake application @ 250 kg/ha',
                    'Application of Trichoderma harzianum @ 2.5 kg/ha'
                ],
                'severity': 'High'
            },
            'Healthy': {
                'title': 'Healthy Plant',
                'symptoms': ['Vibrant green leaves', 'Normal growth pattern', 'No visible lesions'],
                'recommendations': [
                    'Continue good agricultural practices',
                    'Monitor regularly for early signs',
                    'Maintain proper irrigation schedule',
                    'Apply balanced fertilization'
                ],
                'chemical_control': ['No chemical treatment needed'],
                'organic_control': ['Continue organic practices if applicable'],
                'severity': 'None'
            },
            
            # Bean diseases
            'Angular_Leaf_Spot': {
                'title': 'Angular Leaf Spot',
                'symptoms': [
                    'Angular water-soaked spots on leaves',
                    'Spots limited by leaf veins',
                    'Yellow halos around spots'
                ],
                'recommendations': [
                    'Use disease-free seeds',
                    'Practice 3-year crop rotation',
                    'Remove crop debris after harvest',
                    'Avoid overhead irrigation'
                ],
                'severity': 'Medium'
            },
            'Bean_Rust': {
                'title': 'Bean Rust',
                'symptoms': [
                    'Small reddish-brown pustules on leaves',
                    'Pustules may appear on stems and pods',
                    'Premature leaf drop'
                ],
                'recommendations': [
                    'Plant resistant varieties',
                    'Apply sulfur-based fungicides',
                    'Space plants for good air circulation',
                    'Avoid working in wet fields'
                ],
                'severity': 'High'
            },
            
            # Lentil diseases
            'Ascochyta blight': {
                'title': 'Ascochyta Blight',
                'symptoms': [
                    'Brown lesions with concentric rings',
                    'Lesions on leaves, stems, and pods',
                    'Gray fungal growth in humid conditions'
                ],
                'recommendations': [
                    'Use certified disease-free seeds',
                    'Apply Chlorothalonil at early flowering',
                    'Practice 4-year crop rotation',
                    'Deep plowing to bury infected debris'
                ],
                'severity': 'High'
            },
            'Lentil Rust': {
                'title': 'Lentil Rust',
                'symptoms': [
                    'Orange to brown pustules on leaves',
                    'Pustules rupture releasing spores',
                    'Severe defoliation in advanced stages'
                ],
                'recommendations': [
                    'Early sowing to avoid peak rust period',
                    'Foliar spray of Propiconazole @ 0.1%',
                    'Remove volunteer lentil plants',
                    'Use tolerant varieties like L 4076'
                ],
                'severity': 'Medium'
            },
            
            # Maize diseases
            'Common_Rust': {
                'title': 'Common Rust of Maize',
                'symptoms': [
                    'Circular to elongated cinnamon-brown pustules',
                    'Pustules mostly on upper leaf surface',
                    'May cause yellowing and drying of leaves'
                ],
                'recommendations': [
                    'Plant resistant hybrids',
                    'Apply Mancozeb @ 0.25% at first appearance',
                    'Avoid excessive nitrogen application',
                    'Remove alternative hosts'
                ],
                'severity': 'Medium'
            },
            'Gray_Leaf_Spot': {
                'title': 'Gray Leaf Spot',
                'symptoms': [
                    'Rectangular gray to tan lesions',
                    'Lesions parallel to leaf veins',
                    'Severe infection causes complete blighting'
                ],
                'recommendations': [
                    'Use resistant hybrids',
                    'Practice crop rotation with soybean',
                    'Reduce plant density for better air movement',
                    'Apply Azoxystrobin at disease onset'
                ],
                'severity': 'High'
            },
            
            # Pigeon pea diseases
            'Leaf_Spot': {
                'title': 'Leaf Spot',
                'symptoms': [
                    'Circular brown spots with yellow halos',
                    'Spots may coalesce forming large necrotic areas',
                    'Premature leaf fall in severe cases'
                ],
                'recommendations': [
                    'Spray Mancozeb @ 0.25%',
                    'Remove and destroy infected leaves',
                    'Avoid dense planting',
                    'Use balanced fertilization'
                ],
                'severity': 'Low'
            },
            'Leaf_webber': {
                'title': 'Leaf Webber',
                'symptoms': [
                    'Leaves webbed together by larvae',
                    'Skeletonization of leaves',
                    'Reduced photosynthetic area'
                ],
                'recommendations': [
                    'Spray Chlorpyriphos @ 0.05%',
                    'Release Trichogramma parasites',
                    'Install pheromone traps @ 5/ha',
                    'Remove and destroy webbed leaves'
                ],
                'severity': 'Medium'
            },
            
            # Wheat diseases
            'Bacterial leaf blight': {
                'title': 'Bacterial Leaf Blight',
                'symptoms': [
                    'Water-soaked lesions turning yellow',
                    'Lesions with bacterial ooze in morning',
                    'Drying and bleaching of leaves'
                ],
                'recommendations': [
                    'Use resistant varieties like HD 2967',
                    'Avoid overhead irrigation',
                    'Spray Streptocycline @ 0.01%',
                    'Practice clean cultivation'
                ],
                'severity': 'Medium'
            },
            'Blast': {
                'title': 'Wheat Blast',
                'symptoms': [
                    'Bleached spikelets',
                    'Black lesions on rachis',
                    'Complete bleaching of heads'
                ],
                'recommendations': [
                    'Use tolerant varieties',
                    'Avoid late sowing',
                    'Apply Tricyclazole @ 0.1%',
                    'Destroy infected crop residue'
                ],
                'severity': 'High'
            },
            
            # Rice diseases
            'Brown_Rust': {
                'title': 'Brown Rust',
                'symptoms': [
                    'Small brown pustules on leaves',
                    'Pustules arranged in linear patterns',
                    'Yellowing of leaves around pustules'
                ],
                'recommendations': [
                    'Use resistant varieties like PR 114',
                    'Spray Propiconazole @ 0.1%',
                    'Avoid excess nitrogen',
                    'Drain field periodically'
                ],
                'severity': 'Medium'
            },
            'Yellow_Rust': {
                'title': 'Yellow Rust',
                'symptoms': [
                    'Yellow-orange pustules in stripes',
                    'Pustules contain yellow powder',
                    'Severe infection causes complete drying'
                ],
                'recommendations': [
                    'Plant resistant varieties',
                    'Spray Tebuconazole @ 0.1%',
                    'Early sowing to avoid infection',
                    'Remove volunteer plants'
                ],
                'severity': 'High'
            },
            'Powdery_Mildew': {
                'title': 'Powdery Mildew',
                'symptoms': [
                    'White powdery growth on leaves',
                    'Growth mostly on upper surface',
                    'Leaves may curl and dry'
                ],
                'recommendations': [
                    'Spray Wettable sulfur @ 0.2%',
                    'Improve air circulation',
                    'Avoid dense planting',
                    'Use resistant varieties'
                ],
                'severity': 'Low'
            }
        }
    
    def get_advice(self, crop_type, disease_name):
        """Get detailed advice for specific disease"""
        # Try exact match first
        if disease_name in self.advice_templates:
            return self.advice_templates[disease_name]
        
        # Try partial match
        for key, advice in self.advice_templates.items():
            if key.lower() in disease_name.lower() or disease_name.lower() in key.lower():
                return advice
        
        # Default generic advice
        return self._get_generic_advice(disease_name)
    
    def _get_generic_advice(self, disease_name):
        """Generate generic advice for unknown diseases"""
        return {
            'title': disease_name,
            'symptoms': ['Consult local agricultural expert for specific symptoms'],
            'recommendations': [
                'Isolate affected plants',
                'Consult local KVK (Krishi Vigyan Kendra)',
                'Take clear photos for expert consultation',
                'Maintain field sanitation'
            ],
            'chemical_control': ['Consult agricultural officer for appropriate fungicide'],
            'organic_control': ['Neem-based formulations may help', 'Improve soil health'],
            'severity': 'Unknown'
        }
    
    def get_preventive_measures(self, crop_type):
        """Get general preventive measures for crop"""
        general_measures = [
            'Use certified disease-free seeds',
            'Practice crop rotation',
            'Maintain proper plant spacing',
            'Ensure balanced nutrition',
            'Monitor fields regularly (at least weekly)',
            'Control weeds that may harbor diseases',
            'Avoid working in fields when plants are wet',
            'Clean equipment between fields'
        ]
        
        crop_specific = {
            'rice': [
                'Maintain proper water management',
                'Use resistant/tolerant varieties',
                'Apply recommended fungicides preventively'
            ],
            'wheat': [
                'Avoid late sowing',
                'Use seed treatment with fungicides',
                'Destroy crop residues after harvest'
            ],
            'maize': [
                'Avoid continuous maize cultivation',
                'Use resistant hybrids',
                'Control insect vectors'
            ],
            'chickpea': [
                'Deep summer plowing',
                'Avoid waterlogging',
                'Use bio-control agents'
            ]
        }
        
        measures = general_measures + crop_specific.get(crop_type, [])
        return measures
    
    def generate_report(self, crop_type, disease_name, confidence, image_info=None):
        """Generate comprehensive disease report"""
        advice = self.get_advice(crop_type, disease_name)
        
        report = {
            'crop': crop_type,
            'disease': disease_name,
            'confidence': confidence,
            'diagnosis': advice['title'],
            'severity': advice.get('severity', 'Unknown'),
            'symptoms': advice.get('symptoms', []),
            'recommendations': advice.get('recommendations', []),
            'chemical_control': advice.get('chemical_control', []),
            'organic_control': advice.get('organic_control', []),
            'preventive_measures': self.get_preventive_measures(crop_type),
            'image_info': image_info
        }
        
        return report