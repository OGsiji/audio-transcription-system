"""
Audio Transcription Processor
Handles audio file transcription using Google Speech-to-Text or Gemini AI
"""

import os
import logging
import json
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import google.generativeai as genai
from pydub import AudioSegment
from .transcript_formatter import TranscriptFormatter

logger = logging.getLogger(__name__)


class AudioTranscriptionProcessor:
    """Processor for transcribing audio files using Google Gemini"""

    def __init__(
        self,
        gemini_api_key: str,
        model_name: str = "gemini-2.5-flash",
        temp_dir: str = "/tmp/audio_processing",
        cleanup_temp_files: bool = True,
        max_chunk_size_mb: int = 20
    ):
        """
        Initialize the audio transcription processor

        Args:
            gemini_api_key: Google Gemini API key
            model_name: Gemini model to use
            temp_dir: Temporary directory for processing
            cleanup_temp_files: Whether to clean up temporary files after processing
            max_chunk_size_mb: Maximum audio chunk size in MB for processing
        """
        self.gemini_api_key = gemini_api_key
        self.model_name = model_name
        self.temp_dir = temp_dir
        self.cleanup_temp_files = cleanup_temp_files
        self.max_chunk_size_mb = max_chunk_size_mb

        # Configure Gemini
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel(model_name)

        # Initialize transcript formatter
        self.formatter = TranscriptFormatter()

        # Create temp directory
        os.makedirs(self.temp_dir, exist_ok=True)

        logger.info(f"AudioTranscriptionProcessor initialized with model: {model_name}")

    def get_audio_duration(self, audio_path: str) -> float:
        """
        Get audio file duration in seconds

        Args:
            audio_path: Path to audio file

        Returns:
            Duration in seconds
        """
        try:
            audio = AudioSegment.from_file(audio_path)
            duration = len(audio) / 1000.0  # Convert to seconds
            return duration
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0

    def convert_to_supported_format(self, audio_path: str) -> str:
        """
        Convert audio to a format supported by Gemini (MP3, WAV, etc.)

        Args:
            audio_path: Path to audio file

        Returns:
            Path to converted audio file
        """
        try:
            audio = AudioSegment.from_file(audio_path)

            # Convert to MP3 with reasonable quality
            output_path = os.path.join(
                self.temp_dir,
                f"converted_{Path(audio_path).stem}.mp3"
            )

            audio.export(
                output_path,
                format="mp3",
                bitrate="128k",
                parameters=["-ac", "1"]  # Mono audio
            )

            logger.info(f"Converted audio to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to convert audio: {e}")
            raise

    def split_audio_if_needed(self, audio_path: str) -> List[str]:
        """
        Split audio file into chunks if it exceeds max size

        Args:
            audio_path: Path to audio file

        Returns:
            List of audio chunk paths
        """
        file_size_mb = os.path.getsize(audio_path) / (1024 * 1024)

        if file_size_mb <= self.max_chunk_size_mb:
            return [audio_path]

        try:
            audio = AudioSegment.from_file(audio_path)
            duration_ms = len(audio)

            # Calculate chunk duration based on file size
            num_chunks = int(file_size_mb / self.max_chunk_size_mb) + 1
            chunk_duration_ms = duration_ms // num_chunks

            chunks = []
            for i in range(num_chunks):
                start = i * chunk_duration_ms
                end = start + chunk_duration_ms if i < num_chunks - 1 else duration_ms

                chunk = audio[start:end]
                chunk_path = os.path.join(
                    self.temp_dir,
                    f"chunk_{i}_{Path(audio_path).name}"
                )

                chunk.export(chunk_path, format="mp3", bitrate="128k")
                chunks.append(chunk_path)

                logger.info(f"Created chunk {i+1}/{num_chunks}: {chunk_path}")

            return chunks

        except Exception as e:
            logger.error(f"Failed to split audio: {e}")
            return [audio_path]

    def transcribe_audio_with_gemini(self, audio_path: str) -> Dict:
        """
        Transcribe audio using Google Gemini

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary with transcription results
        """
        try:
            logger.info(f"Starting transcription for: {audio_path}")
            start_time = time.time()

            # Upload audio file to Gemini
            audio_file = genai.upload_file(audio_path)
            logger.info(f"Uploaded audio file: {audio_file.name}")

            # Wait for file to be processed
            while audio_file.state.name == "PROCESSING":
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)

            if audio_file.state.name == "FAILED":
                raise ValueError(f"Audio processing failed: {audio_file.state.name}")

            # Create transcription prompt
            prompt = """
            Please transcribe this audio file. Provide:
            1. A complete, accurate transcription of all spoken content
            2. Identify speakers if multiple people are speaking (Speaker 1, Speaker 2, etc.)
            3. Note any significant background sounds or music
            4. Indicate unclear or inaudible sections with [inaudible]

            Return the result in JSON format:
            {
                "transcription": "full transcription text",
                "language": "detected language",
                "speakers": ["Speaker 1", "Speaker 2"],
                "summary": "brief summary of content",
                "key_topics": ["topic1", "topic2"],
                "timestamps": [
                    {"time": "00:00", "text": "transcription segment"},
                    {"time": "00:30", "text": "transcription segment"}
                ]
            }
            """

            # Generate transcription
            response = self.model.generate_content([prompt, audio_file])

            processing_time = time.time() - start_time
            logger.info(f"Transcription completed in {processing_time:.2f} seconds")

            # Parse response
            try:
                # Try to extract JSON from response
                response_text = response.text.strip()

                # Remove markdown code blocks if present
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

                result = json.loads(response_text.strip())
            except json.JSONDecodeError:
                # Fallback: use raw text as transcription
                result = {
                    "transcription": response.text,
                    "language": "unknown",
                    "speakers": [],
                    "summary": "",
                    "key_topics": [],
                    "timestamps": []
                }

            # Add metadata
            result["processing_time"] = processing_time
            result["model"] = self.model_name
            result["file_name"] = os.path.basename(audio_path)
            result["file_size_mb"] = os.path.getsize(audio_path) / (1024 * 1024)

            # Clean up uploaded file
            genai.delete_file(audio_file.name)

            return result

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def transcribe_file(self, audio_path: str) -> Dict:
        """
        Transcribe a single audio file (with chunking if needed)

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary with complete transcription results
        """
        logger.info(f"Processing audio file: {audio_path}")

        # Convert to supported format if needed
        converted_path = audio_path
        if not audio_path.lower().endswith(('.mp3', '.wav', '.m4a')):
            converted_path = self.convert_to_supported_format(audio_path)

        # Split if file is too large
        chunks = self.split_audio_if_needed(converted_path)

        if len(chunks) == 1:
            # Single file transcription
            result = self.transcribe_audio_with_gemini(chunks[0])
        else:
            # Multiple chunks - transcribe each and merge
            logger.info(f"Processing {len(chunks)} audio chunks")
            chunk_results = []

            for i, chunk_path in enumerate(chunks):
                logger.info(f"Transcribing chunk {i+1}/{len(chunks)}")
                chunk_result = self.transcribe_audio_with_gemini(chunk_path)
                chunk_results.append(chunk_result)

            # Merge results
            result = self._merge_chunk_results(chunk_results)
            result["num_chunks"] = len(chunks)

        # Cleanup temporary files
        if self.cleanup_temp_files:
            self._cleanup_temp_files(chunks, converted_path, audio_path)

        return result

    def _merge_chunk_results(self, chunk_results: List[Dict]) -> Dict:
        """
        Merge results from multiple audio chunks

        Args:
            chunk_results: List of chunk transcription results

        Returns:
            Merged transcription result
        """
        merged = {
            "transcription": "",
            "language": chunk_results[0].get("language", "unknown"),
            "speakers": [],
            "summary": "",
            "key_topics": [],
            "timestamps": [],
            "processing_time": 0,
            "model": self.model_name,
            "file_name": chunk_results[0].get("file_name", ""),
            "file_size_mb": sum(r.get("file_size_mb", 0) for r in chunk_results)
        }

        # Merge transcriptions
        transcriptions = [r.get("transcription", "") for r in chunk_results]
        merged["transcription"] = " ".join(transcriptions)

        # Merge speakers (unique)
        all_speakers = []
        for r in chunk_results:
            all_speakers.extend(r.get("speakers", []))
        merged["speakers"] = list(set(all_speakers))

        # Merge key topics (unique)
        all_topics = []
        for r in chunk_results:
            all_topics.extend(r.get("key_topics", []))
        merged["key_topics"] = list(set(all_topics))

        # Merge summaries
        summaries = [r.get("summary", "") for r in chunk_results if r.get("summary")]
        merged["summary"] = " ".join(summaries)

        # Sum processing times
        merged["processing_time"] = sum(r.get("processing_time", 0) for r in chunk_results)

        return merged

    def _cleanup_temp_files(
        self,
        chunks: List[str],
        converted_path: str,
        original_path: str
    ):
        """Clean up temporary files after processing"""
        for chunk_path in chunks:
            if chunk_path != original_path and os.path.exists(chunk_path):
                try:
                    os.remove(chunk_path)
                    logger.debug(f"Removed temporary chunk: {chunk_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove chunk {chunk_path}: {e}")

        if converted_path != original_path and os.path.exists(converted_path):
            try:
                os.remove(converted_path)
                logger.debug(f"Removed converted file: {converted_path}")
            except Exception as e:
                logger.warning(f"Failed to remove converted file {converted_path}: {e}")

    def batch_transcribe(
        self,
        audio_files: List[str],
        output_dir: Optional[str] = None
    ) -> List[Dict]:
        """
        Transcribe multiple audio files

        Args:
            audio_files: List of audio file paths
            output_dir: Directory to save transcription results (optional)

        Returns:
            List of transcription results
        """
        results = []

        logger.info(f"Starting batch transcription of {len(audio_files)} files")

        for i, audio_path in enumerate(audio_files, 1):
            logger.info(f"Processing file {i}/{len(audio_files)}: {audio_path}")

            # Check if already transcribed (skip if exists)
            if output_dir and self._is_already_transcribed(audio_path, output_dir):
                logger.info(f"⏭️  Skipping already transcribed file: {audio_path}")

                # Load existing result
                try:
                    existing_result = self._load_existing_transcription(audio_path, output_dir)
                    results.append({
                        "file_path": audio_path,
                        "success": True,
                        "result": existing_result,
                        "skipped": True
                    })
                except Exception as e:
                    logger.warning(f"Failed to load existing transcription, will re-transcribe: {e}")
                    # Continue to transcription if loading fails
                    pass
                else:
                    continue

            try:
                result = self.transcribe_file(audio_path)
                results.append({
                    "file_path": audio_path,
                    "success": True,
                    "result": result
                })

                # Save individual result if output directory is specified
                if output_dir:
                    self._save_transcription_result(audio_path, result, output_dir)

            except Exception as e:
                logger.error(f"Failed to transcribe {audio_path}: {e}")
                results.append({
                    "file_path": audio_path,
                    "success": False,
                    "error": str(e)
                })

        logger.info(f"Batch transcription completed: {len(results)} files processed")

        # Create combined transcript if output directory is specified and we have results
        if output_dir and results:
            try:
                self._create_combined_transcript(results, output_dir)
            except Exception as e:
                logger.error(f"Failed to create combined transcript: {e}")

        return results

    def _create_combined_transcript(
        self,
        transcription_results: List[Dict],
        output_dir: str
    ):
        """
        Create a combined transcript from all successful transcriptions

        Args:
            transcription_results: List of transcription results
            output_dir: Directory to save the combined transcript
        """
        combined_filename = "combined_transcript.txt"
        combined_path = os.path.join(output_dir, combined_filename)

        logger.info(f"Creating combined transcript at: {combined_path}")

        self.formatter.create_combined_transcript(
            transcription_results=transcription_results,
            output_path=combined_path,
            title="Combined Audio Transcription"
        )

        logger.info(f"Combined transcript created successfully")

    def _is_already_transcribed(self, audio_path: str, output_dir: str) -> bool:
        """
        Check if audio file has already been transcribed

        Args:
            audio_path: Path to audio file
            output_dir: Directory where transcriptions are saved

        Returns:
            True if both JSON and TXT files exist
        """
        json_filename = f"{Path(audio_path).stem}_transcription.json"
        txt_filename = f"{Path(audio_path).stem}_transcript.txt"

        json_path = os.path.join(output_dir, json_filename)
        txt_path = os.path.join(output_dir, txt_filename)

        # Check if both files exist
        return os.path.exists(json_path) and os.path.exists(txt_path)

    def _load_existing_transcription(self, audio_path: str, output_dir: str) -> Dict:
        """
        Load existing transcription from JSON file

        Args:
            audio_path: Path to audio file
            output_dir: Directory where transcriptions are saved

        Returns:
            Transcription result dictionary
        """
        json_filename = f"{Path(audio_path).stem}_transcription.json"
        json_path = os.path.join(output_dir, json_filename)

        with open(json_path, 'r', encoding='utf-8') as f:
            result = json.load(f)

        return result

    def _save_transcription_result(
        self,
        audio_path: str,
        result: Dict,
        output_dir: str
    ):
        """Save transcription result to both JSON and formatted text files"""
        os.makedirs(output_dir, exist_ok=True)

        # Save JSON file
        json_filename = f"{Path(audio_path).stem}_transcription.json"
        json_path = os.path.join(output_dir, json_filename)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved JSON transcription to: {json_path}")

        # Save formatted text file
        txt_filename = f"{Path(audio_path).stem}_transcript.txt"
        txt_path = os.path.join(output_dir, txt_filename)

        try:
            self.formatter.save_formatted_transcript(
                transcription_data=result,
                audio_filename=os.path.basename(audio_path),
                output_path=txt_path
            )
            logger.info(f"Saved formatted transcript to: {txt_path}")
        except Exception as e:
            logger.error(f"Failed to save formatted transcript: {e}")
