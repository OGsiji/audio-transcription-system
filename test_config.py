#!/usr/bin/env python3
"""
Quick test to verify configuration loads correctly
"""

import os
import sys

# Test 1: Import settings without GEMINI_KEY (should work)
print("Test 1: Import settings module...")
try:
    from src.config.settings import settings
    print("✅ Settings imported successfully")
    print(f"   Environment: {settings.NODE_ENV}")
    print(f"   GEMINI_KEY set: {settings.GEMINI_KEY is not None}")
except Exception as e:
    print(f"❌ Failed to import settings: {e}")
    sys.exit(1)

# Test 2: Validate required fields (should fail if no GEMINI_KEY)
print("\nTest 2: Validate required fields...")
try:
    settings.validate_required_fields()
    print("✅ Validation passed - GEMINI_KEY is set")
except ValueError as e:
    print(f"⚠️  Validation failed (expected if GEMINI_KEY not set):")
    print(f"   {str(e)}")
    print("\n💡 Set GEMINI_KEY environment variable to fix this")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)

# Test 3: Check New Relic import
print("\nTest 3: New Relic availability...")
from src.config.settings import NEW_RELIC_AVAILABLE
print(f"   New Relic available: {NEW_RELIC_AVAILABLE}")
if NEW_RELIC_AVAILABLE:
    print("   (New Relic monitoring enabled)")
else:
    print("   (New Relic not installed - this is fine!)")

print("\n" + "="*60)
print("Configuration test complete!")
print("="*60)

# Summary
if settings.GEMINI_KEY:
    print("\n✅ All checks passed! Ready to start the service.")
else:
    print("\n⚠️  To start the service, set GEMINI_KEY:")
    print("   export GEMINI_KEY=your_api_key")
    print("   or add it to your .env file")
