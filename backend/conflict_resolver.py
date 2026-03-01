"""
Contradiction Resolution System for Farmer Decision Support
Priority-based conflict resolution for agricultural advice
"""

class ConflictResolver:
    def __init__(self):
        # Priority hierarchy: 1 = highest, 4 = lowest
        self.priority_rules = {
            "water_stress": {
                "severe": 1,
                "moderate": 2,
                "mild": 3,
                "optimal": 4
            },
            "disease_risk": {
                "high": 1,
                "medium": 3,
                "low": 4
            },
            "pest_risk": {
                "high": 1,
                "medium": 3,
                "low": 4
            },
            "nutrient_stress": {
                "high": 2,
                "moderate": 3,
                "low": 4
            }
        }
        
        # Stage-specific priority overrides
        self.stage_priorities = {
            "vegetative": ["disease_risk", "pest_risk", "water_stress", "nutrient_stress"],
            "reproductive": ["water_stress", "disease_risk", "pest_risk", "nutrient_stress"],
            "ripening": ["disease_risk", "water_stress", "pest_risk", "nutrient_stress"]
        }
        
        # Legume crops (self-nitrogen fixing)
        self.legume_crops = ["lentils", "bean", "pigeon_pea", "chickpea"]
    
    def get_priority(self, feature, level):
        """Get priority score for a feature level"""
        feature_key = self._normalize_feature_name(feature)
        level_key = self._normalize_level(level)
        
        if feature_key in self.priority_rules and level_key in self.priority_rules[feature_key]:
            return self.priority_rules[feature_key][level_key]
        return 4  # Default lowest priority
    
    def resolve_conflicts(self, plot_data, crop_doc, stage, recommendations):
        """
        Resolve contradictions between recommendations
        Returns: final_advice, conflicts_resolved
        """
        crop_type = plot_data.get("current_crop", "").lower()
        features_data = plot_data.get("features_data", {})
        
        # Extract all active recommendations with their priorities
        active_issues = self._collect_active_issues(features_data, crop_type, stage)
        
        if len(active_issues) <= 1:
            # No conflicts to resolve
            return recommendations, []
        
        # Check for specific conflicts
        conflicts = self._detect_conflicts(active_issues, crop_type, stage)
        
        if not conflicts:
            return recommendations, []
        
        # Resolve each conflict
        resolved_advice = self._apply_resolution_rules(
            recommendations.copy(), 
            conflicts, 
            crop_type, 
            stage, 
            features_data
        )
        
        return resolved_advice, conflicts
    
    def _collect_active_issues(self, features_data, crop_type, stage):
        """Collect all active issues with their priority scores"""
        issues = []
        
        # Water stress
        water_data = features_data.get("water_stress", {})
        if water_data and "stress" in water_data:
            issues.append({
                "feature": "water_stress",
                "level": water_data["stress"],
                "priority": self.get_priority("water_stress", water_data["stress"]),
                "value": water_data.get("score", 0)
            })
        
        # Disease risk
        disease_data = features_data.get("disease_detection", {})
        if disease_data and "risk_level" in disease_data:
            issues.append({
                "feature": "disease_risk",
                "level": disease_data["risk_level"],
                "priority": self.get_priority("disease_risk", disease_data["risk_level"]),
                "value": disease_data.get("disease_prob", 0)
            })
        
        # Pest risk
        pest_data = features_data.get("pest_risk", {})
        if pest_data and "risk_level" in pest_data:
            issues.append({
                "feature": "pest_risk",
                "level": pest_data["risk_level"],
                "priority": self.get_priority("pest_risk", pest_data["risk_level"]),
                "value": pest_data.get("confidence", 0)
            })
        
        # Nutrient stress
        nutrient_data = features_data.get("nutrient_deficiency", {})
        if nutrient_data:
            overall_stress = self._determine_overall_nutrient_stress(nutrient_data)
            if overall_stress != "optimal":
                issues.append({
                    "feature": "nutrient_stress",
                    "level": overall_stress,
                    "priority": self.get_priority("nutrient_stress", overall_stress),
                    "value": 0
                })
        
        # Sort by priority (highest first)
        issues.sort(key=lambda x: x["priority"])
        return issues
    
    def _detect_conflicts(self, active_issues, crop_type, stage):
        """Detect contradictions between issues"""
        conflicts = []
        
        # If we have both high water stress and high disease risk
        water_issue = next((i for i in active_issues if i["feature"] == "water_stress" 
                          and i["level"] in ["severe", "moderate"]), None)
        disease_issue = next((i for i in active_issues if i["feature"] == "disease_risk" 
                            and i["level"] == "high"), None)
        
        if water_issue and disease_issue:
            conflicts.append({
                "type": "water_vs_disease",
                "priority_issue": water_issue if water_issue["priority"] < disease_issue["priority"] else disease_issue,
                "secondary_issue": disease_issue if water_issue["priority"] < disease_issue["priority"] else water_issue,
                "stage": stage
            })
        
        # Nitrogen vs disease conflict
        nitrogen_level = self._get_nitrogen_level(crop_type)
        if nitrogen_level and disease_issue and nitrogen_level in ["high_deficiency", "moderate_deficiency"]:
            conflicts.append({
                "type": "nitrogen_vs_disease",
                "priority_issue": disease_issue,  # Disease has priority over nitrogen
                "secondary_issue": {"feature": "nitrogen", "level": nitrogen_level},
                "stage": stage
            })
        
        # Stage vs intervention conflict (e.g., nutrient application during ripening)
        nutrient_issue = next((i for i in active_issues if i["feature"] == "nutrient_stress" 
                             and i["level"] in ["high", "moderate"]), None)
        if nutrient_issue and stage == "ripening":
            conflicts.append({
                "type": "stage_vs_nutrient",
                "priority_issue": {"feature": "stage", "level": "ripening", "priority": 2},
                "secondary_issue": nutrient_issue,
                "stage": stage
            })
        
        # Legume nitrogen conflict
        if crop_type in self.legume_crops:
            if nitrogen_level and nitrogen_level in ["high_deficiency", "moderate_deficiency"]:
                conflicts.append({
                    "type": "legume_nitrogen",
                    "priority_issue": {"feature": "legume_biology", "level": "nitrogen_fixing", "priority": 2},
                    "secondary_issue": {"feature": "nitrogen", "level": nitrogen_level},
                    "crop": crop_type
                })
        
        return conflicts
    
    def _apply_resolution_rules(self, recommendations, conflicts, crop_type, stage, features_data):
        """Apply resolution rules to generate coherent advice"""
        
        for conflict in conflicts:
            if conflict["type"] == "water_vs_disease":
                # Water stress (severe) vs Disease risk (high)
                if conflict["priority_issue"]["feature"] == "water_stress":
                    # Water is priority - but add disease constraint
                    water_rec = recommendations.get("water_stress", "")
                    disease_rec = recommendations.get("disease_detection", "")
                    
                    # Replace with integrated advice
                    recommendations["water_stress"] = (
                        f"🚨 IRRIGATION URGENTLY NEEDED: Severe water stress detected.\n\n"
                        f"**Primary Action:** Irrigate immediately to prevent crop damage.\n"
                        f"**Important Constraint:** Use furrow irrigation or drip system to avoid wetting leaves, "
                        f"as disease risk is high. Irrigate in early morning to allow foliage to dry quickly.\n\n"
                        f"*Based on: Water stress score {features_data.get('water_stress', {}).get('score', 0)}/100, "
                        f"Disease probability {features_data.get('disease_detection', {}).get('disease_prob', 0)*100:.0f}%*"
                    )
                    
                    # Modify disease advice to acknowledge irrigation
                    if "disease_detection" in recommendations:
                        recommendations["disease_detection"] = (
                            f"⚠️ HIGH DISEASE RISK: Conditions favor disease spread.\n\n"
                            f"**Important:** Irrigation is required due to water stress. "
                            f"Apply fungicide only if symptoms appear, and avoid overhead irrigation.\n"
                            f"Monitor field daily for disease progression."
                        )
                
            elif conflict["type"] == "nitrogen_vs_disease":
                # Nitrogen deficiency vs Disease risk
                nitrogen_rec = recommendations.get("nutrient_deficiency", "")
                
                # Create integrated nitrogen advice
                recommendations["nutrient_deficiency"] = (
                    f"⚠️ NUTRIENT-DISEASE TRADEOFF: Nitrogen deficiency detected with high disease risk.\n\n"
                    f"**Recommendation:** Avoid heavy nitrogen application now as it may worsen disease.\n"
                    f"**Alternative:** If correction is urgent, apply small split dose after implementing disease control.\n"
                    f"**Priority:** Disease management first, then nutrient correction.\n\n"
                    f"*High disease risk takes precedence over nutrient correction*"
                )
                
            elif conflict["type"] == "stage_vs_nutrient":
                # Nutrient need during ripening stage
                if "nutrient_deficiency" in recommendations:
                    recommendations["nutrient_deficiency"] = (
                        f"🌾 RIPENING STAGE LIMITATION: Nutrient stress detected.\n\n"
                        f"**Important:** At ripening stage, nutrient application has limited benefit and may delay maturity.\n"
                        f"**Action:** Focus on preventing further stress rather than correction.\n"
                        f"**Exception:** Only apply foliar micronutrients if deficiency is severe and yield impact is expected.\n\n"
                        f"*Crop stage: {stage.upper()}*"
                    )
                
            elif conflict["type"] == "legume_nitrogen":
                # Legume crop with nitrogen deficiency
                crop_name = crop_type.replace("_", " ").title()
                
                # Replace general nutrient advice with legume-specific advice
                if "nutrient_deficiency" in recommendations:
                    recommendations["nutrient_deficiency"] = (
                        f"🌱 LEGUME-SPECIFIC NITROGEN ADVICE: {crop_name}\n\n"
                        f"**Biological Fact:** {crop_name} fixes its own nitrogen through root nodules.\n"
                        f"**Recommendation:** Do NOT apply heavy nitrogen fertilizer.\n"
                        f"**Alternative Actions:**\n"
                        f"1. Check root nodulation and soil moisture\n"
                        f"2. Improve phosphorus availability to support nitrogen fixation\n"
                        f"3. Apply foliar micronutrients if deficiency symptoms persist\n\n"
                        f"*Legume crops require different nitrogen management than cereals*"
                    )
        
        return recommendations
    
    def _normalize_feature_name(self, feature):
        """Normalize feature names to match priority rules"""
        mapping = {
            "disease_detection": "disease_risk",
            "pest_risk": "pest_risk",
            "water_stress": "water_stress",
            "nutrient_deficiency": "nutrient_stress"
        }
        return mapping.get(feature, feature)
    
    def _normalize_level(self, level):
        """Normalize risk levels"""
        if not level:
            return "optimal"
        level_lower = level.lower()
        
        # Map various level names to standard ones
        if "severe" in level_lower:
            return "severe"
        elif "moderate" in level_lower or "medium" in level_lower:
            return "moderate"
        elif "mild" in level_lower or "low" in level_lower:
            return "mild"
        elif "optimal" in level_lower or "adequate" in level_lower:
            return "optimal"
        elif "high" in level_lower:
            return "high"
        return "optimal"
    
    def _determine_overall_nutrient_stress(self, nutrient_data):
        """Determine overall nutrient stress level from individual nutrients"""
        levels = []
        for nutrient, level in nutrient_data.items():
            if nutrient != "timestamp" and level != "insufficient_data":
                levels.append(level)
        
        if any("high" in str(l).lower() for l in levels):
            return "high"
        elif any("moderate" in str(l).lower() or "possible" in str(l).lower() for l in levels):
            return "moderate"
        elif any("low" in str(l).lower() for l in levels):
            return "low"
        return "optimal"
    
    def _get_nitrogen_level(self, crop_type):
        """Helper to extract nitrogen level from crop data"""
        # This would come from your actual data structure
        # For now, returning None - will be implemented in app.py
        return None

    def resolve_temporal_conflicts(self, features_data, crop_stage, last_updated):
        """Resolve conflicts based on data age and urgency"""
        days_since_update = self._calculate_days_since_update(last_updated)
        
        # If data is more than 5 days old, be more conservative with urgent actions
        if days_since_update > 5:
            return {
                "water_stress": {
                    "severe": "conservative",
                    "moderate": "conservative"
                },
                "disease_risk": {
                    "high": "verify_first"
                }
            }
        return {}

    def _calculate_days_since_update(self, last_updated):
        """Calculate days since last update"""
        try:
            from datetime import datetime
            update_date = datetime.strptime(last_updated, "%Y-%m-%d")
            current_date = datetime.now()
            return (current_date - update_date).days
        except:
            return 0

# Singleton instance
resolver = ConflictResolver()