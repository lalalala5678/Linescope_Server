# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Linescope_Server is a Flask-based server for the Jilin project that receives and displays sensor data and image recognition results from an Orange Pi device. The system is part of a 4-component pipeline: STM32 sensor clusters → 4G monitoring → Orange Pi (image recognition) → Server (display).

## Architecture

**Core Application** (`app.py`):

- Flask web server with MJPEG video streaming
- Background job scheduler running DataStore operations every 30 minutes
- Routes for dashboard, API endpoints, and real-time image streaming

**Utils Module Structure**:

- `DataRead.py`: Reads sensor data from CSV files, returns structured data with timestamps, temperature, humidity, pressure, lux, and sway speed
- `DataStore.py`: Manages rolling data storage with 30-minute intervals, maintains sliding window of sensor data
- `GetImage.py`: Processes test images by drawing incrementing numbers and returns frames for video streaming
- `GetSensorData.py`: Generates random sensor data samples for testing

**Data Flow**:

1. Sensor data arrives via Orange Pi and gets stored in `utils/data/data.txt`
2. Background job (`DataStore.main()`) runs every 30 minutes to maintain rolling data window
3. Image processing occurs in real-time via `/stream.mjpg` endpoint
4. Frontend displays dashboard with historical data and live image feed

## Development Commands

**Start the server**:

```bash
python app.py
```

Server runs on `http://0.0.0.0:5000` with debug mode enabled.

**Install dependencies**:

```bash
pip install -r requirements.txt
```

**Test individual modules**:

```bash
python utils/DataRead.py        # Test sensor data reading
python utils/GetImage.py        # Test image processing
python utils/DataStore.py       # Test data storage operations
```

## Key Endpoints

- `/` - Main dashboard interface
- `/dashboard` - Historical sensor data visualization
- `/result` - Live image recognition results
- `/stream.mjpg` - MJPEG video stream for image display
- `/api/sensor-data` - REST API for sensor data
- `/api/sensors?limit=N` - Get latest N sensor readings
- `/healthz` - Health check endpoint

## Data Formats

**Sensor Data Structure**:

```python
{
    "timestamp_Beijing": "2025-08-18 23:30",  # Beijing timezone
    "sway_speed_dps": float,                  # Degrees per second
    "temperature_C": float,                   # Celsius
    "humidity_RH": float,                     # Relative humidity %
    "pressure_hPa": float,                    # Hectopascals
    "lux": float                              # Light intensity
}
```

## Configuration

**Timing Settings** (in `AppConfig`):

- DataStore interval: 30 minutes (configurable via `datastore_interval_minutes`)
- Video stream frame rate: ~5 FPS (configurable via `stream_frame_interval_sec`)
- Log rotation: 5MB max file size with 3 backups

**File Locations**:

- Sensor data: `utils/data/data.txt`
- Test images: `utils/data/test_image.jpg`
- Image counter: `utils/data/TestImageNumber.txt`
- Application logs: `app.log`

## important Notes

- Use venv to manage dependencies
