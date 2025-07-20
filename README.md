# PianoGuard API

This is the backend API server for the PianoGuard project. It uses **FastAPI** for web routing and **Gunicorn** with **Uvicorn workers** for production deployment. The project is managed in a Python 3.11 virtual environment.

## Features

- FastAPI-based REST API
- Gunicorn + Uvicorn production-ready setup
- systemd service for background execution
- Environment-specific virtual environment support

## Local Development

### Requirements

- Python 3.11
- Virtualenv (recommended)
- Git

### Setup

```bash
git clone https://github.com/Andwardo/pgapi.git
cd pgapi
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Run Locally

```bash
uvicorn main:app --reload
```

The server will start on `http://127.0.0.1:8000/`.

## Production Deployment

Gunicorn is used to run the API as a background service via systemd.

### Example systemd Service File

```ini
[Unit]
Description=Gunicorn for PianoGuard API
After=network.target

[Service]
User=andrew
Group=andrew
WorkingDirectory=/home/andrew/pgapi
Environment="PATH=/home/andrew/pgapi/venv/bin"
ExecStart=/home/andrew/pgapi/venv/bin/gunicorn main:app --config /home/andrew/pgapi/gunicorn_config.py --worker-class uvicorn.workers.UvicornWorker

Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

### Start and Enable

```bash
sudo systemctl daemon-reload
sudo systemctl enable pgapi-gunicorn
sudo systemctl start pgapi-gunicorn
```

## API Test

Test the server with:

```bash
curl http://127.0.0.1:8000/
```

Expected response:

```json
{"message":"PianoGuard API online"}
```

## License

 © 2025 R.Andrew Ballard | Blue Sky Fusion, Inc. ALL RIGHTS RESERVED
