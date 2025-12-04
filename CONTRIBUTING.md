# Contributing to Audio Transcription API

Thank you for your interest in contributing! This guide will help you get started.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (OS, Python version, deployment platform)
- Relevant logs or error messages

### Suggesting Features

Feature requests are welcome! Please open an issue describing:
- The problem you're trying to solve
- Your proposed solution
- Any alternatives you've considered
- How this helps the project's mission (turning audio into publishable content)

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes**
   - Write clear, readable code
   - Follow existing code style
   - Add comments for complex logic
   - Update documentation if needed

4. **Test your changes**
   ```bash
   # Run the service locally
   python main.py
   
   # Test with a sample audio file
   curl -X POST http://localhost:8000/transcribe \
     -H "Content-Type: application/json" \
     -d '{"google_drive_link": "...", "gemini_api_key": "..."}'
   ```

5. **Commit with clear messages**
   ```bash
   git commit -m "Add feature: brief description"
   ```
   
   Good commit messages:
   - "Fix: Handle M4A files without MIME type"
   - "Add: Export transcriptions to DOCX format"
   - "Update: Improve error messages for missing API keys"

6. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Development Setup

```bash
# Clone your fork
git clone https://github.com/your-username/audio-transcription-api.git
cd audio-transcription-api

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your GEMINI_KEY

# Run locally
python main.py
```

## Areas Where Help is Needed

### High Priority
- **Export formats**: Add DOCX, PDF, Markdown export
- **Chapter detection**: Automatically split long recordings into chapters
- **Error handling**: Improve error messages and recovery
- **Tests**: Add unit and integration tests

### Medium Priority
- **Web UI**: Simple interface for non-technical users
- **Webhooks**: Notify when transcription completes
- **Custom vocabulary**: Support for proper nouns and technical terms
- **Additional storage**: S3, Dropbox, Azure Blob support

### Documentation
- Tutorial videos
- Integration examples (Python, JavaScript, cURL)
- Deployment guides for different platforms
- Translations

## Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and small
- Use type hints where helpful

## Questions?

- Open an issue for questions about the codebase
- Start a Discussion for general questions
- Check existing issues before creating new ones

Thank you for contributing!
