#!/bin/bash
# Cleanup Script - Remove unnecessary files and folders for deployment

echo "🧹 Cleaning up project for deployment..."

# Remove virtual environments (they'll be recreated)
echo "Removing virtual environments..."
rm -rf appenv/
rm -rf audenv/
rm -rf venv/
rm -rf vendor/

# Remove Python cache
echo "Removing Python cache..."
rm -rf __pycache__/
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# Remove unnecessary documentation (keep only essential ones)
echo "Removing redundant documentation..."
rm -f MIGRATION_GUIDE.md
rm -f SIMPLE_SETUP.md
rm -f TRANSCRIPT_FORMATTING.md
rm -f example_formatted_output.py

# Remove CI/CD files (we'll create new deployment configs)
echo "Removing old CI/CD configs..."
rm -f Jenkinsfile-prod
rm -f Jenkinsfile-sandbox
rm -f sonar-project.properties

# Remove test downloads and transcriptions (save space)
echo "Removing test data..."
rm -rf audio_downloads/*
rm -rf transcriptions/*

# Remove .claude directory
echo "Removing .claude directory..."
rm -rf .claude/

# Keep .env.example but remove actual .env (for security)
echo "Note: Keep your .env file secure, don't commit it!"

echo "✅ Cleanup complete!"
echo ""
echo "Remaining structure:"
ls -la
