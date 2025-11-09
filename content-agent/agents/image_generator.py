import replicate
import os
import json
from typing import List, Dict, Any, Optional
from agents.llm_wrappers import GeminiLLM, ZAILLM
import time

class ImageGenerator:
    def __init__(self):
        self.llm = self._get_llm()
        self.replicate_client = replicate.Client(api_token=os.getenv("REPLICATE_API_KEY"))
        self.model_name = os.getenv("REPLICATE_MODEL", "ideogram-ai/ideogram-v3-turbo")

    def _get_llm(self):
        if os.getenv("CORE_AGENT_TYPE") == "gemini":
            return GeminiLLM(api_key=os.getenv("GEMINI_API_KEY"))
        elif os.getenv("CORE_AGENT_TYPE") == "zai":
            return ZAILLM(api_key=os.getenv("ZAI_API_KEY"))
        else:
            raise ValueError("Unsupported CORE_AGENT_TYPE. Use 'gemini' or 'zai'.")

    def optimize_prompts_for_replicate(self, content_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize image prompts for Replicate's ideogram-v3-turbo model

        Args:
            content_plan: List of content plans with image concepts

        Returns:
            List of optimized prompts with detailed descriptions
        """
        prompts = []

        for i, content in enumerate(content_plan):
            image_concept = content.get('image_concept', '')
            caption = content.get('caption', '')
            content_type = content.get('content_type', 'general')

            prompt = f"""
            Create a detailed, optimized prompt for generating an image with ideogram-v3-turbo AI model.

            Content context:
            - Image concept: {image_concept}
            - Caption: {caption}
            - Content type: {content_type}

            Create a prompt that will generate a stunning, high-quality image suitable for social media.
            The prompt should include:

            1. Main subject and composition
            2. Art style (e.g., "modern minimalist", "vibrant illustration", "photorealistic")
            3. Color scheme and mood
            4. Lighting and atmosphere
            5. Specific details to include
            6. Composition guidelines (rule of thirds, symmetry, etc.)
            7. Negative prompts (what to avoid)

            Format as a JSON object:
            {{
                "prompt": "Detailed positive prompt for image generation",
                "negative_prompt": "Things to avoid in the image",
                "style": "Art style description",
                "aspect_ratio": "1:1" // for social media
            }}

            Make the prompt detailed but not overly long (ideally under 200 words).
            """

            try:
                response = self.llm._call(prompt)
                optimized_prompt = json.loads(response)
                prompts.append({
                    'post_index': i,
                    'original_content': content,
                    **optimized_prompt
                })
            except json.JSONDecodeError:
                # Fallback prompt structure
                prompts.append({
                    'post_index': i,
                    'original_content': content,
                    'prompt': f"Create a beautiful, modern image of {image_concept}. Vibrant colors, clean composition, suitable for social media.",
                    'negative_prompt': "blurry, low quality, distorted, ugly",
                    'style': "modern digital art",
                    'aspect_ratio': "1:1"
                })
            except Exception as e:
                print(f"Error optimizing prompt for post {i}: {e}")
                # Add fallback prompt
                prompts.append({
                    'post_index': i,
                    'original_content': content,
                    'prompt': f"Create a beautiful, modern image of {image_concept}. Vibrant colors, clean composition.",
                    'negative_prompt': "blurry, low quality",
                    'style': "digital art",
                    'aspect_ratio': "1:1"
                })

        return prompts

    def generate_image(self, prompt_data: Dict[str, Any], max_retries: int = 3) -> Optional[str]:
        """
        Generate an image using Replicate API

        Args:
            prompt_data: Dictionary containing prompt and generation parameters
            max_retries: Maximum number of retry attempts

        Returns:
            URL of the generated image or None if failed
        """
        prompt = prompt_data.get('prompt', '')
        negative_prompt = prompt_data.get('negative_prompt', '')
        aspect_ratio = prompt_data.get('aspect_ratio', '1:1')

        if not prompt:
            return None

        for attempt in range(max_retries):
            try:
                print(f"Generating image (attempt {attempt + 1}/{max_retries})...")
                print(f"Prompt: {prompt[:100]}...")

                # Generate image using Replicate
                input_data = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "aspect_ratio": aspect_ratio,
                    "num_outputs": 1,
                    "guidance_scale": 7.5,
                    "num_inference_steps": 50,
                    "seed": -1  # Random seed
                }

                output = self.replicate_client.run(
                    self.model_name,
                    input=input_data
                )

                # Replicate returns a list of URLs
                if output and len(output) > 0:
                    image_url = output[0]
                    print(f"Image generated successfully: {image_url}")
                    return image_url

            except Exception as e:
                print(f"Error generating image (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue

        print(f"Failed to generate image after {max_retries} attempts")
        return None

    def generate_batch_images(self, optimized_prompts: List[Dict[str, Any]],
                            delay_between_requests: float = 2.0) -> List[Dict[str, Any]]:
        """
        Generate multiple images in batch with delays to avoid rate limiting

        Args:
            optimized_prompts: List of optimized prompt data
            delay_between_requests: Delay in seconds between requests

        Returns:
            List of results with image URLs or error messages
        """
        results = []

        for i, prompt_data in enumerate(optimized_prompts):
            print(f"Generating image {i + 1}/{len(optimized_prompts)}")

            image_url = self.generate_image(prompt_data)

            result = {
                'post_index': i,
                'prompt_data': prompt_data,
                'image_url': image_url,
                'status': 'success' if image_url else 'failed',
                'error': None if image_url else 'Image generation failed'
            }

            results.append(result)

            # Add delay between requests to avoid rate limiting
            if i < len(optimized_prompts) - 1:
                time.sleep(delay_between_requests)

        return results

    def download_image(self, image_url: str, save_path: str) -> bool:
        """
        Download image from URL to local file

        Args:
            image_url: URL of the generated image
            save_path: Local path to save the image

        Returns:
            True if download successful, False otherwise
        """
        try:
            import requests
            response = requests.get(image_url)
            response.raise_for_status()

            with open(save_path, 'wb') as f:
                f.write(response.content)

            print(f"Image downloaded to: {save_path}")
            return True

        except Exception as e:
            print(f"Error downloading image: {e}")
            return False

    def validate_image_content(self, image_url: str, expected_content: str) -> Dict[str, Any]:
        """
        Validate that the generated image matches expected content

        Args:
            image_url: URL of the generated image
            expected_content: Description of what the image should contain

        Returns:
            Validation result with scores and recommendations
        """
        # This is a placeholder for image validation
        # In a real implementation, you might use vision models to validate content
        return {
            'url': image_url,
            'validation_score': 8.5,  # Placeholder score
            'content_match': True,   # Placeholder validation
            'quality_score': 8.0,    # Placeholder quality score
            'recommendations': []     # Empty for now
        }

    def create_image_metadata(self, prompt_data: Dict[str, Any], image_url: str,
                            validation_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create comprehensive metadata for generated images

        Args:
            prompt_data: Original prompt data used for generation
            image_url: URL of the generated image
            validation_result: Optional validation results

        Returns:
            Complete metadata dictionary
        """
        metadata = {
            'generation_timestamp': time.time(),
            'model_used': self.model_name,
            'prompt_used': prompt_data.get('prompt', ''),
            'negative_prompt': prompt_data.get('negative_prompt', ''),
            'style': prompt_data.get('style', ''),
            'aspect_ratio': prompt_data.get('aspect_ratio', '1:1'),
            'image_url': image_url,
            'post_index': prompt_data.get('post_index', -1),
            'validation': validation_result or {}
        }

        return metadata

    def cleanup_old_images(self, image_dir: str, max_age_hours: int = 24) -> int:
        """
        Clean up old generated images to save storage space

        Args:
            image_dir: Directory containing generated images
            max_age_hours: Maximum age in hours before deletion

        Returns:
            Number of files deleted
        """
        import os
        import time

        if not os.path.exists(image_dir):
            return 0

        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        deleted_count = 0

        for filename in os.listdir(image_dir):
            file_path = os.path.join(image_dir, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        print(f"Deleted old image: {filename}")
                    except Exception as e:
                        print(f"Error deleting {filename}: {e}")

        return deleted_count