# Shopping AI Assistant

A Flask-based web application that uses Google's Gemini AI to provide shopping recommendations and analyze shopping lists from images.

## Features

- **AI-Powered Shopping Recommendations**: Get personalized product recommendations based on your queries
- **Image Analysis**: Upload images of shopping lists to extract items automatically
- **Responsive UI**: Works on desktop and mobile devices
- **Dark/Light Mode**: Toggle between dark and light themes
- **Accessibility**: Built with accessibility in mind

## Tech Stack

- **Backend**: Flask, Python 3.8+
- **AI**: Google Gemini API
- **Frontend**: HTML, CSS, JavaScript
- **Caching**: Flask-Caching (with Redis support)
- **Rate Limiting**: Flask-Limiter
- **Security**: Flask-Talisman, Flask-SeaSurf

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/shopping-ai-assistant.git
   cd shopping-ai-assistant
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file based on `.env.example`:
   ```bash
   cp .env.example .env
   ```

5. Edit the `.env` file and add your Gemini API key and other configuration.

## Usage

1. Start the development server:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to `http://localhost:5000`

3. Enter your shopping query or upload an image of a shopping list

## API Endpoints

- `GET /`: Main application page
- `POST /api/chat`: Get shopping recommendations
- `POST /api/process-image`: Analyze shopping list images
- `GET /api/stats`: Get API usage statistics
- `GET /api/health`: Health check endpoint

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
```

### Linting

```bash
flake8
```

## Deployment

For production deployment, it's recommended to use Gunicorn with a reverse proxy like Nginx:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Security Considerations

- The application uses secure headers to protect against common web vulnerabilities
- Rate limiting is implemented to prevent abuse
- Input validation is performed on all user inputs
- File uploads are restricted to specific file types and sizes

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Google Gemini AI for providing the AI capabilities
- Flask and the Python ecosystem for the web framework and tools 