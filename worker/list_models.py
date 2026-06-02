import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
load_dotenv("../.env")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing Gemini models: {e}")
