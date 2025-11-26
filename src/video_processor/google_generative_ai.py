import time
import os
import asyncio
import json
import logging
import re
import json
from typing import Dict, List, Optional, Any

import google.generativeai as genai
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from src.config.settings import settings

# Configure logging
environment = settings.NODE_ENV
log_level = logging.DEBUG if environment == "development" else logging.INFO

logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Reduce third-party noise
logging.getLogger("kafka").setLevel(logging.WARNING)


class EnhancedGoogleGenerativeService:
    """Enhanced Google Generative AI Service for video analysis, safety checks, and content tagging"""

    def __init__(self):
        # Initialize Gemini AI
        self.gemini_key = settings.GEMINI_KEY
        if not self.gemini_key:
            raise ValueError("GEMINI_KEY environment variable is not set")

        genai.configure(api_key=self.gemini_key)
        self.model_name = settings.GEMINI_MODEL
        self.timeout = settings.GEMINI_TIMEOUT

        # Initialize Slack client
        self.slack_token = settings.SLACK_BOT_TOKEN
        if not self.slack_token:
            raise ValueError("SLACK_BOT_TOKEN environment variable is not set")

        self.slack_client = WebClient(token=self.slack_token)
        self.slack_channels = settings.get_slack_channels()

        logging.info("Enhanced Google Generative AI Service initialized successfully")

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the AI service"""
        try:
            # Test Gemini connection
            genai.list_models()
            gemini_status = "healthy"
        except Exception as e:
            logging.error(f"Gemini AI health check failed: {e}")
            gemini_status = "unhealthy"

        try:
            # Test Slack connection
            self.slack_client.auth_test()
            slack_status = "healthy"
        except Exception as e:
            logging.error(f"Slack health check failed: {e}")
            slack_status = "unhealthy"

        return {
            "gemini_ai": gemini_status,
            "slack_integration": slack_status,
            "model": self.model_name,
            "timeout": self.timeout,
        }

    async def analyze_video_safety_and_tags(
        self, video_path: str, circo_post: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze video for safety and generate tags using combined Gemini prompt

        Args:
            video_path: Path to the processed video file
            circo_post: CircoPost data containing metadata

        Returns:
            Dict containing safety_check, tags, aiContext, and video_info
        """
        try:
            job_id = circo_post.get("jobId", "unknown")

            # Upload video to Gemini
            video_file = genai.upload_file(video_path)

            # Wait for processing
            while video_file.state.name == "PROCESSING":
                await asyncio.sleep(10)
                video_file = genai.get_file(video_file.name)

            if video_file.state.name == "FAILED":
                raise ValueError("Gemini video processing failed")

            # Combined safety and tagging prompt
            prompt = self.get_combined_safety_tagging_prompt()

            model = genai.GenerativeModel(model_name=self.model_name)
            response = model.generate_content(
                [video_file, prompt], request_options={"timeout": self.timeout}
            )

            if not response or not response.text:
                raise ValueError("No response from Gemini AI")

            print(response.text)  # Debugging line to see the response

            # Parse JSON response
            try:
                analysis_result = (
                    await EnhancedGoogleGenerativeService.extract_json_from_response(
                        response.text
                    )
                )
            except json.JSONDecodeError:
                # Fallback if response is not JSON
                logging.warning(
                    f"Invalid JSON response from Gemini: {response.text[:200]}..."
                )
                analysis_result = {
                    "safety_check": {
                        "contentFlag": "BLOCK_VIOLATION",
                        "reason": "Invalid AI response format",
                    },
                    "tags": [],
                    "aiContext": (
                        response.text if response.text else "No context available"
                    ),
                }

            # Ensure proper structure and add metadata
            result = {
                "jobId": job_id,
                "safety_check": analysis_result.get(
                    "safety_check",
                    {
                        "contentFlag": "BLOCK_VIOLATION",
                        "reason": "Unknown safety status",
                    },
                ),
                "tags": analysis_result.get("tags", []),
                "aiContext": analysis_result.get("aiContext", "No context available"),
                "video_info": self._extract_video_info(circo_post),
                "analysis_metadata": {
                    "model": self.model_name,
                    "timestamp": int(time.time()),
                    "processing_time": None,  # Can be calculated by caller
                },
            }

            logging.info(
                f"Successfully analyzed video safety and tags for job {job_id}"
            )
            return result

        except Exception as e:
            logging.error(f"Error in Gemini safety and tag analysis: {e}")
            return {
                "jobId": circo_post.get("jobId", "unknown"),
                "safety_check": {
                    "contentFlag": "BLOCK_VIOLATION",
                    "reason": f"Analysis failed: {str(e)}",
                },
                "tags": [],
                "aiContext": f"Analysis error: {str(e)}",
                "video_info": self._extract_video_info(circo_post),
                "analysis_metadata": {
                    "model": self.model_name,
                    "timestamp": int(time.time()),
                    "error": str(e),
                },
            }

    @staticmethod
    async def extract_json_from_response(response_text: str) -> dict:
        """
        Extract JSON from Gemini response that may be wrapped in markdown code blocks
        """
        try:
            # First, try to parse as direct JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code blocks
        # Pattern 1: ```json ... ```
        json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(json_pattern, response_text, re.DOTALL | re.IGNORECASE)

        if match:
            try:
                json_content = match.group(1)
                if json_content:  # Fix: Check if match group is not None
                    return json.loads(json_content)
            except json.JSONDecodeError:
                pass

        # Pattern 2: Look for any JSON-like structure
        json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(json_pattern, response_text, re.DOTALL)

        for match_str in matches:
            try:
                return json.loads(match_str)
            except json.JSONDecodeError:
                continue

        # If all else fails, return empty dict
        return {}

    async def analyze_description_alignment(
        self, user_caption: str, ai_context: str
    ) -> Dict[str, Any]:
        """
        Analyze alignment between user caption and AI context using Gemini

        Args:
            user_caption: User's video description/caption
            ai_context: AI-generated context from safety analysis

        Returns:
            Dict containing alignment score, level, justification, and suggestion
        """
        try:
            if not ai_context:
                return {
                    "alignmentScore": 0,
                    "alignmentLevel": "POOR",
                    "justification": "No AI context provided for comparison",
                    "suggestion": "AI context is required for accurate description analysis",
                    "analysis_metadata": {
                        "model": self.model_name,
                        "timestamp": int(time.time()),
                        "error": "Missing AI context",
                    },
                }

            if not user_caption.strip():
                return {
                    "alignmentScore": 0,
                    "alignmentLevel": "POOR",
                    "justification": "No user caption provided",
                    "suggestion": "A caption is required for alignment analysis",
                    "analysis_metadata": {
                        "model": self.model_name,
                        "timestamp": int(time.time()),
                        "error": "Missing user caption",
                    },
                }

            # Description alignment prompt
            prompt = self.get_description_alignment_prompt(user_caption, ai_context)

            model = genai.GenerativeModel(model_name=self.model_name)
            response = model.generate_content(prompt, request_options={"timeout": 300})

            if not response or not response.text:
                raise ValueError("No response from Gemini AI")

            try:
                alignment_result = (
                    await EnhancedGoogleGenerativeService.extract_json_from_response(
                        response.text
                    )
                )

                # Add metadata
                alignment_result["analysis_metadata"] = {
                    "model": self.model_name,
                    "timestamp": int(time.time()),
                    "input_length": {
                        "caption": len(user_caption),
                        "context": len(ai_context),
                    },
                }

                return alignment_result

            except json.JSONDecodeError:
                # Fallback scoring if JSON parsing fails
                logging.warning(
                    f"Invalid JSON response for description alignment: {response.text[:200]}..."
                )
                return {
                    "alignmentScore": 50,
                    "alignmentLevel": "FAIR",
                    "justification": "Could not parse AI response, defaulting to fair alignment",
                    "suggestion": "Consider reviewing and improving the caption for better alignment",
                    "analysis_metadata": {
                        "model": self.model_name,
                        "timestamp": int(time.time()),
                        "error": "JSON parsing failed",
                    },
                }

        except Exception as e:
            logging.error(f"Error in description alignment analysis: {e}")
            return {
                "alignmentScore": 0,
                "alignmentLevel": "POOR",
                "justification": f"Analysis failed: {str(e)}",
                "suggestion": "Please review the caption manually",
                "analysis_metadata": {
                    "model": self.model_name,
                    "timestamp": int(time.time()),
                    "error": str(e),
                },
            }

    def get_combined_safety_tagging_prompt(self) -> str:
        """Get the combined safety check and tagging prompt"""
        return """
You are an expert video content analyst and a content policy moderator for the platform Circo. Your task is to analyze the provided video, enforce the content policy, and classify the content according to the 'Circo Interest Categories & Subcategories' list. You must adhere strictly to all rules and the required output format.

Part 1: Content Policy Enforcement
First, you must evaluate the video against Circo's Content Policy and assign a `contentFlag`. This is your most important task.

* `contentFlag: "SAFE"`
    Assign this flag if the video contains no mature or policy-violating material. This is the default for most content.

* `contentFlag: "RESTRICT_18+"`
    Assign this flag for content that is allowed on the platform but is considered mature and should be age-gated (18+) and de-amplified from the main "For You" page. This includes:
    - Sex Education: Factual, educational content about sexual health, consent, and safe sex practices.
    - Artistic & Sensual Expression: Content like professional pole dancing, sensual dance, or non-graphic artistic representations of the human body focused on expression and body positivity.
    - NSFW Humor: Comedic skits, jokes, or commentary with mature themes that are not graphically explicit.
    - Mature Discussions: Conversational or educational content about relationships, intimacy, kink, or fetishes that is not visually explicit.

* `contentFlag: "BLOCK_VIOLATION"`
    Assign this flag for content that is strictly forbidden and must be blocked. This includes:
    - Pornography: Any depiction of sexually explicit acts.
    - Non-Consensual Content: Any content depicting sexual acts without clear consent.
    - Hate Speech & Harassment: Content that attacks or demeans individuals or groups.
    - Graphic Violence or Gore: Extreme, graphic depictions of violence or injury.
    - Dangerous Acts: Content promoting self-harm or dangerous challenges.
    - Child Exploitative Content: Any content that could exploit or harm minors.

Part 2: Interest & Subcategory Tagging
If the content is SAFE or RESTRICT_18+, classify it according to these Circo Interest Categories:

1. Entertainment & Gossip: Celebrity News, Reality TV, Viral Moments, Breakups & Hookups, Red Carpet, Influencer Drama, Nollywood Buzz, African Royalty, Paparazzi, Awards & Events, Rumors & Leaks, Memes & Trends, Behind-the-Scenes, Social Media Fights, Baby Bumps & Babies, Throwback Moments, Housemate Highlights, Scandals, Fashion Police, Entertainment Reviews, Fan Reactions, Rich Kid Chronicles, Musician Feuds, Flashbacks, Reunions

2. Music: Afrobeats, Gospel, Hip-Hop, R&B, Amapiano, Live Performances, Cover Songs, Music Reviews, Artist Freestyles, Street Music, Throwback Hits, Music Videos, Studio Sessions, Breakthrough Artists, DJ Mixes, Music Battles, Indigenous Sounds, Interviews & Behind-the-Mic, Lyrics & Meaning, Sound Engineering, TikTok Challenges, New Releases, Fan Tributes, Top Charts, Instrumentals

3. Food & Cooking: Street Food, African Dishes, Quick Meals, Traditional Recipes, Food Reviews, Budget Cooking, Baking, Drinks & Cocktails, Food Challenges, Cooking Tips, Kitchen Hacks, Celebrity Chefs, Food Vlogging, Restaurant Tours, Vegan & Healthy, Jollof Wars, Food Markets, Home Cooking, Spicy Dishes, Cooking for Events, Continental Fusion, Recipe Recreation, Meals for Kids, Plating & Aesthetics, Cooking Mistakes

4. Business & Money: Side Hustles, Investing Basics, Mobile Money, Forex & Crypto, Personal Finance, Entrepreneurship, African Startups, Grant Opportunities, Real Estate, Business News, Savings & Budgeting, Small Biz Tips, Market Trends, Online Selling, Youth Finance, Women in Business, Business Interviews, Risk Management, Stock Market, Passive Income, Freelancing, Digital Business, E-commerce, Money Scams, Business Fails

5. Tech & Innovation: Mobile Apps, African Startups, Product Reviews, Gadgets & Unboxing, Coding Tips, Tech News, AI & Automation, EdTech, Internet & Data Tips, Developer Vlogs, Cybersecurity, Fintech, How-To Tech, Hardware Builds, Local Innovation, Space & Science, Tech Events, Smart Homes, Cloud & SaaS, Tech DIY, UI/UX, Digital Tools, Tech Comedy, Internet Culture, AR/VR & Metaverse

6. Education & Self-Development: Study Hacks, Exam Prep, Career Advice, Public Speaking, Productivity Tips, Reading & Book Summaries, Financial Literacy, Skill Acquisition, Personal Branding, Time Management, Online Courses, Mindset Shift, Motivational Talks, Student Life, Academic Scholarships, Mental Clarity, Growth Mindset, Resume & Interview Tips, Soft Skills, Coding for Beginners, Personal Discipline, Language Learning, Study Abroad, Journaling, Goal Setting

7. Sports & Fitness: Football Highlights, Workout Routines, Gym Motivation, Athlete Profiles, Match Analysis, Sports Gossip, African Leagues, Women in Sports, Sports Comedy, Home Workouts, Injury Prevention, Live Scores, Football Skills, Boxing & MMA, Street Sports, Esports Fitness, Fitness Challenges, Supplements & Nutrition, Fitness Myths, Daily Exercise, Youth Sports, Coaching Tips, National Teams, Bodybuilding, Fantasy Sports

8. News & Opinions: Breaking News, Local Stories, Investigative Reports, Commentary, Social Issues, Global News, Community Watch, News Roundups, Panel Discussions, Youth Voices, Opinion Pieces, Interviews, Fact-Checking, Editorials, UGC Reports, Media Reactions, Diaspora Watch, Civic Education, Crime Reports, Environment, Legal & Courts, Trending Topics, Press Reviews, Activism, Satire & Parody

9. Religion: Gospel Sermons, Islamic Teachings, Daily Devotionals, Prayers, Spiritual Questions, Religious Music, Bible Study, Quran Recitation, Church Highlights, Islamic Lectures, Faith & Lifestyle, Miracles & Testimonies, Interfaith Dialogue, Religious Events, Youth & Faith, Christian Comedy, Motivation from Scripture, End Time Messages, Fasting & Prayer, Prophecies, Faith Debates, Sunday Messages, Mosque Moments, Faith & Money, Marriage in Faith

10. Comedy & Skits: Relationship Skits, Village Comedy, Office Banter, Slang Humor, Pranks, Stand-up Clips, Political Satire, Skits about Parents, Dating Misadventures, Campus Life, Parody Songs, Nigerian Comedy, Ghanaian Humor, Everyday Frustrations, Situationship Skits, Religious Comedy, Voiceover Comedy, Meme Reenactments, Social Media Comedy, Dance Comedy, Regional Dialects, Fashion Fails, Food Jokes, Comic Reactions, Skit Series

11. Web3 & Finance: Crypto Basics, NFT Culture, Blockchain Explained, DeFi Tips, Wallet Safety, Token Reviews, Web3 News, Smart Contracts, Trading Signals, Scams to Avoid, Metaverse Trends, Web3 Startups, Yield Farming, Web3 Jobs, Decentralized Apps, DAO Governance, Gas Fees Explained, Play-to-Earn Games, Layer 2 Solutions, Real Use Cases, Airdrops & Giveaways, Digital Identity, Stablecoins, On-chain Analysis, Community Tokens

12. Movie & Drama: Nollywood Reviews, Series Breakdowns, Love Stories, Suspense & Thriller, Movie Recaps, Behind the Scenes, Short Films, Classic Movies, Cinema Releases, Actor Spotlights, Comedy Drama, Youth Series, K-Drama Fandom, Soap Operas, Movie Trailers, Movie Monologues, Reenactments, Soundtrack Highlights, Subtitled Clips, Fan Theories, Celebrity Cameos, Script Reads, Film Production, Drama Challenges, Viewer Reactions

13. Career & Workplace: CV Writing, Interview Prep, Work From Home, Office Politics, Career Switch, Entry-Level Advice, Job Opportunities, Workplace Humor, Productivity Tips, Corporate Culture, Professional Etiquette, Career Coaching, Remote Tools, Tech Careers, Soft Skills, Salary Negotiation, Career Stories, Intern Diaries, Women at Work, Startup Jobs, Burnout & Recovery, Performance Reviews, Freelancing Life, Job Rejections, Leadership Tips

14. Communities: Student Communities, Diaspora Life, Women Groups, Tech Communities, Creators Circle, Writers' Hub, Activist Spaces, LGBTQ+ Voices, Faith Circles, Rural Voices, African Creators, Campus Tribes, Neighborhood Watch, Community Service, Fans & Fandoms, Single Parents, Youth Clubs, Fashion Tribes, Entrepreneurs Unite, Language Groups, City Spotlights, Alumni Networks, Creatives & Makers, Immigrant Life, Tribal & Ethnic Unity

15. Travel and Tourism: Local Destinations, Budget Travel, Travel Vlogs, Food Tourism, Cultural Experiences, Nature & Parks, Road Trips, Historical Sites, Travel Hacks, African Wonders, Urban Adventures, Travel Safety, Beach Diaries, Border Crossings, Group Trips, Honeymoon Spots, Travel Photography, Wildlife Tours, Festivals Abroad, Backpacking, Rural Exploration, Hotel Reviews, Airport Diaries, Language Abroad, Visa Stories

16. Health and Wellness: Mental Health, Fitness Goals, Healthy Eating, Women's Health, Men's Health, Stress Management, Home Remedies, Disease Awareness, Therapy & Counseling, Nutrition Tips, Weight Loss, Meditation, Health Tech, Sexual Health, Sleep Hygiene, Menstrual Health, Pregnancy & Birth, Herbal Medicine, Body Positivity, Fitness Myths, COVID & Vaccines, Daily Wellness Routines, Medical Stories, Public Health, Health Q&A

17. Lifestyle & Culture: Daily Vlogs, Home Decor, Morning Routines, Night Routines, Cultural Practices, Festive Celebrations, Family Life, Shopping Vlogs, Minimalist Living, Local Languages, African Proverbs, Productivity Hacks, Meal Prepping, Sustainable Living, Cleaning Routines, DIY Crafts, Parenting Tips, Celebrating Traditions, Personal Journals, Rituals & Customs, Life Lessons, Urban Living, Digital Detox, Weekend Diaries, Life Abroad

18. Art & Culture: Painting Process, Traditional Art, Dance Performances, Spoken Word, Drawing Time-lapse, Fashion Design, Art Commentary, Poetry, Sculpture, Graffiti & Street Art, Photography Vlogs, Artist Profiles, Art Challenges, Theatre Clips, Cultural Dance, Music Fusion, Animation Clips, Digital Art, Craft Tutorials, Calligraphy, Cultural Artifacts, Art Exhibitions, Fan Art, Creative Expression, Restoration Projects

19. Politics: National Politics, Youth in Politics, Political Commentary, Election Updates, Law & Constitution, Government Spending, Party Analysis, Political Debates, Activism, Corruption Watch, Political History, Voter Education, Policy Review, African Union, International Politics, Protest Highlights, Legislative Summaries, Political Satire, Campaign Videos, Fact Checking, Public Office Profiles, Local Government, Women in Politics, Opinion Polls, Government Projects

20. Beauty & Fashion: Makeup Tutorials, Skincare Routines, Fashion Hauls, Style Tips, Beauty Reviews, Hair Care, Fashion Trends, Outfit Ideas, Beauty Challenges, Fashion Shows, Styling Tips, Beauty Hacks, Fashion DIY, Seasonal Fashion, Beauty Product Reviews, Fashion History, Sustainable Fashion, Men's Grooming, Fashion Fails, Beauty Transformations

Output Format:
Your entire response MUST be a single, valid JSON object with these keys:

```json
{
  "safety_check": {
    "contentFlag": "SAFE|RESTRICT_18+|BLOCK_VIOLATION",
    "reason": "Brief explanation for the flag assignment"
  },
  "tags": [
    {
      "category": "Category Name",
      "subcategory": ["Subcategory1", "Subcategory2"]
    }
  ],
  "aiContext": "One-sentence description of the video content and your analysis reasoning"
}
```

CRITICAL: If contentFlag is "BLOCK_VIOLATION", set tags to an empty array and explain the violation in the reason and aiContext.
CRITICAL OUTPUT FORMAT:
Return ONLY a valid JSON object without any markdown formatting or code blocks.
Do not wrap your response in ```json or ``` tags.
"""

    def get_description_alignment_prompt(
        self, user_caption: str, ai_context: str
    ) -> str:
        """Get the description alignment analysis prompt"""
        return f"""
You are an AI-powered SEO and Content Strategist. Your primary function is to analyze and score the alignment between a video's true content (represented by the `aiContext`) and the user-provided caption.

Inputs:
1. [aiContext from Video Analysis]: {ai_context}
2. [User-Provided Video Caption]: {user_caption}

Analysis Criteria:
Evaluate the User-Provided Video Caption based on:
1. Semantic Relevance: Does the caption's topic match the aiContext?
2. Keyword Overlap: Do key concepts from the aiContext appear in the caption?
3. Accuracy & Honesty: Is the caption an honest representation of the content, or is it misleading clickbait?

Your entire response MUST be a single, valid JSON object with these keys:
1. `alignmentScore`: An integer score from 0 to 100
2. `alignmentLevel`: A string: 90-100: `EXCELLENT`, 70-89: `GOOD`, 45-69: `FAIR`, 0-44: `POOR`
3. `justification`: A brief explanation for your score
4. `suggestion`: If score is below 90, provide an improved caption. If 90+, confirm it's excellent.

Example:
```json
{{
  "alignmentScore": 75,
  "alignmentLevel": "GOOD",
  "justification": "Caption matches video content with relevant keywords but could be more specific",
  "suggestion": "Consider adding more specific details about the video content"
}}
```
"""

    async def send_safety_notification(
        self,
        analysis_result: Dict[str, Any],
        video_info: Dict[str, Any],
        circo_post: Dict[str, Any],
    ):
        """Send Slack notification based on safety analysis results"""
        if not settings.ENABLE_SLACK_NOTIFICATIONS:
            logging.info("Slack notifications disabled, skipping notification")
            return

        try:
            safety_check = analysis_result.get("safety_check", {})
            content_flag = safety_check.get("contentFlag", "UNKNOWN")

            video_name = video_info.get("name", "Unknown File")
            video_url = video_info.get("url", "Unknown Link")
            tags = analysis_result.get("tags", [])
            ai_context = analysis_result.get("aiContext", "No context available")
            job_id = analysis_result.get("jobId", "unknown")

            if content_flag == "SAFE":
                message = (
                    f":white_check_mark: *Video Safety Check PASSED* :white_check_mark:\n"
                    f"*Job ID:* {job_id}\n"
                    f"*Video File:* {video_name}\n"
                    f"*Video Link:* {video_url}\n"
                    f"*Content Flag:* {content_flag}\n"
                    f"*AI Context:* {ai_context}\n"
                    f"*Generated Tags:* {self._format_tags_for_slack(tags)}"
                )
                await self.send_slack_message(self.slack_channels["passed"], message)

            elif content_flag == "RESTRICT_18+":
                message = (
                    f":warning: *Video Requires 18+ Restriction* :warning:\n"
                    f"*Job ID:* {job_id}\n"
                    f"*Video File:* {video_name}\n"
                    f"*Video Link:* {video_url}\n"
                    f"*Content Flag:* {content_flag}\n"
                    f"*Reason:* {safety_check.get('reason', 'Mature content detected')}\n"
                    f"*AI Context:* {ai_context}\n"
                    f"*Generated Tags:* {self._format_tags_for_slack(tags)}"
                )
                await self.send_slack_message(self.slack_channels["review"], message)

            else:  # BLOCK_VIOLATION
                message = (
                    f":no_entry: *Video BLOCKED - Policy Violation* :no_entry:\n"
                    f"*Job ID:* {job_id}\n"
                    f"*Video File:* {video_name}\n"
                    f"*Video Link:* {video_url}\n"
                    f"*Content Flag:* {content_flag}\n"
                    f"*Violation Reason:* {safety_check.get('reason', 'Policy violation detected')}\n"
                    f"*AI Context:* {ai_context}\n"
                    f"*Action Required:* Manual review and potential content removal\n"
                    f"*Timestamp:* {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}"
                )
                await self.send_slack_message(self.slack_channels["review"], message)

        except Exception as e:
            logging.error(f"Error sending Slack notification: {e}")

    async def send_slack_message(self, channel: str, text: str):
        """Send message to Slack channel"""
        try:
            response = self.slack_client.chat_postMessage(channel=channel, text=text)
            logging.info(f"Slack message sent to {channel}")
            return response
        except SlackApiError as e:
            logging.error(f"Error sending Slack message: {e.response['error']}")
            return None

    def _extract_video_info(self, circo_post: Dict[str, Any]) -> Dict[str, Any]:
        """Extract video information from CircoPost"""
        try:
            media_files = circo_post.get("files", [])
            for media_item in media_files:
                if media_item.get("fileType") == "Video":
                    return {
                        "name": media_item.get("name", "unknown"),
                        "url": media_item.get("original")
                        or media_item.get("cachedOriginal", "unknown"),
                        "id": media_item.get("id", "unknown"),
                    }

            return {"name": "unknown", "url": "unknown", "id": "unknown"}
        except Exception as e:
            logging.error(f"Error extracting video info: {e}")
            return {"name": "error", "url": "error", "id": "error"}

    def _format_tags_for_slack(self, tags: List[Dict[str, Any]]) -> str:
        """Format tags for Slack message display"""
        try:
            if not tags:
                return "No tags generated"

            formatted_tags = []
            for tag in tags:
                category = tag.get("category", "Unknown")
                subcategories = tag.get("subcategory", [])
                if subcategories:
                    formatted_tags.append(f"*{category}:* {', '.join(subcategories)}")
                else:
                    formatted_tags.append(f"*{category}*")

            return "\n".join(formatted_tags)
        except Exception as e:
            logging.error(f"Error formatting tags for Slack: {e}")
            return "Error formatting tags"

    async def test_ai_connection(self) -> Dict[str, Any]:
        """Test the AI service connection and capabilities"""
        try:
            # Test model listing
            models = genai.list_models()
            available_models = [
                model.name
                for model in models
                if "generateContent" in model.supported_generation_methods
            ]

            # Test a simple content generation
            model = genai.GenerativeModel(model_name=self.model_name)
            test_response = model.generate_content(
                "Respond with exactly: 'AI service test successful'",
                request_options={"timeout": 30},
            )

            return {
                "status": "healthy",
                "model": self.model_name,
                "available_models": available_models[:5],  # Limit to first 5
                "test_response": test_response.text if test_response else "No response",
                "timestamp": int(time.time()),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": int(time.time()),
            }
