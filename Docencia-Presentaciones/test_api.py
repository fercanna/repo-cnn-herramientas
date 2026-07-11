
import os
from dotenv import load_dotenv
import google.genai as genai
import sys

print(f"Python version: {sys.version}")
print(f"google-genai version: {genai.__version__}")

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("API Key not found in .env file")
else:
    print("API Key found. Attempting to configure...")
    try:
        genai.configure(api_key=api_key)
        print("✅ Configuration successful!")
    except Exception as e:
        print(f"❌ An error occurred during configuration: {e}")
