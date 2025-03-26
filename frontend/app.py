import os
import cv2
import numpy as np
from flask import Flask, Response, jsonify, request, session
from flask_cors import CORS
import tensorflow as tf
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime, timedelta
import uuid
import json


app = Flask(__name__)
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_HTTPONLY=True
)

CORS(app, 
     supports_credentials=True,
     resources={
         r"/*": {
             "origins": [
                "http://localhost:5173",  # Local development
                "https://emotion-detector-git-main-johan-ahmeds-projects.vercel.app",  # Vercel deployment
                "https://emotion-detector.vercel.app",  # Add your Vercel domain
                "https://your-app-name.vercel.app"  # Replace with your actual Vercel domain
             ],
             "methods": ["GET", "POST", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "expose_headers": ["Content-Type"],
             "supports_credentials": True,
             "max_age": 3600
         }
     })


USERS_CSV = 'data/users.csv'
EMOTIONS_CSV = 'data/emotions.csv'


os.makedirs('data', exist_ok=True)


if not os.path.exists(USERS_CSV):
    pd.DataFrame(columns=['email', 'password']).to_csv(USERS_CSV, index=False)
if not os.path.exists(EMOTIONS_CSV):
    pd.DataFrame(columns=['email', 'timestamp', 'emotion', 'confidence', 'model_type', 'session_id']).to_csv(EMOTIONS_CSV, index=False)


model = None
face_cascade = None
emotion_labels = ['anger', 'contempt', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
active_sessions = {}
active_cameras = {}

def load_model_file(model_path):
    global model, face_cascade
    try:
        
        if not os.path.exists(model_path):
            print(f"Model file not found at: {model_path}")
            return False
            
        
        model = tf.keras.models.load_model(model_path, compile=False)
        
        model.compile(
            optimizer='rmsprop',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        if face_cascade.empty():
            print("Error: Could not load face cascade classifier")
            return False
            
        return True
        
    except Exception as e:
        print(f"Error loading model: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def save_emotion(email, emotion, confidence, model_type, session_id=None):
    try:
        timestamp = datetime.now()
        new_data = {
            'email': email,
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'emotion': emotion,
            'confidence': confidence,
            'model_type': model_type,
            'session_id': session_id
        }
        
        # Add to active session if session_id provided
        if session_id and session_id in active_sessions:
            active_sessions[session_id]['emotions'].append({
                **new_data,
                'timestamp': timestamp
            })
        
        # Save to CSV
        try:
            df = pd.read_csv(EMOTIONS_CSV)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            df.to_csv(EMOTIONS_CSV, index=False)
        except Exception as e:
            print(f"Error saving to CSV: {str(e)}")
            
    except Exception as e:
        print(f"Error saving emotion: {str(e)}")
        import traceback
        traceback.print_exc()
        
        
def process_frame(frame, email, model_type, session_id):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5, minSize=(50, 50))
    
    for (x, y, w, h) in faces:
        face = frame[y:y + h, x:x + w]
        face = cv2.resize(face, (96, 96))
        face = face / 255.0
        face = np.expand_dims(face, axis=0)
        face = np.expand_dims(face, axis=0)
        
        prediction = model.predict(face)
        emotion_idx = np.argmax(prediction)
        emotion = emotion_labels[emotion_idx]
        confidence = float(prediction[0][emotion_idx])
        
        
        save_emotion(email, emotion, confidence, model_type, session_id)
        
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        label = f"{emotion} ({confidence:.2f})"
        cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    return frame

def generate_frames(email, model_type, session_id):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not start camera.")
    
    active_cameras[session_id] = cap
    
    while session_id in active_sessions:  # Check if session is still active
        success, frame = cap.read()
        if not success:
            break
        
        try:
            processed_frame = process_frame(frame, email, model_type, session_id)
            _, buffer = cv2.imencode('.jpg', processed_frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                   
        except Exception as e:
            print(f"Error processing frame: {str(e)}")
            continue
    
    # Clean up camera when done
    if cap and cap.isOpened():
        cap.release()

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
            
        df = pd.read_csv(USERS_CSV)
        if email in df['email'].values:
            return jsonify({"error": "User already exists"}), 400
            
        hashed_password = generate_password_hash(password)
        new_user = pd.DataFrame([{'email': email, 'password': hashed_password}])
        df = pd.concat([df, new_user], ignore_index=True)
        df.to_csv(USERS_CSV, index=False)
        
        session['user'] = email
        return jsonify({"status": "success", "email": email})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"error": "Email and password are required"}), 400
            
        df = pd.read_csv(USERS_CSV)
        user = df[df['email'] == email]
        
        if user.empty or not check_password_hash(user.iloc[0]['password'], password):
            return jsonify({"error": "Invalid credentials"}), 401
            
        session['user'] = email
        return jsonify({"status": "success", "email": email})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analytics', methods=['GET'])
def get_analytics():
    if not session.get('user'):
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        email = session['user']
        
        # Check if file exists and is not empty
        if not os.path.exists(EMOTIONS_CSV) or os.stat(EMOTIONS_CSV).st_size == 0:
            return jsonify({
                "sessionHistory": [],
                "emotionsByTime": [],
                "emotionsByModel": [],
                "emotionTrends": []
            })
            
        df = pd.read_csv(EMOTIONS_CSV)
        user_data = df[df['email'] == email]
        
        if user_data.empty:
            return jsonify({
                "sessionHistory": [],
                "emotionsByTime": [],
                "emotionsByModel": [],
                "emotionTrends": []
            })

        # Process each session separately
        session_summaries = []
        for session_id in user_data['session_id'].unique():
            session_data = user_data[user_data['session_id'] == session_id]
            
            # Calculate emotion counts
            emotion_counts = session_data['emotion'].value_counts().to_dict()
            total_emotions = len(session_data)
            
            # Calculate percentages
            emotion_percentages = {
                emotion: round((count / total_emotions * 100), 2)
                for emotion, count in emotion_counts.items()
            }
            
            session_summaries.append({
                'sessionId': session_id,
                'startTime': session_data['timestamp'].min(),
                'endTime': session_data['timestamp'].max(),
                'duration': round((pd.to_datetime(session_data['timestamp'].max()) - 
                                pd.to_datetime(session_data['timestamp'].min())).total_seconds() / 60, 2),
                'modelType': session_data['model_type'].iloc[0],
                'dominantEmotion': max(emotion_counts.items(), key=lambda x: x[1])[0],
                'totalDetections': total_emotions,
                'emotionBreakdown': emotion_counts,
                'emotionPercentages': emotion_percentages
            })
        
        # Sort sessions by start time, most recent first
        session_summaries.sort(key=lambda x: x['startTime'], reverse=True)
        
        return jsonify({
            "sessionHistory": session_summaries,
            "emotionsByTime": user_data.groupby(['timestamp', 'emotion'])
                .size()
                .reset_index(name='count')
                .to_dict('records'),
            "emotionsByModel": user_data.groupby(['model_type', 'emotion'])
                .size()
                .reset_index(name='count')
                .to_dict('records'),
            "emotionTrends": []  # Add empty trends array as default
        })
        
    except Exception as e:
        print(f"Analytics Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
    
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user', None)
    return jsonify({"status": "success"})

@app.route('/check-auth')
def check_auth():
    user = session.get('user')
    if user:
        return jsonify({"status": "authenticated", "email": user})
    return jsonify({"status": "unauthenticated"}), 401

@app.route('/')
def index():
    return jsonify({"status": "running"})

@app.route('/load-model', methods=['POST'])
def load_model_endpoint():
    if not session.get('user'):
        return jsonify({"error": "Unauthorized"}), 401
        
    try:
        data = request.get_json()
        model_path = data.get('modelPath')
        
        print(f"Attempting to load model from: {model_path}")  
        print(f"Current working directory: {os.getcwd()}")     
        
        if not model_path:
            return jsonify({"error": "Model path not provided"}), 400
            
        success = load_model_file(model_path)
        
        if success:
            return jsonify({"status": "Model loaded successfully"})
        else:
            return jsonify({"error": "model"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/video_feed')
def video_feed():
    if not session.get('user'):
        return jsonify({"error": "Unauthorized"}), 401
    
    session_id = request.args.get('session_id')
    if not session_id or session_id not in active_sessions:
        return jsonify({"error": "Invalid session"}), 400
    
    email = session['user']
    model_type = request.args.get('model_type', 'unknown')
    
    response = Response(
        generate_frames(email, model_type, session_id),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/start-session', methods=['POST'])
def start_session():
    if not session.get('user'):
        return jsonify({"error": "Unauthorized"}), 401
    
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = {
        "user": session["user"],
        "start_time": datetime.now(),
        "emotions": []
    }
    
    return jsonify({"sessionId": session_id})

@app.route('/stop-session', methods=['POST'])
def stop_session():
    data = request.get_json()
    session_id = data.get("sessionId")

    if not session_id or session_id not in active_sessions:
        return jsonify({"error": "Invalid session"}), 400

    session_data = active_sessions[session_id]
    duration = (datetime.now() - session_data['start_time']).total_seconds() / 60

    # Calculate session statistics
    emotions = [e['emotion'] for e in session_data['emotions']]
    emotion_counts = {}
    for emotion in emotions:
        emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
    
    dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0] if emotion_counts else None

    # Calculate percentages for each emotion
    total_emotions = len(emotions)
    emotion_percentages = {
        emotion: (count / total_emotions * 100) if total_emotions > 0 else 0 
        for emotion, count in emotion_counts.items()
    }

    report = {
        "duration": round(duration, 2),
        "dominantEmotion": dominant_emotion,
        "totalDetections": total_emotions,
        "emotionBreakdown": emotion_counts,
        "emotionPercentages": {
            emotion: round(percentage, 2) 
            for emotion, percentage in emotion_percentages.items()
        }
    }

    # Clean up camera if it exists
    if session_id in active_cameras:
        cap = active_cameras[session_id]
        if cap and cap.isOpened():
            cap.release()
        del active_cameras[session_id]

    # Clean up session
    del active_sessions[session_id]

    return jsonify(report)

@app.after_request
def after_request(response):
    # Get the origin from the request
    origin = request.headers.get('Origin')
    allowed_origins = [
        "http://localhost:5173",
        "https://emotion-detector-git-main-johan-ahmeds-projects.vercel.app",
        "https://emotion-detector.vercel.app",
        "https://your-app-name.vercel.app"  # Replace with your actual Vercel domain
    ]
    
    if origin in allowed_origins:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    
    return response

@app.route('/status')
def status():
    return jsonify({"status": "running"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)