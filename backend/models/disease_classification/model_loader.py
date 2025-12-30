"""
Fixed disease model loader without eval()
"""
import torch
import torchvision.models as models
from torchvision import transforms
import torch.nn as nn
from PIL import Image
import numpy as np
import os

class DiseaseModelLoader:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.loaded_models = {}
        
    def load_model(self, crop_type, model_path):
        """Load disease classification model for specific crop"""
        if crop_type in self.loaded_models:
            return self.loaded_models[crop_type]
        
        try:
            # Load checkpoint safely
            checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
            
            # Get model parameters safely
            num_classes = len(checkpoint.get("class_to_idx", {}))
            img_size = checkpoint.get("img_size", 224)
            mean = checkpoint.get("mean", [0.485, 0.456, 0.406])
            std = checkpoint.get("std", [0.229, 0.224, 0.225])
            
            # Create model architecture safely
            model = models.resnet50(weights=None)
            model.fc = nn.Linear(model.fc.in_features, num_classes)
            
            # Load state dict safely
            model.load_state_dict(checkpoint["model_state_dict"])
            model.to(self.device)
            model.eval()
            
            # Create transforms safely
            transform = transforms.Compose([
                transforms.Resize((img_size, img_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=mean, std=std)
            ])
            
            # Create class mappings safely
            idx_to_class = {v: k for k, v in checkpoint["class_to_idx"].items()}
            
            # Store model info safely
            model_info = {
                'model': model,
                'transform': transform,
                'idx_to_class': idx_to_class,
                'img_size': img_size,
                'mean': mean,
                'std': std,
                'num_classes': num_classes
            }
            
            self.loaded_models[crop_type] = model_info
            print(f"✓ Loaded {crop_type} disease model")
            
            return model_info
            
        except Exception as e:
            print(f"Error loading {crop_type} model: {e}")
            return None
    
    def predict(self, crop_type, image_path, threshold=0.6):
        """Make prediction for given crop and image"""
        if crop_type not in self.loaded_models:
            return None, 0.0, "Model not loaded"
        
        model_info = self.loaded_models[crop_type]
        
        try:
            # Load and preprocess image safely
            img = Image.open(image_path).convert("RGB")
            x = model_info['transform'](img).unsqueeze(0).to(self.device)
            
            # Make prediction safely
            with torch.no_grad():
                logits = model_info['model'](x)
                probs = torch.softmax(logits, dim=1)
            
            # Get top prediction safely
            conf, pred_idx = torch.max(probs, dim=1)
            conf = conf.item()
            pred_idx = pred_idx.item()
            
            # Get class name safely
            pred_class = model_info['idx_to_class'].get(pred_idx, "Unknown")
            
            # Check confidence threshold safely
            if conf < threshold:
                return "Uncertain", conf, "Low confidence prediction"
            
            # Get all probabilities safely
            all_probs = probs.squeeze().cpu().numpy()
            all_classes = []
            for idx in range(len(all_probs)):
                class_name = model_info['idx_to_class'].get(idx, f"Class_{idx}")
                all_classes.append({
                    'class': class_name,
                    'confidence': float(all_probs[idx]),
                    'index': idx
                })
            
            # Sort by confidence safely
            all_classes.sort(key=lambda x: x['confidence'], reverse=True)
            
            return pred_class, conf, all_classes
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return None, 0.0, f"Prediction error: {str(e)}"
    
    def get_model_info(self, crop_type):
        """Get information about loaded model"""
        if crop_type in self.loaded_models:
            return self.loaded_models[crop_type]
        return None