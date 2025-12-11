import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Warning: GEMINI_API_KEY not found in .env")

# Configure Gemini
if api_key:
    genai.configure(api_key=api_key)

# Define the model and system prompt
# Note: System instructions are supported in newer models/SDK versions.
# If using a basic model, we might need to prepend the prompt.
generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
]

model = genai.GenerativeModel(model_name="gemini-2.5-flash",
                              generation_config=generation_config,
                              safety_settings=safety_settings,
                              system_instruction="You are Habibot, a witty, charming Lebanese robot. You speak in English but use some Lebanese Arabic slang (like 'Yalla', 'Habibi', 'Wallah') naturally. You are helpful but have a fun personality. Keep your responses concise and conversational, suitable for a spoken response.")

def think(text):
    """
    Sends text to Gemini and returns the response.
    """
    if not api_key:
        return "I am missing my brain key. Please check my configuration."
    
    if not text:
        return None

    try:
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(text)
        return response.text
    except Exception as e:
        print(f"Error in think: {e}")
        return "Sorry, I am having a headache. I cannot think right now."

if __name__ == "__main__":
    # Test the think function
    print(think("Hello, who are you?"))
