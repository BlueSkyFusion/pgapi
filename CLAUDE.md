# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Local Development
```bash
# Setup virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run development server with auto-reload
uvicorn main:app --reload

# Run production server locally
gunicorn main:app --config gunicorn_config.py --worker-class uvicorn.workers.UvicornWorker
```

### Testing
```bash
# Test API endpoint
curl http://127.0.0.1:8000/
# Expected: {"message":"PianoGuard API online"}

# Test dev-only env endpoint (when ENVIRONMENT=dev)
curl http://127.0.0.1:8000/env-test
```

## Architecture

### Core Application Structure
- **main.py**: FastAPI application entry point with API routes
- **env.py**: Strict environment variable validation with length checks (pgapi.env pattern)
- **config.py**: Pydantic-based settings using BaseSettings (alternative to env.py)
- **gunicorn_config.py**: Production server configuration

### Environment Management
The codebase uses two approaches for environment variables:
1. **env.py**: Strict validation with `get_env_var()` function that enforces required keys and lengths
2. **config.py**: Pydantic BaseSettings approach with typed configuration

**Important**: Use the `pgapi.env` pattern (env.py) for strict .env access instead of `os.getenv()` directly in the app.

### API Endpoints
- `GET /`: Health check endpoint
- `GET /env-test`: Development-only endpoint for environment variable testing
- `POST /register-device`: Device registration with factory key validation

### Production Deployment
- Uses Gunicorn with Uvicorn workers
- Runs as systemd service (pgapi-gunicorn.service)
- NGINX reverse proxy with SSL termination
- Binds to 127.0.0.1:8000 for local communication

### Key Dependencies
- FastAPI for web framework
- Pydantic for data validation
- python-dotenv for environment management
- Gunicorn + Uvicorn for production ASGI serving

### Environment Variables
- `PIANOGUARD_FACTORY_KEY`: 64-character factory authentication key
- `ENVIRONMENT`: Set to "dev" for development features (default: "prod")