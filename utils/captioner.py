"""
Image captioning utilities using Hugging Face transformers.
Handles model loading and caption generation.
"""

import os
from typing import Optional
from PIL import Image
import torch
from transformers import BlipProcessor, BlipForConditionalGeneration


class ImageCaptioner:
    """
    Handles image captioning using the Salesforce/blip-image-captioning-base model.
    Model downloads automatically on first run.
    """
    
    def __init__(self, model_name: str = "Salesforce/blip-image-captioning-base"):
        """
        Initialize the captioning model.
        
        Args:
            model_name: Hugging Face model identifier
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.processor = None
        self._load_model()
    
    def _load_model(self):
        """Load the pretrained model and processor."""
        try:
            print(f"Loading model: {self.model_name}")
            print(f"Using device: {self.device}")
            
            # Load processor
            print("Loading processor...")
            self.processor = BlipProcessor.from_pretrained(
                self.model_name,
                local_files_only=False
            )
            print("✓ Processor loaded")
            
            # Load model - FORCE USE OF SAFETENSORS
            print("Loading model into memory...")
            self.model = BlipForConditionalGeneration.from_pretrained(
                self.model_name,
                local_files_only=False,
                use_safetensors=True  # Force safetensors usage
            )
            print("✓ Model loaded into memory")
            
            # Move model to device
            print(f"Moving model to {self.device}...")
            self.model.to(self.device)
            self.model.eval()
            
            print("=" * 60)
            print("✓ MODEL READY!")
            print("=" * 60)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR DETAILS:\n{error_details}")
            raise RuntimeError(f"Failed to load model: {str(e)}\n\nFull traceback:\n{error_details}")
    
    def generate_caption(
        self, 
        image_path: str, 
        max_length: int = 50, 
        num_beams: int = 4
    ) -> Optional[str]:
        """
        Generate a caption for the given image.
        
        Args:
            image_path: Path to the input image
            max_length: Maximum length of generated caption
            num_beams: Number of beams for beam search
            
        Returns:
            Generated caption string or None if error occurs
        """
        try:
            # Load and preprocess image
            image = Image.open(image_path)
            
            # Convert to RGB if necessary
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Process image
            inputs = self.processor(image, return_tensors="pt").to(self.device)
            
            # Generate caption
            with torch.no_grad():
                output_ids = self.model.generate(
                    **inputs,
                    max_length=max_length,
                    num_beams=num_beams
                )
            
            # Decode caption
            caption = self.processor.decode(output_ids[0], skip_special_tokens=True)
            
            return caption.strip()
            
        except Exception as e:
            print(f"Error generating caption: {str(e)}")
            return None
    
    def batch_generate_captions(
        self, 
        image_paths: list, 
        max_length: int = 50, 
        num_beams: int = 4
    ) -> list:
        """
        Generate captions for multiple images.
        
        Args:
            image_paths: List of image file paths
            max_length: Maximum caption length
            num_beams: Number of beams for beam search
            
        Returns:
            List of generated captions
        """
        captions = []
        for img_path in image_paths:
            caption = self.generate_caption(img_path, max_length, num_beams)
            captions.append(caption if caption else "Unable to generate caption")
        return captions
