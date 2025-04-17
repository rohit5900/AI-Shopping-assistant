import pytest
import json
import os
from app import app, validate_image_file
from unittest.mock import patch, MagicMock

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

def test_home_page(client):
    """Test that the home page loads correctly"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Shopping AI Assistant' in response.data

def test_health_check(client):
    """Test the health check endpoint"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert data['model'] == 'Gemini'
    assert 'request_id' in data

def test_chat_endpoint_empty_query(client):
    """Test the chat endpoint with an empty query"""
    response = client.post('/api/chat', 
                          data=json.dumps({'query': ''}),
                          content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Please enter a valid question'

def test_chat_endpoint_invalid_json(client):
    """Test the chat endpoint with invalid JSON"""
    response = client.post('/api/chat', 
                          data='invalid json',
                          content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert data['error'] == 'Invalid JSON data'

@patch('app.model.generate_content')
def test_chat_endpoint_success(mock_generate_content, client):
    """Test the chat endpoint with a valid query"""
    # Mock the Gemini model response
    mock_response = MagicMock()
    mock_response.text = "1. Product Category: Headphones\n2. Top 3 Recommendations:\n   - Sony WH-1000XM4 | Price: $348 | Features: Noise cancelling, 30-hour battery, Bluetooth 5.0 | Buy at: [Amazon, Best Buy]\n   - Bose QuietComfort 45 | Price: $329 | Features: Comfortable, great sound, noise cancelling | Buy at: [Amazon, Bose]\n   - Apple AirPods Pro | Price: $249 | Features: Seamless Apple integration, noise cancelling, spatial audio | Buy at: [Apple, Amazon]\n3. Shopping Tips: Consider your primary use case - commuting, gaming, or music listening."
    mock_generate_content.return_value = mock_response
    
    response = client.post('/api/chat', 
                          data=json.dumps({'query': 'Best wireless headphones under $400'}),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'response' in data
    assert 'cached' in data
    assert data['cached'] == False
    assert 'request_id' in data
    assert 'Sony WH-1000XM4' in data['response']

def test_validate_image_file_valid():
    """Test the validate_image_file function with a valid file"""
    mock_file = MagicMock()
    mock_file.filename = 'test.jpg'
    mock_file.content_type = 'image/jpeg'
    
    is_valid, result = validate_image_file(mock_file)
    assert is_valid == True
    assert isinstance(result, str)
    assert result.endswith('_test.jpg')

def test_validate_image_file_invalid_extension():
    """Test the validate_image_file function with an invalid file extension"""
    mock_file = MagicMock()
    mock_file.filename = 'test.exe'
    mock_file.content_type = 'application/x-msdownload'
    
    is_valid, result = validate_image_file(mock_file)
    assert is_valid == False
    assert 'Invalid file type' in result

def test_validate_image_file_invalid_mime():
    """Test the validate_image_file function with an invalid MIME type"""
    mock_file = MagicMock()
    mock_file.filename = 'test.jpg'
    mock_file.content_type = 'application/pdf'
    
    is_valid, result = validate_image_file(mock_file)
    assert is_valid == False
    assert 'Invalid file type' in result

def test_validate_image_file_no_filename():
    """Test the validate_image_file function with no filename"""
    mock_file = MagicMock()
    mock_file.filename = ''
    mock_file.content_type = 'image/jpeg'
    
    is_valid, result = validate_image_file(mock_file)
    assert is_valid == False
    assert 'No filename provided' in result

def test_validate_image_file_none():
    """Test the validate_image_file function with None"""
    is_valid, result = validate_image_file(None)
    assert is_valid == False
    assert 'No file provided' in result 