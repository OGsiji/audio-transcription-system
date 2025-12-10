"""
Book Formatter - Converts raw transcripts into publishable book format

This module takes raw transcriptions and uses Gemini to:
1. Clean up filler words, repetitions, and speech artifacts
2. Organize content into logical chapters
3. Improve readability while preserving the original message
4. Add proper formatting for publishing
"""

import logging
from typing import List, Dict, Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)


class BookFormatter:
    """Format transcripts into publishable book chapters"""
    
    def __init__(self, gemini_api_key: str, model_name: str = "gemini-2.5-flash"):
        """
        Initialize book formatter
        
        Args:
            gemini_api_key: Google Gemini API key
            model_name: Gemini model to use
        """
        self.gemini_api_key = gemini_api_key
        self.model_name = model_name
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel(model_name)
    
    def format_series_to_book(
        self,
        transcripts: List[Dict],
        book_title: str,
        author_name: str
    ) -> Dict:
        """
        Convert a series of transcripts into a publishable book
        
        Args:
            transcripts: List of transcript dictionaries from transcription
            book_title: Title of the book
            author_name: Name of the author/speaker
            
        Returns:
            Dictionary with book structure including chapters, foreword, etc.
        """
        logger.info(f"Formatting {len(transcripts)} transcripts into book: {book_title}")
        
        # Sort transcripts by filename to maintain order
        sorted_transcripts = sorted(transcripts, key=lambda x: x.get('file_path', ''))
        
        # Generate book structure
        book = {
            "title": book_title,
            "author": author_name,
            "foreword": self._generate_foreword(sorted_transcripts, book_title, author_name),
            "chapters": [],
            "total_chapters": len(sorted_transcripts)
        }
        
        # Process each transcript into a chapter
        for idx, transcript in enumerate(sorted_transcripts, 1):
            if not transcript.get('success'):
                logger.warning(f"Skipping failed transcript: {transcript.get('file_path')}")
                continue
            
            chapter = self._format_chapter(
                transcript_data=transcript['result'],
                chapter_number=idx,
                total_chapters=len(sorted_transcripts),
                book_title=book_title
            )
            
            book['chapters'].append(chapter)
            logger.info(f"Formatted chapter {idx}/{len(sorted_transcripts)}: {chapter['title']}")
        
        return book
    
    def _generate_foreword(
        self,
        transcripts: List[Dict],
        book_title: str,
        author_name: str
    ) -> str:
        """Generate a foreword for the book based on the series content"""
        
        # Get summaries from all successful transcripts
        summaries = []
        for t in transcripts:
            if t.get('success') and t.get('result', {}).get('summary'):
                summaries.append(t['result']['summary'])
        
        prompt = f"""
        You are writing a foreword for a book titled "{book_title}" by {author_name}.
        
        This book is based on a series of {len(transcripts)} recordings. Here are the summaries:
        
        {chr(10).join(f"{i+1}. {s}" for i, s in enumerate(summaries[:10]))}
        
        Write a compelling foreword (2-3 paragraphs) that:
        1. Introduces the theme and purpose of this series
        2. Explains what readers will gain from this book
        3. Sets the tone for the journey ahead
        
        Keep it warm, inviting, and focused on the value to the reader.
        Return ONLY the foreword text, no additional commentary.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to generate foreword: {e}")
            return f"This book contains a series of {len(transcripts)} messages on important themes of faith and life."
    
    def _format_chapter(
        self,
        transcript_data: Dict,
        chapter_number: int,
        total_chapters: int,
        book_title: str
    ) -> Dict:
        """
        Format a single transcript into a book chapter
        
        This is the key function that cleans and organizes the raw transcript
        """
        
        raw_transcription = transcript_data.get('transcription', '')
        summary = transcript_data.get('summary', '')
        topics = transcript_data.get('key_topics', [])
        
        prompt = f"""
        You are a professional editor converting sermon/lecture transcripts into publishable book chapters.
        
        IMPORTANT INSTRUCTIONS:
        1. This is Chapter {chapter_number} of {total_chapters} in the book "{book_title}"
        2. Clean up the text but PRESERVE THE COMPLETE MESSAGE - do not summarize
        3. Remove filler words (um, uh, you know, etc.)
        4. Fix grammar and sentence structure for readability
        5. Organize into logical paragraphs
        6. Keep the speaker's voice and style
        7. Add subheadings for major sections (format as "## Subheading")
        8. If there are scripture references, keep them
        
        DO NOT:
        - Summarize or shorten the content
        - Change the meaning or theology
        - Add content that wasn't said
        - Remove important examples or stories
        
        Raw transcript:
        {raw_transcription}
        
        Summary (for context):
        {summary}
        
        Key topics covered:
        {', '.join(topics)}
        
        Return a JSON object with this structure:
        {{
            "chapter_title": "Descriptive chapter title (3-8 words)",
            "chapter_number": {chapter_number},
            "content": "The cleaned, formatted chapter text with subheadings",
            "key_points": ["3-5 key takeaways from this chapter"],
            "scripture_references": ["Any Bible verses mentioned"],
            "word_count": approximate_word_count
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            import json
            chapter = json.loads(response_text.strip())
            
            return chapter
            
        except Exception as e:
            logger.error(f"Failed to format chapter {chapter_number}: {e}")
            # Fallback - return minimally formatted version
            return {
                "chapter_title": f"Chapter {chapter_number}",
                "chapter_number": chapter_number,
                "content": raw_transcription,
                "key_points": topics[:5] if topics else [],
                "scripture_references": [],
                "word_count": len(raw_transcription.split())
            }
