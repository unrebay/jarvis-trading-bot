"""
Image Handler Module - Processes trading images with vision analysis

Handles:
- Image upload and validation
- Vision analysis with Claude
- Chart annotation generation
- Image annotation entity creation
- Supabase storage and embedding
"""

import base64
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from io import BytesIO

from PIL import Image
import requests

from .claude_client import ClaudeClient


@dataclass
class ImageMetadata:
    """Metadata about an uploaded image"""
    file_name: str
    file_size_kb: float
    dimensions: Dict[str, int]  # width, height
    format: str
    file_hash: str
    upload_time: str


@dataclass
class VisionAnalysis:
    """Result of vision analysis"""
    analysis_type: str  # "chart", "diagram", "concept_map"
    confidence: float
    detected_patterns: List[str]
    key_levels: List[Dict[str, Any]]
    annotations: List[Dict[str, Any]]
    educational_value: str
    learning_points: List[str]
    raw_response: str


class ImageHandler:
    """
    Handles image processing with vision analysis

    Workflow:
    1. Receive image (URL or upload)
    2. Validate and optimize
    3. Extract metadata
    4. Analyze with Claude vision
    5. Generate annotations
    6. Create image_annotation entity
    7. Store in Supabase
    """

    def __init__(self, claude_client: ClaudeClient, supabase_client=None):
        """
        Initialize image handler

        Args:
            claude_client: ClaudeClient instance for vision API calls
            supabase_client: Supabase client for storage
        """
        self.claude = claude_client
        self.supabase = supabase_client
        self.image_dir = Path("kb/media/images/processed")
        self.image_dir.mkdir(parents=True, exist_ok=True)

    def process_image_url(self, image_url: str, context: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Process image from URL

        Args:
            image_url: URL to image
            context: Optional context about image (title, description, etc)

        Returns:
            Dict with analysis results and entity data
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            image_data = response.content

            # Process and analyze
            return self._process_image_data(
                image_data,
                image_url=image_url,
                context=context
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to download image: {str(e)}"
            }

    def process_image_upload(self, file_path: str, context: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Process uploaded image file

        Args:
            file_path: Local path to image file
            context: Optional context

        Returns:
            Dict with analysis results
        """
        try:
            with open(file_path, 'rb') as f:
                image_data = f.read()

            return self._process_image_data(
                image_data,
                file_path=file_path,
                context=context
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to process image: {str(e)}"
            }

    def _process_image_data(
        self,
        image_data: bytes,
        image_url: str = None,
        file_path: str = None,
        context: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Internal: Process image data

        Args:
            image_data: Image bytes
            image_url: Optional original URL
            file_path: Optional original file path
            context: Optional context

        Returns:
            Analysis results and entity data
        """
        context = context or {}

        # Validate and get metadata
        metadata_result = self._validate_and_optimize_image(image_data)
        if not metadata_result.get("success"):
            return metadata_result

        metadata = metadata_result["metadata"]
        optimized_image = metadata_result["image_data"]

        # Analyze with vision
        analysis_result = self._analyze_with_vision(optimized_image, context)
        if not analysis_result.get("success"):
            return analysis_result

        analysis = analysis_result["analysis"]

        # Store image
        image_id = self._store_image(optimized_image, metadata)

        # Create entity
        entity = self._create_image_annotation_entity(
            image_id,
            metadata,
            analysis,
            context
        )

        # Store in Supabase
        if self.supabase:
            entity_id = self._store_entity(entity)
            entity["id"] = entity_id

        return {
            "success": True,
            "image_id": image_id,
            "metadata": asdict(metadata),
            "analysis": asdict(analysis) if isinstance(analysis, VisionAnalysis) else analysis,
            "entity": entity
        }

    def _validate_and_optimize_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        Validate image and return metadata

        Args:
            image_data: Image bytes

        Returns:
            Dict with success flag, metadata, and optimized image
        """
        try:
            # Open image
            image = Image.open(BytesIO(image_data))

            # Validate
            if image.size[0] < 400:  # min width
                return {
                    "success": False,
                    "error": f"Image too small: {image.size[0]}x{image.size[1]} (min 400px width)"
                }

            # Get metadata
            file_name = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            file_hash = hashlib.sha256(image_data).hexdigest()[:12]
            file_size_kb = len(image_data) / 1024

            metadata = ImageMetadata(
                file_name=f"{file_name}_{file_hash}",
                file_size_kb=round(file_size_kb, 2),
                dimensions={"width": image.size[0], "height": image.size[1]},
                format=image.format or "unknown",
                file_hash=file_hash,
                upload_time=datetime.now().isoformat()
            )

            # Optimize if needed
            optimized = image_data
            if len(image_data) > 10 * 1024 * 1024:  # > 10MB
                # Resize and compress
                if image.size[0] > 2400:
                    ratio = 2400 / image.size[0]
                    new_size = (2400, int(image.size[1] * ratio))
                    image = image.resize(new_size, Image.Resampling.LANCZOS)

                # Save compressed
                buffer = BytesIO()
                image.save(buffer, format="JPEG", quality=85, optimize=True)
                optimized = buffer.getvalue()

            return {
                "success": True,
                "metadata": metadata,
                "image_data": optimized
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Image validation failed: {str(e)}"
            }

    def _analyze_with_vision(
        self,
        image_data: bytes,
        context: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Analyze image with Claude vision

        Args:
            image_data: Image bytes
            context: Context about image

        Returns:
            Dict with analysis results
        """
        try:
            # Encode image
            image_base64 = base64.standard_b64encode(image_data).decode("utf-8")

            # Determine image type
            image_type = "image/jpeg"
            try:
                img = Image.open(BytesIO(image_data))
                if img.format == "PNG":
                    image_type = "image/png"
                elif img.format == "GIF":
                    image_type = "image/gif"
            except:
                pass

            # Build vision request
            system_prompt = self._load_vision_prompt("image_analyzer.md")

            user_message = f"""Analyze this trading chart/diagram image.

Context:
- Title: {context.get('title', 'Unknown')}
- Description: {context.get('description', 'Not provided')}

Provide analysis in the following JSON structure:
{{
  "type": "chart|diagram|concept_map",
  "summary": "1-2 sentence summary",
  "analysis": {{
    "instrument": "if chart, what symbol",
    "timeframe": "if chart, what timeframe",
    "visual_elements": ["element1", "element2"],
    "patterns_detected": ["pattern_1", "pattern_2"],
    "key_levels": [
      {{"level": 1.0850, "type": "support|resistance", "strength": "strong|medium|weak"}}
    ],
    "confidence_score": 0.85
  }},
  "learning_points": ["point1", "point2"],
  "related_patterns": ["pattern_id_1"],
  "related_lessons": ["lesson_id_1"]
}}"""

            # Call Claude with vision
            response = self.claude.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": user_message
                            }
                        ]
                    }
                ]
            )

            # Parse response
            analysis_text = response.content[0].text

            # Extract JSON
            try:
                json_start = analysis_text.find('{')
                json_end = analysis_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    analysis_json = json.loads(analysis_text[json_start:json_end])
                else:
                    analysis_json = {}
            except json.JSONDecodeError:
                analysis_json = {}

            analysis = VisionAnalysis(
                analysis_type=analysis_json.get("type", "unknown"),
                confidence=analysis_json.get("analysis", {}).get("confidence_score", 0.0),
                detected_patterns=analysis_json.get("analysis", {}).get("patterns_detected", []),
                key_levels=analysis_json.get("analysis", {}).get("key_levels", []),
                annotations=analysis_json.get("annotations", []),
                educational_value=analysis_json.get("analysis", {}).get("significance", ""),
                learning_points=analysis_json.get("learning_points", []),
                raw_response=analysis_text
            )

            return {
                "success": True,
                "analysis": analysis
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Vision analysis failed: {str(e)}"
            }

    def _store_image(self, image_data: bytes, metadata: ImageMetadata) -> str:
        """
        Store optimized image locally and to Supabase

        Args:
            image_data: Image bytes
            metadata: Image metadata

        Returns:
            Image ID for reference
        """
        # Local storage
        image_id = f"image_{metadata.file_hash}"
        local_path = self.image_dir / f"{metadata.file_name}.jpg"

        with open(local_path, 'wb') as f:
            f.write(image_data)

        # Supabase storage
        if self.supabase:
            try:
                self.supabase.storage.from_("knowledge-base").upload(
                    f"images/processed/{metadata.file_name}.jpg",
                    image_data
                )
            except Exception as e:
                print(f"Warning: Failed to upload to Supabase: {e}")

        return image_id

    def _create_image_annotation_entity(
        self,
        image_id: str,
        metadata: ImageMetadata,
        analysis: VisionAnalysis,
        context: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Create image_annotation entity

        Args:
            image_id: Image ID
            metadata: Image metadata
            analysis: Vision analysis results
            context: User context

        Returns:
            Entity dict
        """
        return {
            "id": image_id,
            "image_url": f"s3://jarvis-kb/images/{metadata.file_name}.jpg",
            "file_path": f"kb/media/images/processed/{metadata.file_name}",
            "title": context.get("title", "Trading Chart"),
            "description": context.get("description", f"Analysis: {analysis.analysis_type}"),
            "type": analysis.analysis_type,
            "content_type": f"image/{metadata.format.lower()}",
            "dimensions": metadata.dimensions,
            "file_size_kb": metadata.file_size_kb,
            "annotations": analysis.annotations,
            "text_annotations": [
                {"label": point, "text": point}
                for point in analysis.learning_points
            ],
            "related_patterns": analysis.detected_patterns,
            "related_lessons": context.get("related_lessons", []),
            "related_rules": context.get("related_rules", []),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": {
                "confidence": analysis.confidence,
                "analysis_type": analysis.analysis_type,
                "key_levels": analysis.key_levels,
                "raw_analysis": analysis.raw_response
            }
        }

    def _store_entity(self, entity: Dict[str, Any]) -> str:
        """
        Store image_annotation entity in Supabase

        Args:
            entity: Entity dict

        Returns:
            Entity ID
        """
        if not self.supabase:
            return entity.get("id", "unknown")

        try:
            result = self.supabase.table("image_annotations").insert(entity).execute()
            return entity["id"]
        except Exception as e:
            print(f"Warning: Failed to store entity: {e}")
            return entity.get("id", "unknown")

    def _load_vision_prompt(self, prompt_file: str) -> str:
        """
        Load vision analysis prompt from kb/prompts/

        Args:
            prompt_file: Prompt filename

        Returns:
            Prompt content
        """
        try:
            prompt_path = Path(f"kb/prompts/{prompt_file}")
            if prompt_path.exists():
                with open(prompt_path, 'r') as f:
                    return f.read()
        except:
            pass

        # Fallback to default
        return """You are an expert chart analyzer specialized in trading patterns and market structure."""
