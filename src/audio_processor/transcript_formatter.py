"""
Transcript Formatter
Converts raw transcriptions into clean, readable formatted text
"""

import os
import logging
from typing import Dict
from datetime import datetime

logger = logging.getLogger(__name__)


class TranscriptFormatter:
    """Formats raw transcriptions into clean, readable text documents"""

    def __init__(self):
        """Initialize the transcript formatter"""
        logger.info("TranscriptFormatter initialized")

    def format_transcript(self, transcription_data: Dict, audio_filename: str) -> str:
        """
        Format a transcription into clean, readable text

        Args:
            transcription_data: Raw transcription data from Gemini
            audio_filename: Original audio filename

        Returns:
            Formatted transcript as string
        """
        # Extract data
        transcription = transcription_data.get('transcription', '')
        language = transcription_data.get('language', 'Unknown')
        speakers = transcription_data.get('speakers', [])
        summary = transcription_data.get('summary', '')
        key_topics = transcription_data.get('key_topics', [])
        timestamps = transcription_data.get('timestamps', [])
        processing_time = transcription_data.get('processing_time', 0)
        model = transcription_data.get('model', 'Unknown')

        # Build formatted transcript
        lines = []

        # Header
        lines.append("=" * 80)
        lines.append("AUDIO TRANSCRIPTION")
        lines.append("=" * 80)
        lines.append("")

        # Metadata
        lines.append(f"File: {audio_filename}")
        lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Language: {language}")
        if speakers:
            lines.append(f"Speakers: {', '.join(speakers)}")
        lines.append(f"Transcribed by: {model}")
        lines.append(f"Processing time: {processing_time:.2f} seconds")
        lines.append("")

        # Summary (if available)
        if summary:
            lines.append("-" * 80)
            lines.append("SUMMARY")
            lines.append("-" * 80)
            lines.append("")
            lines.append(self._wrap_text(summary, width=80))
            lines.append("")

        # Key Topics (if available)
        if key_topics:
            lines.append("-" * 80)
            lines.append("KEY TOPICS")
            lines.append("-" * 80)
            lines.append("")
            for topic in key_topics:
                lines.append(f"• {topic}")
            lines.append("")

        # Main Transcript
        lines.append("=" * 80)
        lines.append("FULL TRANSCRIPT")
        lines.append("=" * 80)
        lines.append("")

        # Format the full transcription with proper line breaks (no timestamps)
        lines.append(self._format_paragraphs(transcription))

        # Footer
        lines.append("")
        lines.append("-" * 80)
        lines.append("End of Transcript")
        lines.append("-" * 80)

        return "\n".join(lines)

    def _wrap_text(self, text: str, width: int = 80, indent: int = 0) -> str:
        """
        Wrap text to specified width with optional indentation

        Args:
            text: Text to wrap
            width: Maximum line width
            indent: Number of spaces to indent

        Returns:
            Wrapped text
        """
        if not text:
            return ""

        words = text.split()
        lines = []
        current_line = " " * indent

        for word in words:
            if len(current_line) + len(word) + 1 <= width:
                if current_line.strip():
                    current_line += " " + word
                else:
                    current_line += word
            else:
                if current_line.strip():
                    lines.append(current_line)
                current_line = " " * indent + word

        if current_line.strip():
            lines.append(current_line)

        return "\n".join(lines)

    def _format_paragraphs(self, text: str, width: int = 80) -> str:
        """
        Format text into readable paragraphs

        Args:
            text: Raw text
            width: Maximum line width

        Returns:
            Formatted text with paragraphs
        """
        if not text:
            return ""

        # Split on common paragraph indicators
        paragraphs = []
        current_para = []

        sentences = text.replace('. ', '.\n').replace('? ', '?\n').replace('! ', '!\n').split('\n')

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            current_para.append(sentence)

            # Create paragraph every 4-5 sentences or at topic changes
            if len(current_para) >= 5:
                para_text = ' '.join(current_para)
                paragraphs.append(self._wrap_text(para_text, width=width))
                current_para = []

        # Add remaining sentences
        if current_para:
            para_text = ' '.join(current_para)
            paragraphs.append(self._wrap_text(para_text, width=width))

        return "\n\n".join(paragraphs)

    def save_formatted_transcript(
        self,
        transcription_data: Dict,
        audio_filename: str,
        output_path: str
    ) -> str:
        """
        Format and save transcript to a text file

        Args:
            transcription_data: Raw transcription data
            audio_filename: Original audio filename
            output_path: Path to save formatted transcript

        Returns:
            Path to saved file
        """
        try:
            # Format the transcript
            formatted_text = self.format_transcript(transcription_data, audio_filename)

            # Save to file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)

            logger.info(f"Saved formatted transcript to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to save formatted transcript: {e}")
            raise

    def create_combined_transcript(
        self,
        transcription_results: list,
        output_path: str,
        title: str = "Combined Transcription"
    ) -> str:
        """
        Combine multiple transcriptions into a single document

        Args:
            transcription_results: List of transcription results
            output_path: Path to save combined transcript
            title: Title for the combined document

        Returns:
            Path to saved file
        """
        try:
            lines = []

            # Header
            lines.append("=" * 80)
            lines.append(title.upper())
            lines.append("=" * 80)
            lines.append("")
            lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"Total files: {len(transcription_results)}")
            lines.append("")
            lines.append("")

            # Process each file
            for idx, result in enumerate(transcription_results, 1):
                if not result.get('success'):
                    continue

                file_path = result.get('file_path', 'Unknown')
                filename = os.path.basename(file_path)
                transcription_data = result.get('result', {})

                # File header
                lines.append("=" * 80)
                lines.append(f"FILE {idx}: {filename}")
                lines.append("=" * 80)
                lines.append("")

                # Add formatted content
                formatted = self.format_transcript(transcription_data, filename)

                # Skip the header from individual file (avoid duplication)
                formatted_lines = formatted.split('\n')
                # Find where "FULL TRANSCRIPT" starts
                start_idx = 0
                for i, line in enumerate(formatted_lines):
                    if 'FULL TRANSCRIPT' in line:
                        start_idx = i + 3  # Skip the header and separator
                        break

                if start_idx > 0:
                    lines.extend(formatted_lines[start_idx:])
                else:
                    lines.append(transcription_data.get('transcription', ''))

                lines.append("")
                lines.append("")

            # Footer
            lines.append("=" * 80)
            lines.append("END OF COMBINED TRANSCRIPT")
            lines.append("=" * 80)

            # Save to file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))

            logger.info(f"Saved combined transcript to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to create combined transcript: {e}")
            raise
