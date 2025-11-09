import requests
import json
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import os
from agents.llm_wrappers import GeminiLLM, ZAILLM

class TrendResearcher:
    def __init__(self):
        self.llm = self._get_llm()

    def _get_llm(self):
        if os.getenv("CORE_AGENT_TYPE") == "gemini":
            return GeminiLLM(api_key=os.getenv("GEMINI_API_KEY"))
        elif os.getenv("CORE_AGENT_TYPE") == "zai":
            return ZAILLM(api_key=os.getenv("ZAI_API_KEY"))
        else:
            raise ValueError("Unsupported CORE_AGENT_TYPE. Use 'gemini' or 'zai'.")

    def research_trends(self, niche: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Research trending topics based on niche and keywords

        Args:
            niche: The target niche (e.g., "AI technology", "fashion", "fitness")
            keywords: List of relevant keywords for the niche

        Returns:
            List of trending topics with metadata
        """
        # Use LLM to analyze trends based on the niche and keywords
        prompt = f"""
        As a trend research specialist, analyze current trending topics for the niche: "{niche}"

        Focus on these keywords: {', '.join(keywords)}

        Research and identify the top 10 trending topics that would be engaging for social media content.
        For each trend, provide:
        1. Topic title
        2. Brief description of why it's trending
        3. Engagement potential (high/medium/low)
        4. Target audience segments
        5. Content angle suggestions
        6. Relevant hashtags

        Format your response as a JSON array of objects with the following structure:
        {{
            "title": "Topic title",
            "description": "Why it's trending",
            "engagement_potential": "high/medium/low",
            "target_audience": ["audience1", "audience2"],
            "content_angles": ["angle1", "angle2"],
            "hashtags": ["#hashtag1", "#hashtag2"]
        }}
        """

        try:
            response = self.llm._call(prompt)
            # Try to parse as JSON
            trends_data = json.loads(response)
            return trends_data if isinstance(trends_data, list) else []
        except json.JSONDecodeError:
            # If LLM response is not valid JSON, create a fallback structure
            return self._create_fallback_trends(niche, keywords)
        except Exception as e:
            print(f"Error in trend research: {e}")
            return self._create_fallback_trends(niche, keywords)

    def _create_fallback_trends(self, niche: str, keywords: List[str]) -> List[Dict[str, Any]]:
        """Create fallback trends if LLM fails"""
        return [
            {
                "title": f"Latest {niche} innovations",
                "description": "Exploring cutting-edge developments in the field",
                "engagement_potential": "high",
                "target_audience": ["enthusiasts", "professionals"],
                "content_angles": ["educational", "inspirational"],
                "hashtags": [f"#{niche.replace(' ', '')}", "#innovation", "#trending"]
            },
            {
                "title": f"{niche} tips and tricks",
                "description": "Practical advice for improving skills and knowledge",
                "engagement_potential": "medium",
                "target_audience": ["beginners", "intermediate"],
                "content_angles": ["how-to", "tutorial"],
                "hashtags": [f"#{niche.replace(' ', '')}tips", "#howto", "#learning"]
            }
        ]

    def get_trending_hashtags(self, niche: str) -> List[str]:
        """Get trending hashtags for a specific niche"""
        prompt = f"""
        Generate 15 trending hashtags for the niche: "{niche}"

        Focus on:
        1. High-volume hashtags
        2. Niche-specific hashtags
        3. Emerging trending hashtags
        4. Engagement-focused hashtags

        Format as a JSON array of strings.
        """

        try:
            response = self.llm._call(prompt)
            hashtags = json.loads(response)
            return hashtags if isinstance(hashtags, list) else [f"#{niche.replace(' ', '')}", "#trending", "#viral"]
        except:
            return [f"#{niche.replace(' ', '')}", "#trending", "#viral", "#fyp", "#explore"]

    def analyze_content_performance(self, topic: str) -> Dict[str, Any]:
        """Analyze potential performance of a content topic"""
        prompt = f"""
        Analyze the content performance potential for this topic: "{topic}"

        Provide analysis on:
        1. Engagement score (1-10)
        2. Best posting times
        3. Optimal content format
        4. Target demographics
        5. Viral potential

        Format as JSON with keys: engagement_score, best_times, content_format, demographics, viral_potential
        """

        try:
            response = self.llm._call(prompt)
            analysis = json.loads(response)
            return analysis if isinstance(analysis, dict) else {
                "engagement_score": 7,
                "best_times": ["morning", "evening"],
                "content_format": "image + text",
                "demographics": ["18-35"],
                "viral_potential": "medium"
            }
        except:
            return {
                "engagement_score": 5,
                "best_times": ["morning", "evening"],
                "content_format": "image + text",
                "demographics": ["18-35"],
                "viral_potential": "low"
            }