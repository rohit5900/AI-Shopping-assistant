from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
import os
import logging
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from functools import wraps
import base64
import google.generativeai as genai
import hashlib
import re
from werkzeug.utils import secure_filename
import uuid

# Load environment variables
load_dotenv()

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, 
    static_url_path='',
    static_folder='static',
    template_folder='templates'
)
app.secret_key = os.getenv("SECRET_KEY", os.urandom(24))
CORS(app)  # Allow all origins in development

# Configure file upload settings
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['ALLOWED_MIMETYPES'] = {'image/jpeg', 'image/png', 'image/gif'}

# Development-friendly settings
if os.getenv("FLASK_ENV") == "development":
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['DEBUG'] = True
else:
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['DEBUG'] = False

app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configure rate limiting with more granular limits
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["30 per minute", "100 per hour"],
    storage_uri=os.getenv("REDIS_URL", "memory://")
)

# Configure caching with Redis if available, otherwise use simple in-memory cache
cache_config = {
    'CACHE_TYPE': os.getenv("CACHE_TYPE", "simple"),
    'CACHE_DEFAULT_TIMEOUT': int(os.getenv("CACHE_TIMEOUT", "300")),
    'CACHE_KEY_PREFIX': 'shopping_assistant_'
}

if os.getenv("REDIS_URL"):
    cache_config['CACHE_REDIS_URL'] = os.getenv("REDIS_URL")

cache = Cache(app, config=cache_config)

# Configure Gemini with your API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    logger.error("GEMINI_API_KEY not found in environment variables")
    raise ValueError("GEMINI_API_KEY is required")

genai.configure(api_key=GEMINI_API_KEY)

# Initialize the model with the latest version
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("Successfully initialized Gemini model")
except Exception as e:
    logger.error(f"Failed to initialize Gemini model: {str(e)}")
    raise

# Enhanced shopping prompt template with strict requirements
SHOPPING_PROMPT = """You are a professional shopping assistant. For any product query:

REQUIRED RESPONSE FORMAT:
1. Product Category: [category name]
2. Top 3 Recommendations:
   - [Brand] [Model] | Price: [$X-$Y] | Features: [3 key features] | Buy at: [store1, store2]
   - [Brand] [Model] | Price: [$X-$Y] | Features: [3 key features] | Buy at: [store1, store2]
   - [Brand] [Model] | Price: [$X-$Y] | Features: [3 key features] | Buy at: [store1, store2]
3. Shopping Tips: [brief advice]

EXAMPLE RESPONSE FOR "ORGANIC COTTON SHEETS":
1. Product Category: Bed Sheets
2. Top 3 Recommendations:
   - Boll & Branch Signature Hemmed | Price: $229-$279 | Features: 100% organic cotton, 300 thread count, Oeko-Tex certified | Buy at: [bollandbranch.com, Amazon]
   - Brooklinen Luxe Core Sheet Set | Price: $199-$249 | Features: Long-staple organic cotton, 480 thread count, 30-day trial | Buy at: [brooklinen.com]
   - Target Threshold Organic Cotton | Price: $49-$79 | Features: Affordable organic option, 200 thread count, multiple colors | Buy at: [Target stores, target.com]
3. Shopping Tips: Look for GOTS certification for true organic cotton.

Now respond to this query: {query}"""

# Image processing prompt template
IMAGE_PROMPT = """You are a shopping list analyzer. Analyze the image and extract all shopping items. 
Return the items as a JSON array of strings. Only include actual shopping items, not headers or other text.
Example response format:
{
    "items": ["milk", "bread", "eggs", "apples"]
}

Now analyze this image:"""

# Error handling decorator with improved logging
def handle_errors(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                "error": "An unexpected error occurred",
                "details": str(e) if os.getenv("FLASK_ENV") == "development" else None,
                "request_id": request.id if hasattr(request, 'id') else None
            }), 500
    return decorated_function

# Track API usage with improved session handling
def track_api_usage():
    if 'api_calls' not in session:
        session['api_calls'] = 0
        session['first_api_call'] = datetime.now().isoformat()
    
    session['api_calls'] += 1
    session['last_api_call'] = datetime.now().isoformat()
    
    # Log usage for analytics
    logger.info(f"API usage tracked: {session['api_calls']} calls, last call: {session['last_api_call']}")

# Security headers with improved CSP
@app.after_request
def add_security_headers(response):
    csp = (
        "default-src 'self';"
        "img-src 'self' data: https:;"
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"
        "font-src 'self' https://fonts.gstatic.com;"
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com;"
        "connect-src 'self';"
    )
    
    if os.getenv("FLASK_ENV") == "development":
        # More permissive CSP for development
        csp = (
            "default-src 'self';"
            "img-src 'self' data: https:;"
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;"
            "font-src 'self' https://fonts.gstatic.com;"
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com;"
            "connect-src 'self';"
        )
    
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

# Improved image validation with content type checking
def validate_image_file(file):
    """Validate image file type and content."""
    if not file:
        return False, "No file provided"
    
    if not file.filename:
        return False, "No filename provided"
    
    # Secure the filename
    filename = secure_filename(file.filename)
    
    # Check file extension
    if not filename.lower().endswith(tuple(app.config['ALLOWED_EXTENSIONS'])):
        return False, f"Invalid file type. Allowed types: {', '.join(app.config['ALLOWED_EXTENSIONS'])}"
    
    # Check MIME type
    if file.content_type not in app.config['ALLOWED_MIMETYPES']:
        return False, f"Invalid file type. Allowed MIME types: {', '.join(app.config['ALLOWED_MIMETYPES'])}"
    
    # Generate a unique filename to prevent overwriting
    unique_filename = f"{uuid.uuid4()}_{filename}"
    
    return True, unique_filename

# Request ID middleware for better tracking
@app.before_request
def before_request():
    request.id = str(uuid.uuid4())
    request.start_time = time.time()
    logger.info(f"Request started: {request.method} {request.path} [ID: {request.id}]")

@app.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        duration = time.time() - request.start_time
        logger.info(f"Request completed: {request.method} {request.path} [ID: {request.id}] - Status: {response.status_code} - Duration: {duration:.2f}s")
    return response

# Add a route to serve static files directly
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

# Add a route to serve the main page
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
@limiter.limit("10 per minute")
@handle_errors
def chat():
    start_time = time.time()
    track_api_usage()
    
    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON data"}), 400
    
    query = data.get('query', '').strip()
    
    if not query:
        return jsonify({"error": "Please enter a valid question"}), 400
    
    # Sanitize input to prevent prompt injection
    query = re.sub(r'[<>]', '', query)
    
    # Check cache first
    cache_key = f"query_{hashlib.md5(query.encode()).hexdigest()}"
    cached_response = cache.get(cache_key)
    if cached_response:
        logger.info(f"Cache hit for query: {query[:30]}...")
        return jsonify({"response": cached_response, "cached": True})
    
    logger.info(f"Processing query: {query[:30]}...")
    
    # Generate response with enhanced configuration
    try:
        response = model.generate_content(
            SHOPPING_PROMPT.format(query=query),
            generation_config={
                "temperature": float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
                "top_p": float(os.getenv("GEMINI_TOP_P", "0.9")),
                "top_k": int(os.getenv("GEMINI_TOP_K", "40")),
                "max_output_tokens": int(os.getenv("GEMINI_MAX_TOKENS", "1000"))
            },
            safety_settings={
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
            }
        )
        
        # Ensure we get text response
        if not response.text:
            raise ValueError("Empty response from Gemini model")
        
        # Cache the response
        cache.set(cache_key, response.text, timeout=int(os.getenv("CACHE_TIMEOUT", "3600")))
        
        # Log performance metrics
        elapsed_time = time.time() - start_time
        logger.info(f"Query processed in {elapsed_time:.2f} seconds")
        
        return jsonify({
            "response": response.text,
            "cached": False,
            "request_id": request.id
        })
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Failed to get shopping recommendations",
            "details": str(e) if os.getenv("FLASK_ENV") == "development" else None,
            "request_id": request.id
        }), 500

@app.route('/api/process-image', methods=['POST'])
@limiter.limit("5 per minute")
@handle_errors
def process_image():
    try:
        if 'image' not in request.files:
            logger.error("No image file in request")
            return jsonify({"error": "No image provided"}), 400
        
        image_file = request.files['image']
        is_valid, result = validate_image_file(image_file)
        
        if not is_valid:
            logger.error(f"Invalid image file: {result}")
            return jsonify({"error": result}), 400
        
        unique_filename = result
        
        # Read the image file
        image_data = image_file.read()
        if not image_data:
            logger.error("Empty image data")
            return jsonify({"error": "Empty image data"}), 400
        
        file_size = len(image_data)
        if file_size > app.config['MAX_CONTENT_LENGTH']:
            logger.error(f"File too large: {file_size} bytes")
            return jsonify({"error": "File size exceeds limit"}), 400
        
        # Save the file for potential future use
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        with open(file_path, 'wb') as f:
            f.write(image_data)
        
        # Log image details
        logger.info(f"Processing image: {unique_filename}, size: {file_size} bytes, type: {image_file.content_type}")
        
        # Create a vision model instance
        vision_model = genai.GenerativeModel('gemini-pro-vision')
        
        # Generate content with the image
        response = vision_model.generate_content([
            IMAGE_PROMPT,
            {"mime_type": image_file.content_type, "data": image_data}
        ])
        
        if not response.text:
            logger.error("Empty response from vision model")
            return jsonify({"error": "Failed to analyze image"}), 500
        
        # Parse the response
        try:
            items = json.loads(response.text)
            if not isinstance(items, dict) or 'items' not in items:
                logger.error(f"Invalid response format: {response.text}")
                raise ValueError("Invalid response format")
            
            logger.info(f"Successfully processed image, found {len(items['items'])} items")
            return jsonify({
                "items": items['items'],
                "request_id": request.id
            })
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error, trying to parse as text: {str(e)}")
            # If the response isn't valid JSON, try to extract items from text
            items = [item.strip() for item in response.text.split('\n') if item.strip()]
            if items:
                logger.info(f"Successfully parsed {len(items)} items from text response")
                return jsonify({
                    "items": items,
                    "request_id": request.id
                })
            else:
                logger.error("No items found in text response")
                return jsonify({"error": "Could not identify any items in the image"}), 400
            
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Failed to process image",
            "details": str(e) if os.getenv("FLASK_ENV") == "development" else "An unexpected error occurred",
            "request_id": request.id
        }), 500

@app.route('/api/stats', methods=['GET'])
@handle_errors
def get_stats():
    """Return API usage statistics"""
    api_calls = session.get('api_calls', 0)
    first_call = session.get('first_api_call', None)
    last_call = session.get('last_api_call', None)
    
    return jsonify({
        "api_calls": api_calls,
        "first_api_call": first_call,
        "last_api_call": last_call,
        "request_id": request.id
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model": "Gemini",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "request_id": request.id
    })

# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "error": "Rate limit exceeded. Please try again later.",
        "retry_after": e.description,
        "request_id": request.id
    }), 429

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}", exc_info=True)
    return jsonify({
        "error": "An internal server error occurred",
        "request_id": request.id
    }), 500

@app.errorhandler(404)
def not_found_error(e):
    return jsonify({
        "error": "Resource not found",
        "request_id": request.id
    }), 404

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    
    logger.info(f"Starting application on port {port}, debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)