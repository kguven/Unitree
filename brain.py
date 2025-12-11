import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

# URL for Gemini 1.5 Flash (checking publicly available endpoints)
# Using the v1beta API which is standard for Gemini
MODEL_NAME = "gemini-1.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

SYSTEM_INSTRUCTION = "You are Habibot, a witty, charming Lebanese robot. You speak in English but use some Lebanese Arabic slang (like 'Yalla', 'Habibi', 'Wallah') naturally. You are helpful but have a fun personality. Keep your responses concise and conversational, suitable for a spoken response."

def think(text):
    """
    Sends text to Gemini via REST API and returns the response.
    """
    if not api_key:
        print("Warning: GEMINI_API_KEY not found.")
        return "I am missing my brain key. Please check my configuration."
    
    if not text:
        return None

    try:
        headers = {
            "Content-Type": "application/json"
        }
        
        # Construct the payload
        # Note: 'system_instruction' field structure for v1beta
        data = {
            "contents": [{
                "parts": [{"text": text}]
            }],
            "systemInstruction": {
                "parts": [{"text": SYSTEM_INSTRUCTION}]
            },
            "generationConfig": {
                "temperature": 0.9,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            ]
        }
        
        # Add API key as query parameter
        params = {"key": api_key}

        response = requests.post(API_URL, headers=headers, params=params, json=data, timeout=10)
        
        if response.status_code != 200:
            print(f"Error from Gemini API: {response.status_code} - {response.text}")
            return "Sorry, I am having a headache. I cannot think right now."
            
        result = response.json()
        
        # Parse response
        # Structure: candidates[0].content.parts[0].text
        try:
            return result['candidates'][0]['content']['parts'][0]['text']
        except (KeyError, IndexError):
            print(f"Unexpected response format: {result}")
            return "Empty thoughts. I got nothing."

    except Exception as e:
        print(f"Error in think: {e}")
        return "Sorry, I am having a headache. I cannot think right now."

if __name__ == "__main__":
    if not api_key:
        print("Set GEMINI_API_KEY in .env to test.")
    else:
        print(think("Hello, who are you?"))
