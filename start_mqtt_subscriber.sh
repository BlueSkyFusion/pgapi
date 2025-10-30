#!/bin/bash
cd /home/andrew/pgapi
source venv/bin/activate
exec python mqtt_subscriber.py
