# PianoGuard DCM-1 API Stack Documentation

**Server**: dev1.pgapi.net
**Environment**: Production Development Server
**Last Updated**: 2025-10-30
**Author**: R. Andrew Ballard (c) 2025 "Andwardo"

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [System Services](#system-services)
3. [Database Configuration](#database-configuration)
4. [API Endpoints](#api-endpoints)
5. [MQTT Telemetry System](#mqtt-telemetry-system)
6. [SSL/TLS Configuration](#ssltls-configuration)
7. [Environment Variables](#environment-variables)
8. [Deployment](#deployment)
9. [Monitoring & Logs](#monitoring--logs)
10. [Testing](#testing)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    PianoGuard DCM-1 Stack                   │
└─────────────────────────────────────────────────────────────┘

Internet
   │
   ├─── HTTPS (443) ──────┐
   └─── HTTP  (80)  ──────┤
                          │
                    ┌─────▼─────┐
                    │   NGINX   │ (Reverse Proxy + SSL)
                    │   :443    │
                    └─────┬─────┘
                          │
                    ┌─────▼─────────┐
                    │  Gunicorn     │ (WSGI Server)
                    │  127.0.0.1    │
                    │  :8000        │
                    └─────┬─────────┘
                          │
                    ┌─────▼─────────┐
                    │   FastAPI     │ (API Framework)
                    │   + Uvicorn   │
                    └─────┬─────────┘
                          │
         ┌────────────────┼────────────────┐
         │                │                │
    ┌────▼─────┐   ┌─────▼──────┐   ┌────▼─────┐
    │PostgreSQL│   │  Mosquitto │   │  Python  │
    │  :5432   │   │   MQTT     │   │  venv    │
    └──────────┘   │  :1883     │   └──────────┘
                   │  :8883(TLS)│
                   └─────▲──────┘
                         │
                   ┌─────┴──────┐
                   │   MQTT     │
                   │ Subscriber │
                   │  Service   │
                   └────────────┘

DCM-1 Devices ──── MQTT Publish ───> pianoguard/+/telemetry
```

### Technology Stack

- **OS**: CentOS/RHEL 8 (Linux 4.18.0)
- **Web Server**: NGINX 1.x (Reverse proxy + SSL termination)
- **WSGI Server**: Gunicorn 23.0.0 with Uvicorn workers
- **API Framework**: FastAPI 0.116.1
- **Database**: PostgreSQL 13
- **MQTT Broker**: Mosquitto 2.x
- **Python**: 3.11.13
- **Process Manager**: systemd

---

## System Services

### 1. pgapi-gunicorn.service

**Purpose**: Main API service serving REST endpoints

**Service File**: `/etc/systemd/system/pgapi-gunicorn.service`

```ini
[Unit]
Description=Gunicorn for PianoGuard API
After=network.target

[Service]
User=andrew
Group=andrew
WorkingDirectory=/home/andrew/pgapi
Environment="PATH=/home/andrew/pgapi/venv/bin"
ExecStart=/bin/bash /home/andrew/pgapi/start_gunicorn.sh
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**Start Script**: `/home/andrew/pgapi/start_gunicorn.sh`

```bash
#!/bin/bash
cd /home/andrew/pgapi
source venv/bin/activate
exec gunicorn main:app --config gunicorn_config.py --worker-class uvicorn.workers.UvicornWorker
```

**Configuration**: `gunicorn_config.py`
- Bind: `127.0.0.1:8000`
- Workers: 4
- Worker class: `uvicorn.workers.UvicornWorker`
- Timeout: 60 seconds

**Commands**:
```bash
sudo systemctl start pgapi-gunicorn
sudo systemctl stop pgapi-gunicorn
sudo systemctl restart pgapi-gunicorn
sudo systemctl status pgapi-gunicorn
sudo journalctl -u pgapi-gunicorn -f
```

### 2. mqtt-subscriber.service

**Purpose**: Subscribe to MQTT telemetry and store in PostgreSQL

**Service File**: `/etc/systemd/system/mqtt-subscriber.service`

```ini
[Unit]
Description=PianoGuard MQTT Subscriber Service
After=network.target mosquitto.service postgresql-13.service
Requires=network.target

[Service]
Type=simple
User=andrew
Group=andrew
WorkingDirectory=/home/andrew/pgapi
Environment="PATH=/home/andrew/pgapi/venv/bin"
ExecStart=/bin/bash /home/andrew/pgapi/start_mqtt_subscriber.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mqtt-subscriber

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Start Script**: `/home/andrew/pgapi/start_mqtt_subscriber.sh`

```bash
#!/bin/bash
cd /home/andrew/pgapi
source venv/bin/activate
exec python mqtt_subscriber.py
```

**Commands**:
```bash
sudo systemctl start mqtt-subscriber
sudo systemctl stop mqtt-subscriber
sudo systemctl restart mqtt-subscriber
sudo systemctl status mqtt-subscriber
sudo journalctl -u mqtt-subscriber -f
```

### 3. mosquitto.service

**Purpose**: MQTT broker for device telemetry

**Configuration**: `/etc/mosquitto/mosquitto.conf`

```conf
# Mosquitto minimal config for PianoGuard
per_listener_settings false
allow_anonymous true

log_dest file /var/log/mosquitto/mosquitto.log
log_type all

listener 1883                    # Non-TLS (testing)

listener 8883                    # TLS (production)
certfile /etc/mosquitto/mosquitto.crt
keyfile /etc/mosquitto/mosquitto.key
```

**Commands**:
```bash
sudo systemctl start mosquitto
sudo systemctl stop mosquitto
sudo systemctl restart mosquitto
sudo systemctl status mosquitto
sudo journalctl -u mosquitto -f
```

### 4. postgresql-13.service

**Purpose**: Primary data store for devices and telemetry

**Database**: `pianoguard`
**User**: `pianoguard`
**Port**: 5432

**Commands**:
```bash
sudo systemctl start postgresql-13
sudo systemctl stop postgresql-13
sudo systemctl restart postgresql-13
sudo systemctl status postgresql-13
PGPASSWORD='Kawai2Toyota4Steinway' psql -U pianoguard -d pianoguard -h localhost
```

### 5. nginx.service

**Purpose**: Reverse proxy and SSL termination

**Configuration**: `/etc/nginx/conf.d/pgapi.conf` (assumed)

**SSL Certificates**:
- Certificate: `/etc/letsencrypt/live/dev1.pgapi.net/fullchain.pem`
- Private Key: `/etc/letsencrypt/live/dev1.pgapi.net/privkey.pem`
- Expiration: January 27, 2026

**Commands**:
```bash
sudo systemctl start nginx
sudo systemctl stop nginx
sudo systemctl restart nginx
sudo systemctl reload nginx  # Reload config without dropping connections
sudo nginx -t                # Test configuration
sudo nginx -s reload         # Reload SSL certificates
```

---

## Database Configuration

### Connection Details

- **Host**: localhost
- **Port**: 5432
- **Database**: pianoguard
- **User**: pianoguard
- **Password**: Kawai2Toyota4Steinway

### Schema

#### Devices Table

```sql
Table "public.Devices"
    Column     |           Type           | Nullable |                Default
---------------+--------------------------+----------+---------------------------------------
 id            | integer                  | not null | nextval('"Devices_id_seq"'::regclass)
 device_id     | character varying(255)   | not null |
 userId        | integer                  |          |
 friendly_name | character varying(255)   |          |
 location      | character varying(255)   |          |
 last_seen     | timestamp with time zone |          |
 status        | character varying(255)   |          | 'offline'::character varying
 createdAt     | timestamp with time zone | not null |
 updatedAt     | timestamp with time zone | not null |

Indexes:
    "Devices_pkey" PRIMARY KEY, btree (id)
    "Devices_device_id_key" UNIQUE CONSTRAINT, btree (device_id)

Foreign-key constraints:
    "Devices_userId_fkey" FOREIGN KEY ("userId") REFERENCES "Users"(id)
```

#### TelemetryData Table

```sql
Table "public.TelemetryData"
     Column      |           Type           | Nullable |                   Default
-----------------+--------------------------+----------+---------------------------------------------
 id              | integer                  | not null | nextval('"TelemetryData_id_seq"'::regclass)
 device_id       | character varying(255)   | not null |
 timestamp       | timestamp with time zone | not null |
 wifi_rssi       | integer                  |          |
 createdAt       | timestamp with time zone | not null |
 updatedAt       | timestamp with time zone | not null |
 fw_version      | character varying(32)    |          |
 wifi_ssid       | character varying(255)   |          |
 uptime_ms       | bigint                   |          |
 free_heap       | integer                  |          |
 led_power       | boolean                  | not null | false
 led_water       | boolean                  | not null | false
 led_pads        | boolean                  | not null | false
 battery_voltage | real                     |          |

Indexes:
    "TelemetryData_pkey" PRIMARY KEY, btree (id)
    "idx_telemetry_device_id" btree (device_id)
    "idx_telemetry_device_timestamp" btree (device_id, "timestamp" DESC)
    "idx_telemetry_timestamp" btree ("timestamp" DESC)
```

### Database Commands

```bash
# Connect to database
PGPASSWORD='Kawai2Toyota4Steinway' psql -U pianoguard -d pianoguard -h localhost

# View table schema
\d "Devices"
\d "TelemetryData"

# Query latest telemetry
SELECT device_id, timestamp, fw_version, battery_voltage
FROM "TelemetryData"
ORDER BY "createdAt" DESC
LIMIT 10;

# Query device list
SELECT device_id, last_seen, status
FROM "Devices"
ORDER BY last_seen DESC;
```

---

## API Endpoints

**Base URL**: `https://dev1.pgapi.net`

### Health Check

**GET /**

Check API status.

**Response**:
```json
{
  "message": "PianoGuard API online"
}
```

### Device Registration

**POST /register-device**

Register a new DCM-1 device.

**Headers**:
- `X-Factory-Key`: Factory authentication key (64 characters)

**Request Body**:
```json
{
  "device_id": "DCM1-XXXXXXXXXXXX",
  "firmware_version": "1.0.0"
}
```

**Response**:
```json
{
  "status": "registered",
  "device_id": "DCM1-XXXXXXXXXXXX"
}
```

### Latest Telemetry

**GET /api/data/latest**

Get the most recent telemetry data.

**Query Parameters**:
- `device_id` (optional): Filter by specific device

**Response**:
```json
{
  "device_id": "test-device-001",
  "timestamp": 1730297800,
  "fw_version": "1.0.0",
  "wifi_ssid": "TestNetwork",
  "wifi_rssi": -65,
  "uptime_ms": 123456,
  "free_heap": 50000,
  "battery_voltage": 12.5,
  "status": {
    "power": true,
    "water": false,
    "pads": true
  }
}
```

### Telemetry History

**GET /api/data/history**

Get historical telemetry data.

**Query Parameters**:
- `device_id` (optional): Filter by specific device
- `limit` (optional): Maximum records to return (1-1000, default: 100)

**Response**:
```json
{
  "data": [
    {
      "device_id": "test-device-001",
      "timestamp": 1730297800,
      "fw_version": "1.0.0",
      "wifi_ssid": "TestNetwork",
      "wifi_rssi": -65,
      "uptime_ms": 123456,
      "free_heap": 50000,
      "battery_voltage": 12.5,
      "status": {
        "power": true,
        "water": false,
        "pads": true
      }
    }
  ],
  "total_records": 1
}
```

### Device List

**GET /api/data/devices**

Get list of all registered devices.

**Response**:
```json
[
  {
    "device_id": "test-device-001",
    "last_seen": 1730297800
  }
]
```

---

## MQTT Telemetry System

### Broker Configuration

**Host**: localhost
**Ports**:
- 1883: Non-TLS (currently active)
- 8883: TLS (configured but not active)

**Anonymous Access**: Enabled

### Topic Structure

**Pattern**: `pianoguard/{device_id}/telemetry`

**Example**: `pianoguard/DCM1-XXXXXXXXXXXX/telemetry`

**Wildcard Subscription**: `pianoguard/+/telemetry`

### Telemetry Message Format

DCM-1 devices publish JSON messages with the following structure:

```json
{
  "device_id": "DCM1-XXXXXXXXXXXX",
  "timestamp": 1730297800,
  "fw_version": "1.0.0",
  "wifi_ssid": "NetworkName",
  "wifi_rssi": -65,
  "uptime_ms": 123456,
  "free_heap": 50000,
  "battery_voltage": 12.5,
  "status": {
    "power": true,
    "water": false,
    "pads": true
  }
}
```

**Required Fields**:
- `device_id`: Unique device identifier
- `timestamp`: Unix epoch timestamp (seconds)

**Optional Fields**:
- `fw_version`: Firmware version string
- `wifi_ssid`: Connected WiFi network name
- `wifi_rssi`: WiFi signal strength (dBm)
- `uptime_ms`: Device uptime in milliseconds
- `free_heap`: Available heap memory (bytes)
- `battery_voltage`: Battery voltage (volts)
- `status`: Object containing LED status indicators
  - `power`: Power LED status (boolean)
  - `water`: Water sensor LED status (boolean)
  - `pads`: Pad sensor LED status (boolean)

### MQTT Subscriber Service

The `mqtt_subscriber.py` service:
1. Subscribes to `pianoguard/+/telemetry`
2. Validates incoming messages
3. Stores telemetry in PostgreSQL
4. Updates device `last_seen` timestamp

**Features**:
- Async PostgreSQL connection pooling (asyncpg)
- Cross-thread async coordination with `asyncio.run_coroutine_threadsafe()`
- Automatic reconnection on disconnect
- Graceful shutdown handling (SIGTERM, SIGINT)
- Comprehensive logging

### Testing MQTT Telemetry

#### Publish Test Message

```bash
mosquitto_pub -h localhost -p 1883 \
  -t "pianoguard/test-device-001/telemetry" \
  -m '{
    "device_id": "test-device-001",
    "timestamp": 1730297800,
    "fw_version": "1.0.0",
    "wifi_ssid": "TestNetwork",
    "wifi_rssi": -65,
    "uptime_ms": 123456,
    "free_heap": 50000,
    "battery_voltage": 12.5,
    "status": {
      "power": true,
      "water": false,
      "pads": true
    }
  }'
```

#### Verify Storage

```bash
# Check subscriber logs
sudo journalctl -u mqtt-subscriber -n 20

# Query database
PGPASSWORD='Kawai2Toyota4Steinway' psql -U pianoguard -d pianoguard -h localhost \
  -c "SELECT device_id, timestamp, fw_version, battery_voltage
      FROM \"TelemetryData\"
      ORDER BY \"createdAt\" DESC
      LIMIT 1;"
```

#### Verify API Response

```bash
curl "https://dev1.pgapi.net/api/data/latest?device_id=test-device-001"
```

---

## SSL/TLS Configuration

### SSL Certificates

**Domain**: dev1.pgapi.net

**Certificate Authority**: Let's Encrypt

**Certificate Paths**:
- Full Chain: `/etc/letsencrypt/live/dev1.pgapi.net/fullchain.pem`
- Private Key: `/etc/letsencrypt/live/dev1.pgapi.net/privkey.pem`
- Certificate: `/etc/letsencrypt/live/dev1.pgapi.net/cert.pem`
- Chain: `/etc/letsencrypt/live/dev1.pgapi.net/chain.pem`

**Expiration**: January 27, 2026

### Certificate Renewal

Let's Encrypt certificates expire every 90 days.

```bash
# Manual renewal (if auto-renewal fails)
sudo certbot renew

# Reload nginx to apply new certificate
sudo nginx -s reload

# Verify certificate expiration
echo | openssl s_client -servername dev1.pgapi.net -connect dev1.pgapi.net:443 2>/dev/null | openssl x509 -noout -dates
```

### MQTT TLS Configuration

**Certificate**: `/etc/mosquitto/mosquitto.crt` (self-signed)
**Private Key**: `/etc/mosquitto/mosquitto.key`
**Created**: July 19, 2025

**Note**: TLS is currently disabled for MQTT (using port 1883). To enable:

1. Update `mqtt_subscriber.py`:
   ```python
   MQTT_PORT = 8883
   USE_TLS = True
   ```

2. Restart service:
   ```bash
   sudo systemctl restart mqtt-subscriber
   ```

---

## Environment Variables

**File**: `/home/andrew/pgapi/.env`

```bash
# Device authentication key (64 characters)
PIANOGUARD_FACTORY_KEY=732f1541438256855d95585cf4eff969623bb1caff374b47

# API secret key for JWT/sessions
SECRET_KEY=SkeeterWasADog

# Database configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=pianoguard
DB_PASSWORD=Kawai2Toyota4Steinway
DB_NAME=pianoguard

# MQTT configuration
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=your-mqtt-username
MQTT_PASSWORD=your-mqtt-password
MQTT_TLS=False

# AWS IoT (not currently used)
AWS_IOT_ENDPOINT=your-iot-endpoint.amazonaws.com
AWS_CLIENT_ID=device123
AWS_ROOT_CA_PATH=/certs/root_ca.pem
AWS_CERT_PATH=/certs/client.crt
AWS_KEY_PATH=/certs/client.key

# Logging
LOG_LEVEL=info
```

### Environment Variable Loading

The application uses two approaches:

1. **env.py**: Strict validation with `get_env_var()` function
2. **config.py**: Pydantic BaseSettings approach

Both load from `.env` file using `python-dotenv`.

---

## Deployment

### Directory Structure

```
/home/andrew/pgapi/
├── main.py                      # FastAPI application entry point
├── data.py                      # Data API routes
├── env.py                       # Environment variable validation
├── config.py                    # Pydantic settings
├── gunicorn_config.py           # Gunicorn configuration
├── mqtt_subscriber.py           # MQTT subscriber service
├── start_gunicorn.sh            # Gunicorn start script
├── start_mqtt_subscriber.sh     # MQTT subscriber start script
├── mqtt-subscriber.service      # Systemd service file
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables
├── venv/                        # Python virtual environment
├── CLAUDE.md                    # Claude Code guidance
├── STACK.md                     # This file
└── .git/                        # Git repository
```

### Python Dependencies

**File**: `requirements.txt`

```
annotated-types==0.7.0
anyio==4.9.0
asyncpg==0.29.0
click==8.2.1
fastapi==0.116.1
gunicorn==23.0.0
h11==0.16.0
idna==3.10
packaging==25.0
paho-mqtt==2.1.0
pydantic==2.11.7
pydantic_core==2.33.2
python-dotenv==1.1.1
sniffio==1.3.1
starlette==0.47.2
typing-inspection==0.4.1
typing_extensions==4.14.1
uvicorn==0.35.0
```

### Virtual Environment Setup

```bash
cd /home/andrew/pgapi
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Service Installation

```bash
# Copy service files to systemd
sudo cp /home/andrew/pgapi/mqtt-subscriber.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services to start on boot
sudo systemctl enable pgapi-gunicorn
sudo systemctl enable mqtt-subscriber
sudo systemctl enable mosquitto
sudo systemctl enable postgresql-13
sudo systemctl enable nginx

# Start all services
sudo systemctl start pgapi-gunicorn
sudo systemctl start mqtt-subscriber
sudo systemctl start mosquitto
sudo systemctl start postgresql-13
sudo systemctl start nginx
```

---

## Monitoring & Logs

### Service Status

```bash
# Check all services
systemctl status pgapi-gunicorn
systemctl status mqtt-subscriber
systemctl status mosquitto
systemctl status postgresql-13
systemctl status nginx
```

### Log Files

**Application Logs**:
```bash
# API logs
sudo journalctl -u pgapi-gunicorn -f
sudo journalctl -u pgapi-gunicorn -n 100 --no-pager

# MQTT subscriber logs
sudo journalctl -u mqtt-subscriber -f
sudo journalctl -u mqtt-subscriber -n 100 --no-pager

# Mosquitto logs
sudo journalctl -u mosquitto -f
cat /var/log/mosquitto/mosquitto.log
tail -f /var/log/mosquitto/mosquitto.log

# MQTT subscriber file log
tail -f /var/log/mqtt-subscriber.log

# PostgreSQL logs
sudo journalctl -u postgresql-13 -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### System Monitoring

```bash
# View running processes
ps aux | grep gunicorn
ps aux | grep python
ps aux | grep mosquitto

# Check listening ports
sudo ss -tlnp | grep :8000   # Gunicorn
sudo ss -tlnp | grep :1883   # MQTT
sudo ss -tlnp | grep :5432   # PostgreSQL
sudo ss -tlnp | grep :443    # NGINX HTTPS

# Check SELinux status
getenforce
sudo ausearch -m AVC -ts recent
```

---

## Testing

### API Health Check

```bash
# Local
curl http://localhost:8000/

# Remote
curl https://dev1.pgapi.net/
```

### Device Registration Test

```bash
curl -X POST https://dev1.pgapi.net/register-device \
  -H "Content-Type: application/json" \
  -H "X-Factory-Key: 732f1541438256855d95585cf4eff969623bb1caff374b47" \
  -d '{
    "device_id": "DCM1-TEST001",
    "firmware_version": "1.0.0"
  }'
```

### Telemetry API Tests

```bash
# Get latest telemetry
curl "https://dev1.pgapi.net/api/data/latest"
curl "https://dev1.pgapi.net/api/data/latest?device_id=test-device-001"

# Get telemetry history
curl "https://dev1.pgapi.net/api/data/history?limit=10"
curl "https://dev1.pgapi.net/api/data/history?device_id=test-device-001&limit=50"

# Get device list
curl "https://dev1.pgapi.net/api/data/devices"
```

### MQTT Publish Test

```bash
# Publish test telemetry
mosquitto_pub -h localhost -p 1883 \
  -t "pianoguard/DCM1-TEST001/telemetry" \
  -m '{"device_id":"DCM1-TEST001","timestamp":1730297800,"fw_version":"1.0.0","wifi_ssid":"TestNet","wifi_rssi":-65,"uptime_ms":123456,"free_heap":50000,"battery_voltage":12.5,"status":{"power":true,"water":false,"pads":true}}'

# Subscribe to all telemetry (for debugging)
mosquitto_sub -h localhost -p 1883 -t "pianoguard/+/telemetry" -v
```

### Database Tests

```bash
# Check device count
PGPASSWORD='Kawai2Toyota4Steinway' psql -U pianoguard -d pianoguard -h localhost \
  -c "SELECT COUNT(*) FROM \"Devices\";"

# Check telemetry count
PGPASSWORD='Kawai2Toyota4Steinway' psql -U pianoguard -d pianoguard -h localhost \
  -c "SELECT COUNT(*) FROM \"TelemetryData\";"

# View recent telemetry
PGPASSWORD='Kawai2Toyota4Steinway' psql -U pianoguard -d pianoguard -h localhost \
  -c "SELECT device_id, timestamp, led_power, led_water, led_pads
      FROM \"TelemetryData\"
      ORDER BY \"createdAt\" DESC
      LIMIT 5;"
```

### End-to-End Test

Complete pipeline test:

```bash
# 1. Publish MQTT message
mosquitto_pub -h localhost -p 1883 \
  -t "pianoguard/test-e2e/telemetry" \
  -m '{"device_id":"test-e2e","timestamp":1730297800,"fw_version":"1.0.0","battery_voltage":12.5,"status":{"power":true,"water":false,"pads":true}}'

# 2. Check subscriber processed it
sudo journalctl -u mqtt-subscriber -n 5

# 3. Verify in database
PGPASSWORD='Kawai2Toyota4Steinway' psql -U pianoguard -d pianoguard -h localhost \
  -c "SELECT * FROM \"TelemetryData\" WHERE device_id='test-e2e' ORDER BY \"createdAt\" DESC LIMIT 1;"

# 4. Verify via API
curl "https://dev1.pgapi.net/api/data/latest?device_id=test-e2e"
```

---

## Troubleshooting

### Common Issues

#### API Not Responding

```bash
# Check if service is running
sudo systemctl status pgapi-gunicorn

# Check logs for errors
sudo journalctl -u pgapi-gunicorn -n 50

# Restart service
sudo systemctl restart pgapi-gunicorn
```

#### MQTT Subscriber Not Storing Data

```bash
# Check service status
sudo systemctl status mqtt-subscriber

# Check logs
sudo journalctl -u mqtt-subscriber -n 50

# Verify MQTT broker is running
sudo systemctl status mosquitto

# Test MQTT connection
mosquitto_sub -h localhost -p 1883 -t "pianoguard/+/telemetry" -v

# Restart subscriber
sudo systemctl restart mqtt-subscriber
```

#### Database Connection Errors

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql-13

# Test connection
PGPASSWORD='Kawai2Toyota4Steinway' psql -U pianoguard -d pianoguard -h localhost -c "SELECT 1;"

# Check PostgreSQL logs
sudo journalctl -u postgresql-13 -n 50
```

#### SSL Certificate Errors

```bash
# Check certificate expiration
echo | openssl s_client -servername dev1.pgapi.net -connect dev1.pgapi.net:443 2>/dev/null | openssl x509 -noout -dates

# Reload nginx with new certificate
sudo nginx -s reload

# Test nginx configuration
sudo nginx -t
```

### SELinux Issues

If services fail with permission errors:

```bash
# Check SELinux status
getenforce

# View recent denials
sudo ausearch -m AVC -ts recent

# Temporarily disable (for testing only)
sudo setenforce 0

# Re-enable
sudo setenforce 1
```

---

## Security Considerations

1. **Factory Key**: The `PIANOGUARD_FACTORY_KEY` should be rotated periodically
2. **Database Password**: Strong password in use, consider rotating
3. **MQTT Authentication**: Currently anonymous - should enable authentication for production
4. **MQTT TLS**: Currently disabled - should enable for production deployments
5. **Firewall**: Ensure only necessary ports are exposed (443, 1883/8883)
6. **SELinux**: Currently enforcing - provides additional security layer
7. **Service Isolation**: Services run as non-root user `andrew`

---

## Future Enhancements

1. **MQTT TLS**: Enable TLS on port 8883 for encrypted device communication
2. **MQTT Authentication**: Implement username/password or certificate-based auth
3. **Rate Limiting**: Add rate limiting to API endpoints
4. **Authentication**: Implement JWT-based API authentication
5. **Monitoring**: Add Prometheus/Grafana for metrics
6. **Alerting**: Set up alerts for service failures
7. **Backup**: Implement automated PostgreSQL backups
8. **High Availability**: Consider PostgreSQL replication
9. **Load Balancing**: Multiple API instances for scalability
10. **Docker**: Containerize services for easier deployment

---

## Contact & Support

**Developer**: R. Andrew Ballard (c) 2025 "Andwardo"
**Repository**: https://github.com/BlueSkyFusion/pgapi
**Server**: dev1.pgapi.net

---

*Last Updated: 2025-10-30*
