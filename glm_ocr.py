from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig
import torch
import os
import gc
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GLMOCRProcessor:
    """Reusable OCR processor using GLM-OCR model"""
    
    def __init__(
        self,
        model_path: str = "zai-org/GLM-OCR",
        cache_dir: str = "./model_folder",
        use_int8: bool = True
    ):
        """
        Initialize the OCR processor
        
        Args:
            model_path: HuggingFace model path
            cache_dir: Directory to cache the model
            use_int8: Whether to use int8 quantization (saves memory)
        """
        self.model_path = model_path
        self.cache_dir = cache_dir
        self.use_int8 = use_int8
        self.processor = None
        self.model = None
        self.is_loaded = False
    
    def load_model(self) -> bool:
        """
        Load the OCR model and processor
        
        Returns:
            True if successful, False otherwise
        """
        if self.is_loaded:
            logger.info("OCR model already loaded")
            return True
        
        try:
            logger.info("Loading GLM-OCR model with int8 quantization...")
            
            # Load processor
            self.processor = AutoProcessor.from_pretrained(
                self.model_path,
                cache_dir=self.cache_dir
            )
            
            # Configure quantization
            quantization_config = None
            if self.use_int8:
                try:
                    quantization_config = BitsAndBytesConfig(
                        load_in_8bit=True,
                        llm_int8_threshold=6.0
                    )
                except Exception as e:
                    logger.warning(f"Could not configure int8 quantization: {e}")
                    logger.warning("Loading model without quantization (will use more memory)")
                    quantization_config = None
            
            # Load model
            self.model = AutoModelForImageTextToText.from_pretrained(
                pretrained_model_name_or_path=self.model_path,
                quantization_config=quantization_config,
                device_map="auto",
                cache_dir=self.cache_dir
            )
            
            self.is_loaded = True
            logger.info("GLM-OCR model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load OCR model: {e}")
            return False
    
    def process_image(
        self,
        image_path: str,
        prompt: str = "Text Recognition:",
        max_new_tokens: int = 32000
    ) -> str:
        """
        Process a single image to extract text
        
        Args:
            image_path: Path to the image file
            prompt: Prompt text for OCR (default: "Text Recognition:")
            max_new_tokens: Maximum tokens to generate
        
        Returns:
            Extracted text from the image
        """
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        logger.info(f"Processing image: {Path(image_path).name}")
        
        # Prepare messages
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "url": image_path},
                    {"type": "text", "text": prompt}
                ],
            }
        ]
        
        # Process image
        inputs = self.processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        ).to(self.model.device)
        inputs.pop("token_type_ids", None)
        
        # Generate OCR output
        generated_ids = self.model.generate(**inputs, max_new_tokens=max_new_tokens)
        output_text = self.processor.decode(
            generated_ids[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=False
        )
        
        # Clear memory
        del inputs
        del generated_ids
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        
        logger.info(f"OCR completed for: {Path(image_path).name}")
        return output_text
    
    def process_and_save(
        self,
        image_path: str,
        output_folder: str,
        prompt: str = "Text Recognition:"
    ) -> Tuple[str, str]:
        """
        Process image and save OCR result to file
        
        Args:
            image_path: Path to the image file
            output_folder: Folder to save OCR results
            prompt: Prompt text for OCR
        
        Returns:
            Tuple of (extracted_text, output_file_path)
        """
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Process image
        output_text = self.process_image(image_path, prompt)
        
        # Create output filename
        image_name = Path(image_path).stem
        output_filename = f"ocr_{image_name}.txt"
        output_path = os.path.join(output_folder, output_filename)
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"OCR Result for: {Path(image_path).name}\n")
            f.write(f"Source: {image_path}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(output_text + "\n")
        
        logger.info(f"Saved OCR result to: {output_filename}")
        return output_text, output_path
    
    def unload_model(self):
        """Unload the model to free memory"""
        if self.is_loaded:
            logger.info("Unloading OCR model...")
            del self.model
            del self.processor
            self.model = None
            self.processor = None
            self.is_loaded = False
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
            
            logger.info("OCR model unloaded")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        self.unload_model()


# Standalone script functionality (backward compatibility)
def main():
    """Run OCR on images from file_list.txt"""
    MODEL_PATH = "zai-org/GLM-OCR"
    temp_folder = "ocr_result"
    
    # Read image paths from file_list.txt
    file_list_path = os.path.join("temp", "file_list.txt")
    
    if not os.path.exists(file_list_path):
        print(f"Error: {file_list_path} not found!")
        print("Please run get_files.py first to generate the file list.")
        return
    
    # Read all file paths and filter for images
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    image_paths = []
    
    with open(file_list_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if Path(line).suffix.lower() in image_extensions:
                if os.path.exists(line):
                    image_paths.append(line)
    
    print(f"Found {len(image_paths)} image(s) to process")
    
    if len(image_paths) == 0:
        print("No valid images found in file list!")
        return
    
    # Create OCR processor
    ocr = GLMOCRProcessor(model_path=MODEL_PATH)
    
    # Load model
    if not ocr.load_model():
        print("Failed to load OCR model!")
        return
    
    # Create output folder
    os.makedirs(temp_folder, exist_ok=True)
    
    # Process each image
    for idx, image_path in enumerate(image_paths, 1):
        print(f"\nProcessing image {idx}/{len(image_paths)}: {Path(image_path).name}")
        
        try:
            text, output_path = ocr.process_and_save(image_path, temp_folder)
            print(f"  ✓ Saved to: {Path(output_path).name}")
            print(f"  ✓ Extracted {len(text)} characters")
        except Exception as e:
            print(f"  ✗ Error processing {Path(image_path).name}: {e}")
    
    print(f"\n{'='*80}")
    print(f"Processed {len(image_paths)} image(s)")
    print(f"Output files saved in: {temp_folder}/")
    
    # Cleanup
    ocr.unload_model()


if __name__ == "__main__":
    main()
