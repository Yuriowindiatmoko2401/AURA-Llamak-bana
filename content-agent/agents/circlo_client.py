"""
Circlo Authentication Client
Handles JWT authentication with Circlo API
"""

import os
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import json

load_dotenv()


class CircloClient:
    """Client for handling Circlo API authentication"""

    def __init__(self):
        self.base_url = "https://api.getcirclo.com"
        self.direct_post_url = "https://api.getcirclo.com/api/user-preferences/recommend/create-post"
        self.jwt_token = os.getenv("CIRCLO_JWT")
        self.authenticated = False
        self.user_data = None

    async def authenticate(self) -> Dict[str, Any]:
        """
        Authenticate with Circlo API using JWT token

        Returns:
            Dict containing authentication response
        """
        if not self.jwt_token:
            return {
                "success": False,
                "error": "CIRCLO_JWT environment variable not set"
            }

        auth_url = f"{self.base_url}/api/v2/user/authenticate"

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        payload = {
            "jwtCode": self.jwt_token
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    auth_url,
                    headers=headers,
                    json=payload
                )

                # Handle response
                if response.status_code == 200:
                    result = response.json()
                    if result.get("success"):
                        self.authenticated = True
                        self.user_data = result.get("data", {})
                        return {
                            "success": True,
                            "data": self.user_data,
                            "message": "Authentication successful"
                        }
                    else:
                        return {
                            "success": False,
                            "error": result.get("error", "Authentication failed"),
                            "response": result
                        }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "status_code": response.status_code
                    }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Request timeout - authentication server did not respond"
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
        Post content directly to Circlo without authentication

        Args:
            content_data: Dictionary containing post content and metadata

        Returns:
            Dict containing the API response
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.direct_post_url,
                    headers=headers,
                    json=content_data
                )

                # Handle response
                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "data": result,
                        "message": "Content posted successfully"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "status_code": response.status_code
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

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to Circlo API"""
        try:
            # Test direct connection with minimal payload
            test_payload = {"test": True}
            test_result = await self.direct_post(test_payload)
            return {
                "status": "success" if test_result["success"] else "error",
                "message": "Circlo API connection successful" if test_result["success"] else f"Connection failed: {test_result['error']}",
                "direct_mode": True
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Connection test failed: {str(e)}",
                "direct_mode": False
            }


# Singleton instance
circlo_client = CircloClient()