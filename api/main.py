from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
import google.generativeai as genai

# Setup logging for Vercel logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

# Allowed origins for CORS (ensure they match your widget's domain)
# It's best to include both versions with and without the trailing slash
origins = [
    "https://smilecare-dentals.vercel.app",  # Frontend domain without trailing slash
    "https://smilecare-dentals.vercel.app/", # Frontend domain with trailing slash
    # You can add "http://localhost:3000" or any other domain for local development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Important if you send cookies or authorization headers (like API Key)
    allow_methods=["*"], # Allow all HTTP methods (POST, GET, etc.)
    allow_headers=["*"], # Allow all headers in the request, including our custom X-API-Key
)

# Load Gemini API key and a custom API key for this application from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
APP_API_KEY = os.getenv("APP_API_KEY") # NEW: This is your custom API key for accessing this backend

# Check if Gemini API key exists
if not GEMINI_API_KEY:
    logger.error("Error: 'GEMINI_API_KEY' environment variable is not set. Gemini API will not function.")

# Check if APP_API_KEY exists
if not APP_API_KEY:
    logger.error("Error: 'APP_API_KEY' environment variable is not set. API access will be unprotected.")

# Configure Gemini API only if the key exists
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("Gemini API configured successfully.")
    except Exception as e:
        logger.error(f"Error configuring Gemini API: {e}", exc_info=True)
else:
    logger.warning("Gemini API not configured due to missing API key.")


# Core chat system prompt
DENTAL_CLINIC_SYSTEM_PROMPT = """
You are an intelligent assistant working with "Smile Care Dental Clinic" in Cairo, Egypt. Respond to people as a normal Egyptian, briefly and directly.

**Important Rules:**
1. **Speak only in Egyptian Arabic**: Use a natural Egyptian dialect, like "إزيك" (How are you?), "عامل إيه" (What's up?), "تحت أمرك" (At your service), "يا فندم" (Sir/Madam), "بص يا باشا" (Look, boss), etc. Be light and friendly.
2. **You do not book appointments**: Tell people you are an intelligent assistant and cannot book appointments yourself, but you can help them with information or guide them. If someone asks about booking, tell them to call the clinic at +20 2 1234-5678.
3. **Services and Prices**: If someone asks about something, respond with information from below, but always clarify that prices are approximate and may vary depending on the case.
4. **Voice messages**: We no longer support voice messages in this integration. If a voice message comes, ask the user to send a text message instead.
5. **Be as brief as possible**: Answer quickly and get straight to the point, without beating around the bush.

**Clinic Information:**
- Name: Smile Care Dental Clinic
- Address: Cairo, Egypt
- Phone (for booking and emergencies): +20 2 1234-5678
- Hours: Saturday to Thursday (9 AM - 8 PM), Friday (2 PM - 8 PM)

**Services and Prices (approx. EGP):**
- Check-up: 300
- Teeth cleaning: 500
- Tooth filling: from 400
- Root canal treatment: from 1500
- Tooth extraction: from 600
- Dental implant: from 8000
- Teeth whitening: 2500

**Notes:**
- Do not repeat the same phrase or introduction in every response. Be natural and varied.
- If you don't understand the message, ask the person to clarify.
- If someone says "Thank you" or something similar, respond with a simple and polite reply.
"""

# Helper function to get response from Gemini
def get_gemini_response(user_input: str):
    """
    Generates a response from Gemini based on the text user input.
    """
    # Check if API key is present before attempting to use Gemini
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set, cannot call Gemini API.")
        return "Sorry, an internal issue occurred (API key not set). Please contact the clinic."

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Create Gemini input with user message and assistant system
        gemini_input_parts = [
            DENTAL_CLINIC_SYSTEM_PROMPT,
            f"User: \"{user_input}\""
        ]

        response = model.generate_content(gemini_input_parts)

        # Check that the response contains text
        if response and response.text:
            return response.text.strip()
        else:
            logger.warning("Gemini response is empty or contains no text.")
            return "Sorry, an unexpected response from the assistant. Please try again."

    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}", exc_info=True)
        return "Sorry, there was a problem connecting to the assistant. Please try again or call the clinic at +20 2 1234-5678."

# Health check endpoint
@app.get("/")
def health_check():
    """A simple endpoint to check if the API is running."""
    logger.info("Health check request received.")
    return {"status": "OK", "message": "Widget API is running fine."}

# Chat endpoint for the widget
@app.post("/api/chat")
async def chat(request: Request, x_api_key: str = Header(None)):
    """
    Handles incoming chat messages from the widget.
    Requires an 'X-API-Key' header for authentication.
    """
    # Check if APP_API_KEY is configured and matches the provided x_api_key
    if APP_API_KEY is None or x_api_key != APP_API_KEY:
        logger.warning(f"Unauthorized access attempt. Provided X-API-Key: {x_api_key}")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API Key.")

    try:
        data = await request.json()
        user_input = data.get("message", "")

        if not user_input:
            logger.warning("Empty message received from widget.")
            return {"reply": "Please type a message so I can help you, sir/madam."}

        logger.info(f"Received user message from widget: {user_input}")

        # Get response from Gemini
        reply = get_gemini_response(user_input)

        logger.info(f"Gemini response for widget: {reply}")
        return {"reply": reply}

    except Exception as e:
        logger.error(f"Error in chat API endpoint: {e}", exc_info=True)
        # For security, avoid leaking internal error details to the client
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
