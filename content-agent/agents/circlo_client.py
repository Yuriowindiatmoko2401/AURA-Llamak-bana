"""
Circlo Authentication Client
Handles JWT authentication with Circlo API
"""

import os
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()


class CircloClient:
    """Client for handling Circlo API posting"""

    def __init__(self):
        self.base_url = "https://api.getcirclo.com"
        self.direct_post_url = "https://api.getcirclo.com/api/user-preferences/recommend/create-post"
        self.bearer_token = os.getenv("CIRCLO_JWT")  # Using JWT as Bearer token
        self.authenticated = False
        self.user_data = None

    async def authenticate(self) -> Dict[str, Any]:
        """
        Validate Circlo API access using Bearer token

        Returns:
            Dict containing authentication response
        """
        if not self.bearer_token:
            return {
                "success": False,
                "error": "CIRCLO_JWT environment variable not set"
            }

        # We're using Bearer token authentication directly for posting
        # No separate auth endpoint needed based on current API docs
        self.authenticated = True
        self.user_data = {"token_valid": True}

        return {
            "success": True,
            "data": self.user_data,
            "message": "Bearer token authentication ready"
        }

    def get_user_data(self) -> Optional[Dict[str, Any]]:
        """Get authenticated user data"""
        return self.user_data if self.authenticated else None

    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        return self.authenticated

    async def refresh_authentication(self) -> Dict[str, Any]:
        """Refresh authentication"""
        self.authenticated = False
        self.user_data = None
        return await self.authenticate()

    async def direct_post(self, content_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post content directly to Circlo using Bearer token authentication

        Args:
            content_data: Dictionary containing post content and metadata

        Returns:
            Dict containing the API response
        """
        if not self.bearer_token:
            return {
                "success": False,
                "error": "Bearer token not available for authentication"
            }

        headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            print(f"📤 Making POST request to: {self.direct_post_url}")
            print(f"   Headers: Authorization=Bearer [REDACTED], Content-Type=application/json")
            print(f"   Payload: {content_data}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.direct_post_url,
                    headers=headers,
                    json=content_data
                )

                print(f"   Response status: {response.status_code}")
                print(f"   Response body: {response.text[:500]}...")  # Show first 500 chars

                # Handle response
                if response.status_code == 200 or response.status_code == 201:
                    result = response.json()
                    return {
                        "success": True,
                        "data": result,
                        "message": "Content posted successfully",
                        "status_code": response.status_code
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "status_code": response.status_code,
                        "response_text": response.text
                    }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timeout - API server did not respond"
            }
        except httpx.RequestError as e:
            return {
                "success": False,
                "error": f"Network error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    def format_content_for_circlo(self, content: Dict[str, Any], user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format content data to match Circlo's create-post API structure
        Based on docs: https://docs.getcirclo.com/create-post

        Required fields: media_source, caption
        Optional fields: profile, niche, keywords

        Args:
            content: Dictionary containing generated content with caption, hashtags, image_url, etc.
            user_preferences: User preferences including niche and profile information

        Returns:
            Dictionary formatted for Circlo's create-post API
        """
        # Extract basic information
        niche = user_preferences.get('niche', 'general')
        profile_type = user_preferences.get('profile_type', 'general')

        # Build the Circlo-compatible payload with required fields first
        circlo_payload = {
            "caption": content.get('caption', ''),  # Required field
        }

        # Add media_source (required) - use image URL if available, otherwise use placeholder
        if content.get('image_url'):
            circlo_payload["media_source"] = content['image_url']
        else:
            # For text-only posts, we still need media_source according to API docs
            # Use a placeholder or generate a simple text-based media
            circlo_payload["media_source"] = f"text_post_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Add optional fields
        circlo_payload["profile"] = profile_type
        circlo_payload["niche"] = niche

        # Add keywords if available
        keywords = content.get('keywords', [])

        # If no keywords, extract from hashtags
        if not keywords:
            hashtags = content.get('hashtags', [])
            if hashtags:
                # Clean hashtags and convert to keywords
                keywords = [
                    tag.lstrip('#').replace(' ', '').replace('-', '').replace('_', '')
                    for tag in hashtags[:10]  # Limit to 10 keywords
                ]

        # Ensure we have at least some keywords
        if not keywords:
            keywords = [niche.replace(' ', ''), "content", "social"]

        circlo_payload["keywords"] = keywords

        return circlo_payload

    async def post_content_to_circlo(self, content: Dict[str, Any], user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post formatted content to Circlo's create-post API

        Args:
            content: Generated content dictionary
            user_preferences: User preferences for formatting

        Returns:
            Dict containing the posting result
        """
        try:
            # Format content for Circlo
            circlo_payload = self.format_content_for_circlo(content, user_preferences)

            print(f"📤 Posting to Circlo with payload:")
            print(f"   Profile: {circlo_payload['profile']}")
            print(f"   Niche: {circlo_payload['niche']}")
            print(f"   Media Source: {circlo_payload['media_source']}")
            print(f"   Caption Length: {len(circlo_payload['caption'])}")
            print(f"   Keywords: {circlo_payload['keywords'][:5]}...")  # Show first 5 keywords

            # Post to Circlo
            result = await self.direct_post(circlo_payload)

            if result["success"]:
                print(f"✅ Successfully posted to Circlo")
                return {
                    "status": "success",
                    "message": "Content posted successfully to Circlo",
                    "circlo_data": result.get("data"),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                print(f"❌ Failed to post to Circlo: {result.get('error')}")
                return {
                    "status": "error",
                    "error": result.get("error"),
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            error_msg = f"Error posting to Circlo: {str(e)}"
            print(f"❌ {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Circlo API with Bearer token"""
        try:
            # Test with a minimal valid payload using default profile and valid image
            test_payload = {
                "caption": "Test post - API connection verification 🔧",
                "media_source": "https://replicate.delivery/xezq/pxGUAMd98fVKe0OiZ4oEHlN2UfdmaAk0imag57OBb9niECPrA/tmpn80nwj98.png",  # Use valid image URL
                "profile": "general",  # Use general instead of test
                "niche": "general",   # Use general niche
                "keywords": ["test", "api", "connection"]
            }

            test_result = await self.direct_post(test_payload)

            if test_result["success"]:
                return {
                    "status": "success",
                    "message": "Circlo API connection successful with Bearer token",
                    "direct_mode": True,
                    "response_data": test_result.get("data")
                }
            else:
                return {
                    "status": "error",
                    "message": f"Connection failed: {test_result.get('error')}",
                    "direct_mode": True,
                    "status_code": test_result.get("status_code")
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection test failed: {str(e)}",
                "direct_mode": False
            }


# Singleton instance
circlo_client = CircloClient()