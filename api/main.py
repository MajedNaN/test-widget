from fastapi import FastAPI, Request, Header, HTTPException
import logging
import asyncio
from functools import partial

# FastAPI app
app = FastAPI()

# Logging setup
logger = logging.getLogger("uvicorn")
logger.setLevel(logging.INFO)

# Your Gemini model client should be defined and authenticated earlier
# For example:
# from google.generativeai import GenerativeModel
# model = GenerativeModel(...)

# Config (example API key for demonstration)
APP_API_KEY = "your_secure_api_key_here"

# Async wrapper for Gemini call
async def get_gemini_response(user_input: str) -> str:
    try:
        gemini_input_parts = [
            {"role": "user", "parts": [{"text": user_input}]}
        ]

        # Run the blocking Gemini call in a thread to avoid blocking event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            partial(model.generate_content, gemini_input_parts)
        )

        if response and hasattr(response, "text") and response.text:
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
    logger.info("Health check request received.")
    return {"status": "OK", "message": "Widget API is running fine."}

# Chat endpoint
@app.post("/api/chat")
async def chat(request: Request, x_api_key: str = Header(None)):
    """
    Handles incoming chat messages from the widget.
    Requires an 'X-API-Key' header for authentication.
    """
    if APP_API_KEY is None or x_api_key != APP_API_KEY:
        logger.warning(f"Unauthorized access attempt. Provided X-API-Key: {x_api_key}")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API Key.")

    try:
        data = await request.json()
        user_input = data.get("message", "").strip()

        if not user_input:
            logger.warning("Empty message received from widget.")
            return {"reply": "Please type a message so I can help you, sir/madam."}

        logger.info(f"Received user message from widget: {user_input}")

        # Get Gemini response (non-blocking)
        reply = await get_gemini_response(user_input)

        logger.info(f"Gemini response for widget: {reply}")
        return {"reply": reply}

    except Exception as e:
        logger.error(f"Error in chat API endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
