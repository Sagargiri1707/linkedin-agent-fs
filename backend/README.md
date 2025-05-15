# LinkedIn Automation AI Agent

A FastAPI-based application that automates LinkedIn content creation, approval, and posting using AI services and WhatsApp for notifications.

## Features

- Trend detection using Perplexity AI
- AI content generation with DeepSeek
- Image generation with Ideogram
- LinkedIn OAuth 2.0 integration for posting
- WhatsApp notifications and approval workflow via Twilio
- Content scheduling and engagement tracking

## Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── config.py             # App configuration and settings
│   ├── database.py           # MongoDB connection management
│   ├── models.py             # Pydantic models for data structures
│   ├── scheduler.py          # APScheduler for background tasks
│   ├── services/
│   │   ├── __init__.py
│   │   ├── external_apis.py  # Integration with external services
│   │   └── linkedin_agent_service.py # Core business logic
├── main.py                   # FastAPI application entry point
├── requirements.txt          # Python dependencies
└── .env.example              # Example environment variables
```

## Setup

1. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys and configuration
   ```

4. **MongoDB Setup**
   - Install and run MongoDB locally, or use a cloud MongoDB service.
   - Update the connection string in your .env file.

5. **Run the application**
   ```bash
   uvicorn main:app --reload
   ```

6. **LinkedIn Setup**
   - Register an application at [LinkedIn Developers](https://www.linkedin.com/developers/)
   - Configure OAuth 2.0 settings with the correct redirect URI
   - Add the credentials to your .env file

7. **Twilio Setup**
   - Create a Twilio account
   - Set up a WhatsApp Sandbox or Business account
   - Configure the webhook to point to your `/webhook/twilio/whatsapp` endpoint
   - Add the credentials to your .env file

## Authentication

The application uses LinkedIn OAuth 2.0 for authentication. Visit `/auth/linkedin/login` to start the authorization flow.

## API Endpoints

- `GET /`: Health check
- `GET /auth/linkedin/login`: Start LinkedIn OAuth flow
- `GET /auth/linkedin/callback`: Handle OAuth callback from LinkedIn
- `POST /webhook/twilio/whatsapp`: Handle WhatsApp messages (approval/rejection)
- `POST /trigger/generate-content-from-trend`: Manual trigger for content generation

## Development

This application uses APScheduler for background tasks, MongoDB for storage, and FastAPI for the API layer.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 