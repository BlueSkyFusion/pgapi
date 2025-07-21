#!/bin/bash
/home/andrew/pgapi/venv/bin/gunicorn main:app \
  --config /home/andrew/pgapi/gunicorn_config.py \
  --worker-class uvicorn.workers.UvicornWorker
