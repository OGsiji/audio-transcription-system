#!/usr/bin/env python3
"""
Quick test script to verify your setup
Run this to make sure everything is configured correctly
"""

import os
import sys
from pathlib import Path

# Add color output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.GREEN}✓{Colors.END} {msg}")

def print_error(msg):
    print(f"{Colors.RED}✗{Colors.END} {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠{Colors.END} {msg}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{msg}{Colors.END}")

print_header("🔍 Audio Transcription Service - Setup Test")
print()

# Test 1: Check Python version
print_header("1. Checking Python Version")
version = sys.version_info
if version.major == 3 and version.minor >= 11:
    print_success(f"Python {version.major}.{version.minor}.{version.micro} (✓ 3.11+)")
else:
    print_error(f"Python {version.major}.{version.minor}.{version.micro} (need 3.11+)")
    print("   Please upgrade Python")

# Test 2: Check .env file
print_header("2. Checking Configuration")
env_file = Path(".env")
if env_file.exists():
    print_success(".env file exists")

    # Read and check keys
    with open(env_file) as f:
        content = f.read()

    if "GEMINI_KEY=" in content and "your_gemini_api_key_here" not in content:
        # Check if there's an actual key
        for line in content.split('\n'):
            if line.startswith('GEMINI_KEY=') and len(line.split('=', 1)[1].strip()) > 10:
                print_success("GEMINI_KEY is configured")
                break
        else:
            print_error("GEMINI_KEY appears to be empty or invalid")
    else:
        print_error("GEMINI_KEY not configured in .env")
        print("   Add your API key from https://makersuite.google.com/app/apikey")

    if "GOOGLE_DRIVE_API_KEY=" in content:
        for line in content.split('\n'):
            if line.startswith('GOOGLE_DRIVE_API_KEY=') and len(line.split('=', 1)[1].strip()) > 10:
                print_success("GOOGLE_DRIVE_API_KEY is configured")
                break
        else:
            print_warning("GOOGLE_DRIVE_API_KEY appears to be empty")
            print("   You can use the same key as GEMINI_KEY")
    else:
        print_warning("GOOGLE_DRIVE_API_KEY not found in .env")
        print("   You can use the same key as GEMINI_KEY")
else:
    print_error(".env file not found")
    print("   Run: cp .env.example .env")
    print("   Then edit .env with your API keys")

# Test 3: Check FFmpeg
print_header("3. Checking FFmpeg Installation")
try:
    import subprocess
    result = subprocess.run(['ffmpeg', '-version'],
                          capture_output=True,
                          text=True,
                          timeout=5)
    if result.returncode == 0:
        version_line = result.stdout.split('\n')[0]
        print_success(f"FFmpeg installed: {version_line}")
    else:
        print_error("FFmpeg found but not working correctly")
except FileNotFoundError:
    print_error("FFmpeg not installed")
    print("   macOS: brew install ffmpeg")
    print("   Ubuntu: sudo apt-get install ffmpeg")
except Exception as e:
    print_error(f"Error checking FFmpeg: {e}")

# Test 4: Check required dependencies
print_header("4. Checking Python Dependencies")
required_packages = {
    'fastapi': 'FastAPI web framework',
    'uvicorn': 'ASGI server',
    'pydantic': 'Data validation',
    'google.generativeai': 'Gemini AI',
    'pydub': 'Audio processing',
    'requests': 'HTTP client'
}

missing = []
for package, description in required_packages.items():
    try:
        __import__(package)
        print_success(f"{package:<25} - {description}")
    except ImportError:
        missing.append(package)
        print_error(f"{package:<25} - {description}")

if missing:
    print()
    print_warning("Missing packages detected!")
    print("   Run: pip install -r requirements.txt")

# Test 5: Check directories
print_header("5. Checking Directories")
dirs = ['audio_downloads', 'transcriptions', '/tmp/audio_processing']
for dir_path in dirs:
    path = Path(dir_path)
    try:
        path.mkdir(parents=True, exist_ok=True)
        print_success(f"{dir_path} directory ready")
    except Exception as e:
        print_error(f"Cannot create {dir_path}: {e}")

# Test 6: Try importing main modules
print_header("6. Checking Application Modules")
modules_to_test = [
    ('src.config.settings', 'Configuration module'),
    ('src.services.google_drive_service', 'Google Drive service'),
    ('src.audio_processor.audio_transcription_processor', 'Audio transcription'),
]

for module_name, description in modules_to_test:
    try:
        __import__(module_name)
        print_success(f"{description}")
    except ImportError as e:
        print_error(f"{description}: {e}")
    except Exception as e:
        print_warning(f"{description}: {e}")

# Final summary
print_header("📋 Summary")
print()

try:
    # Try to load settings
    from src.config.settings import settings

    if settings.GEMINI_KEY and settings.GOOGLE_DRIVE_API_KEY:
        print_success("All critical configuration is in place!")
        print()
        print(f"{Colors.BOLD}Next steps:{Colors.END}")
        print("1. Start the service: python main.py")
        print("2. Visit: http://localhost:8000/docs")
        print("3. Submit a transcription job with your Google Drive link")
        print()
        print(f"{Colors.BOLD}Quick test:{Colors.END}")
        print('curl -X POST "http://localhost:8000/transcribe" \\')
        print('  -H "Content-Type: application/json" \\')
        print("  -d '{")
        print('    "google_drive_link": "YOUR_FOLDER_LINK",')
        print('    "recursive": true')
        print("  }'")
    else:
        print_warning("Configuration incomplete")
        print()
        print("Please set these in your .env file:")
        if not settings.GEMINI_KEY:
            print(f"  - GEMINI_KEY")
        if not settings.GOOGLE_DRIVE_API_KEY:
            print(f"  - GOOGLE_DRIVE_API_KEY (can use same as GEMINI_KEY)")

except Exception as e:
    print_error(f"Could not load settings: {e}")
    print()
    print("Make sure your .env file is properly configured")

print()
print("For detailed setup instructions, see: SIMPLE_SETUP.md")
print()
