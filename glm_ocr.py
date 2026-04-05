import os
import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Any, Dict
import logging
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GLMOCRProcessor:
    """Reusable OCR processor using a llama.cpp OpenAI-compatible backend"""
    
    def __init__(
        self,
        model_path: str = "zai-org/GLM-OCR",
        cache_dir: str = "./model_folder",
        use_int8: bool = True,
        llm_base_url: str = "http://localhost:8080"
    ):
        """
        Initialize the OCR processor
        
        Args:
            model_path: Model name/path understood by llama.cpp server
            cache_dir: Kept for backward compatibility (unused by llama.cpp backend)
            use_int8: Kept for backward compatibility (unused by llama.cpp backend)
            llm_base_url: Base URL for llama.cpp server
        """
        self.model_path = model_path
        self.cache_dir = cache_dir
        self.use_int8 = use_int8
        self.llm_base_url = llm_base_url.rstrip("/")
        self.api_uri_v1 = f"{self.llm_base_url}/v1"
        self._model_load_endpoint = f"{self.llm_base_url}/models/load"
        self._model_unload_endpoint = f"{self.llm_base_url}/models/unload"
        self._timeout = 120
        self._requests_session: Optional[requests.Session] = None
        self.currently_loaded_model: Optional[str] = None
        self._effective_model_name: str = model_path
        self.is_loaded = False

    def _get_session(self) -> requests.Session:
        if self._requests_session is None:
            self._requests_session = requests.Session()
        return self._requests_session

    def _check_server_status(self) -> bool:
        try:
            response = self._get_session().get(f"{self.llm_base_url}/health", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            # Some llama.cpp wrappers do not expose /health; try /v1/models as fallback.
            try:
                response = self._get_session().get(f"{self.api_uri_v1}/models", timeout=8)
                return response.status_code == 200
            except requests.RequestException:
                return False

    def _try_load_remote_model(self) -> bool:
        """Try explicit model load endpoint; succeed silently when endpoint is unavailable."""
        payload = {"model": self.model_path}
        try:
            response = self._get_session().post(self._model_load_endpoint, json=payload, timeout=self._timeout)
            if response.status_code == 200:
                return True
            logger.warning(
                "Model load endpoint returned status %s: %s",
                response.status_code,
                response.text,
            )
            return False
        except requests.RequestException:
            # Endpoint may not exist in all llama.cpp distributions; continue if chat endpoint works.
            logger.info("Model load endpoint not available; assuming model is managed externally")
            return True

    def _fetch_available_models(self) -> list[str]:
        """Read model ids from OpenAI-compatible /v1/models response."""
        try:
            response = self._get_session().get(f"{self.api_uri_v1}/models", timeout=8)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        discovered: list[str] = []

        for item in data.get("data", []):
            model_id = item.get("id")
            if isinstance(model_id, str) and model_id.strip():
                discovered.append(model_id.strip())

        for item in data.get("models", []):
            if isinstance(item, dict):
                for key in ("model", "name"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        discovered.append(value.strip())

        # Preserve order while removing duplicates.
        return list(dict.fromkeys(discovered))

    def _resolve_effective_model_name(self, available_models: list[str]) -> str:
        """Pick a model id that actually exists in the running server."""
        if not available_models:
            return self.model_path

        configured = self.model_path.strip()
        configured_lower = configured.lower()
        configured_name = Path(configured).name.strip().lower()

        for candidate in available_models:
            if candidate == configured:
                return candidate

        for candidate in available_models:
            if candidate.lower() == configured_lower:
                return candidate

        for candidate in available_models:
            if Path(candidate).name.strip().lower() == configured_name:
                return candidate

        logger.warning(
            "Configured OCR model '%s' not found on server. Falling back to '%s'.",
            self.model_path,
            available_models[0],
        )
        return available_models[0]

    @staticmethod
    def _extract_text_from_response(data: Dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            return ""

        message = choices[0].get("message") or {}
        content = message.get("content", "")

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            chunks = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        chunks.append(str(text))
                elif item:
                    chunks.append(str(item))
            return "\n".join(chunks)

        return str(content) if content is not None else ""

    @staticmethod
    def _to_data_url(image_path: str) -> str:
        ext = Path(image_path).suffix.lower().lstrip(".")
        mime_map = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "bmp": "image/bmp",
            "tiff": "image/tiff",
            "webp": "image/webp",
        }
        mime_type = mime_map.get(ext, "image/png")
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime_type};base64,{b64}"
    
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
            logger.info("Initializing llama.cpp OCR backend...")

            if not self._check_server_status():
                logger.error("llama.cpp server is not reachable at %s", self.llm_base_url)
                return False

            # Best-effort load; some deployments load models externally.
            self._try_load_remote_model()

            available_models = self._fetch_available_models()
            if not available_models:
                logger.error(
                    "No models are available on llama.cpp server. "
                    "Start server with a model (and mmproj for vision models)."
                )
                return False

            self._effective_model_name = self._resolve_effective_model_name(available_models)
            self.currently_loaded_model = self._effective_model_name
            self.is_loaded = True
            logger.info("llama.cpp OCR backend initialized successfully")
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

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        logger.info(f"Processing image: {Path(image_path).name}")

        image_data_url = self._to_data_url(image_path)
        payload = {
            "model": self._effective_model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                    ],
                }
            ],
            "stream": False,
            "max_tokens": int(max_new_tokens),
            "temperature": 0.0,
        }

        try:
            response = self._get_session().post(
                f"{self.api_uri_v1}/chat/completions",
                json=payload,
                timeout=self._timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"llama.cpp OCR request failed: {e}") from e

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response from llama.cpp: {response.text[:500]}") from e

        output_text = self._extract_text_from_response(data)
        if not output_text:
            output_text = ""
        
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

            # Best effort unload; many llama.cpp setups manage model lifecycle externally.
            if self.currently_loaded_model:
                payload = {"model": self.currently_loaded_model}
                try:
                    self._get_session().post(self._model_unload_endpoint, json=payload, timeout=30)
                except requests.RequestException:
                    logger.info("Model unload endpoint not available; skipping explicit unload")
                except Exception:
                    # During interpreter teardown, requests internals can be partially unloaded.
                    logger.info("Model unload endpoint not available; skipping explicit unload")

            if self._requests_session is not None:
                self._requests_session.close()
                self._requests_session = None

            self.currently_loaded_model = None
            self.is_loaded = False

            logger.info("OCR model unloaded")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.unload_model()
        except Exception:
            # Avoid raising during interpreter shutdown.
            pass


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
