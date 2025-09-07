#!/usr/bin/env python3
"""
MinStory - AI Short Film Generator
Streamlit Application Launcher
"""

import os
import sys
import subprocess
from pathlib import Path

def check_requirements():
    """Check if required packages are installed"""
    try:
        import streamlit
        import openai
        import google.generativeai
        import pydantic
        import PIL
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("Please install requirements: pip install -r requirements_streamlit.txt")
        return False

def check_env_file():
    """Check if environment file exists"""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  .env file not found")
        print("Please copy config.env.example to .env and add your API keys")
        return False
    print("✅ Environment file found")
    return True

def main():
    """Main launcher function"""
    print("🎬 MinStory - AI Short Film Generator")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check environment
    if not check_env_file():
        print("\nTo create .env file:")
        print("1. Copy config.env.example to .env")
        print("2. Add your API keys")
        print("3. Run this script again")
        sys.exit(1)
    
    # Launch Streamlit
    print("\n🚀 Starting Streamlit application...")
    print("The app will open in your default browser")
    print("Press Ctrl+C to stop the application")
    print("-" * 50)
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

