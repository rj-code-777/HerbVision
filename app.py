from flask import request, session, jsonify
from transformers import AutoImageProcessor, AutoModelForImageClassification
from flask import Flask, request, jsonify, render_template, session
import google.generativeai as genai
from PIL import Image
import numpy as np
import tensorflow as tf
from datetime import datetime
import bcrypt
from flask_pymongo import PyMongo
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import os
import torch
import smtplib
import random
from email_validator import validate_email, EmailNotValidError
from flask import Flask, request, jsonify, session
from datetime import datetime, timedelta
from transformers import AutoImageProcessor, AutoModelForImageClassification
# Initialize the Flask app
app = Flask(__name__)
# Allow all origins
CORS(app, resources={r"/*": {"origins": "*"}})

# Load model directly
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'Your api key'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=10)


@app.route('/send_otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')

    try:
        # Validate email format
        validate_email(email)
    except EmailNotValidError as e:
        return jsonify({"error": str(e)}), 400

    otp = random.randint(100000, 999999)  # Generate 6-digit OTP
    session['otp'] = otp  # Store OTP in session
    session['otp_email'] = email

    # Send OTP via email
    try:
        # Replace these with your actual email settings
        sender_email = "senders email id"
        sender_password = "password"
        with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
            smtp.starttls()
            smtp.login(sender_email, sender_password)
            message = f"Subject: Your OTP\n\nYour OTP is {
                otp}. It will expire in 10 minutes."
            smtp.sendmail(sender_email, email, message)
        return jsonify({"message": "OTP sent successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to send OTP", "details": str(e)}), 500

# Endpoint for verifying OTP


@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    data = request.json
    email = data.get('email')
    otp = data.get('otp')

    # Debug print statements to verify session values
    print(f"Session Email: {session.get('otp_email')}")
    print(f"Session OTP: {session.get('otp')}")
    print(f"Received Email: {email}")
    print(f"Received OTP: {otp}")

    # Check for type consistency in OTP comparison
    if session.get('otp_email') != email or session.get('otp') != int(otp):
        return jsonify({"error": "Invalid OTP or email"}), 401

    # OTP verified, proceed with signup
    session.pop('otp', None)  # Clear OTP from session
    return jsonify({"message": "OTP verified successfully"}), 200


@app.after_request
def add_cors_headers(response):
    response.headers.add("Access-Control-Allow-Origin",
                         "http://localhost:5000")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
    return response


def classify_image(image):
    # Load the image processor and model
    processor = AutoImageProcessor.from_pretrained(
        "rjain2002/ayurAI")
    model = AutoModelForImageClassification.from_pretrained(
        "rjain2002/ayurAI")

    # Preprocess the image and make predictions
    inputs = processor(images=image, return_tensors="pt")
    outputs = model(**inputs)

    # Get the predicted class index
    predicted_class_idx = outputs.logits.argmax(-1).item()

    return predicted_class_idx


# MongoDB Configuration
# Replace with your MongoDB URI
app.config["MONGO_URI"] = "mongodb://127.0.0.1:27017/HerbalData"
mongo = PyMongo(app)
db = mongo.db
chat_history_collection = db['chatbot_conversations']

# Initialize Gemini Model for Chatbot
# genai.configure(api_key="AIzaSyBzQlSdL16f4xy16BvqSnfe2OUINYINYVA")
# chat_model = genai.GenerativeModel("gemini-1.5-flash")

# Load pre-trained ML model for plant identification (example using TensorFlow)
# Replace with your model path
# model = load_model(
#     'C:/Users/HP/OneDrive/Desktop/final/final/model_avg_25.h5', custom_objects=custom_objects)

# Replace with your actual plant labels

# Rate Limiting Configuration
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per hour", "10 per minute"]  # Adjust as needed
)

# Endpoint 1: User Signup


@app.route('/', methods=['GET'])
def index():
    # You can handle POST requests here if needed
    return render_template('home.html')


@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    # Ensure the OTP was verified
    if session.get('otp_email') != email:
        return jsonify({"error": "Please verify OTP before signing up"}), 403

    # Continue with existing signup code...
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long"}), 400

    user = db.users.find_one({"email": email})
    if user:
        return jsonify({"error": "User already exists"}), 409

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    db.users.insert_one({
        "email": email,
        "password": hashed_pw,
        "is_verified": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    return jsonify({"message": "User created successfully"}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    user = db.users.find_one({"email": email})
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({"message": "Login successful"}), 200


# Endpoint 3: Chatbot Endpoint


api_key = "Chatbot api key"


def generate_text(prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"An error occurred: {e}")
        return "An error occurred. Please try again."

# Route to render chatbot page


@app.route('/chatbot', methods=['GET'])
def chat():
    return render_template('chatbot.html')

# Existing chatbot endpoint with modified response generation


@app.route('/chatbot', methods=['POST'])
@limiter.limit("5 per minute")
def chatbot():
    data = request.json
    email = data.get('email')
    message = data.get('message')
    plant_name = data.get('plantName')
    conversation = session.get('conversation', [])
    # If the message is empty or initial, provide a greeting or introduction
    if not message:
        initial_response = f"Hello! I’m here to help you with information about '{
            plant_name}'. Ask me anything about it!"
        prompt = prompt = (
            f"You are an expert botanist. You are conversing with a user about the plant '{
                plant_name}'. "
            f"Now, respond to the user by giving details about the '{
                plant_name}' its species and its properties give the output in a well structured format make the headings bold only provide 3 main properties"
        )
        response_text1 = generate_text(prompt)
        return jsonify({"message": response_text1})

    # Initialize conversation history if not present in session
    conversation = session.get('conversation', [])
    conversation.append(f"User: {message}")
    session['conversation'] = conversation

    # Build the prompt with conversation history and plant context
    prompt = (
        f"You are an expert botanist. You are conversing with a user about the plant '{
            plant_name}'. "
        f"Here's the conversation history: {'next=>'.join(conversation)} "
        f"Now, respond to the user's latest query: {message}"
    )

    response_text = generate_text(prompt)

    # Add AI response to conversation history
    conversation.append(f"Bot: {response_text}")
    session['conversation'] = conversation

    # Log conversation in MongoDB
    chat_history_collection.update_one(
        {'email': email},
        {'$push': {
            'conversations': {
                'user_message': message,
                'chatbot_response': response_text,
                'timestamp': datetime.utcnow()
            }
        }},
        upsert=True
    )

    return jsonify({"message": response_text})

# Endpoint 4: Image Processing for Plant Identification


@app.route('/index', methods=['GET'])
def getidentify():
    return render_template('index.html')


@app.route('/identify_plant', methods=['POST'])
def process_image():
    if request.method == 'OPTIONS':
        # CORS preflight response
        response = jsonify({"message": "Preflight response"})
        response.headers.add("Access-Control-Allow-Origin",
                             "http://localhost:5000")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response, 200

    if 'image' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    image = request.files['image']

    # Save the uploaded image temporarily
    temp_image_path = os.path.join(
        app.config['UPLOAD_FOLDER'], "temp_plant_image.jpg")
    image.save(temp_image_path)

    # Call the Python script for plant identification
    labels_list = [
        'Amla', 'Curry', 'Betel', 'Bamboo', 'Palak(Spinach)', 'Coriander', 'Ashoka', 'Seethapala', 'Lemongrass', 'Papaya',
        'Curry Leaf', 'Lemon', 'Noni', 'Henna', 'Mango', 'Doddapatre', 'Amruta Balli', 'Betel Nut', 'Tulsi', 'Pomegranate',
        'Castor', 'Jackfruit', 'Insulin', 'Pepper', 'Raktachandini', 'Aloevera', 'Jasmine', 'Doddapatre', 'Neem',
        'Geranium', 'Rose', 'Guava', 'Hibiscus', 'Nithyapushpa', 'Wood Sorel', 'Tamarind', 'Guava', 'Brahmi', 'Sapota',
        'Basale', 'Avocado', 'Ashwagandha', 'Nagadali', 'Arali', 'Ekka', 'Ganike', 'Tulasi', 'Honge', 'Mint',
        'Catharanthus', 'Papaya', 'Brahmi'
    ]


# Example usage
# Load an image file (this can be any PIL image)
    image_input = Image.open(temp_image_path)
    result = labels_list[classify_image(image_input)]

    return jsonify({"identificationResult": result})


if __name__ == '__main__':
    app.run(debug=True)
