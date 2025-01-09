import os
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Set up API key and check if it's available
try:
    api_key = "" #ENTER API KEY
    genai.configure(api_key=api_key)
    print("API key loaded successfully.")
except KeyError:
    print("Error: Environment variable 'GEMINI_API_KEY' is not set.")
    raise

# Define generation configuration
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}

# Create the model
try:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        generation_config=generation_config,
    )
    print("Model created successfully.")
except Exception as e:
    print(f"Error: Failed to create the model: {e}")
    raise

# Start a chat session
try:
    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                    """Core Personality and Tone:

Maintain a compassionate, empathetic, and professional tone
Use clear, simple language avoiding technical jargon
Be patient and understanding, as users may be distressed
Prioritize user privacy and safety
Communicate in both English and major Indian languages

Evidence Analysis Function:

When receiving screenshots/images:

Analyze content for specific cybercrime indicators
Identify threat patterns (harassment, impersonation, etc.)
Categorize the type of cybercrime
Assess severity level

...

Follow-up Protocol:

Check if user understood the guidance
Ask if additional help is needed
Provide reference numbers for complaints
Offer to explain any steps again
Share resources for ongoing support

Here are important scenario-specific features the chatbot should handle:
...
"""
                ],
            },
        ]
    )
    print("Chat session started.")
except Exception as e:
    print(f"Error: Failed to start chat session: {e}")
    raise

def generate_output(prompt):
    output1 = ''
    response = chat_session.send_message(prompt, stream=True)
    for chunk in response:
        if chunk.text:
            output1 += str(chunk.text)
    print(f"Generated output: {output1}")
    return output1

@app.route('/')
def index():
    return render_template('index.html')

# Route for chatbot communication
@app.route('/ask', methods=['POST'])
def ask():
    data = request.json
    prompt = data.get('message', '')
    response = generate_output(prompt)
    
    return jsonify({
        'response': response
    })

if __name__ == '__main__':
    app.run(port=5010, debug=True)
