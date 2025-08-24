# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Linescope_Server is a Flask-based server for the Jilin project that receives and displays sensor data and image recognition results from an Orange Pi device. The system is part of a 4-component pipeline: STM32 sensor clusters → 4G monitoring → Orange Pi (image recognition) → Server (display).

## Recent Code Improvements (2025-08-24)

### Major Architectural Improvements

**1. Modular Flask Application Structure**
- Refactored from single `app.py` to modular architecture in `core/factory.py`
- Separated routes into `routes/main.py` and `routes/api.py`
- Enhanced error handling with global 404/500 handlers
- Fixed Flask template/static folder path configuration

**2. Frontend Complete Modernization**
- **HTML Templates**: Complete redesign with modern glassmorphism UI
  - `templates/index.html`: Interactive dashboard with real-time metrics
  - `templates/dashboard.html`: Advanced data visualization with AG-Grid
  - `templates/result.html`: Professional video streaming interface
- **CSS Framework**: Tailwind CSS + custom glassmorphism theme
- **JavaScript**: ES6+ class-based architecture with modern APIs
- **Libraries**: ECharts, AG-Grid, Lucide Icons, AOS animations

**3. Performance & Reliability Enhancements**
- Added file modification time caching in `DataRead.py`
- Progressive enhancement: WebSocket → SSE → Polling fallbacks
- Error resilience with retry mechanisms and graceful degradation
- Modern browser API integration (Performance Observer, Intersection Observer)

## Architecture

**Core Application** (`core/factory.py`):
- Flask application factory pattern
- Background job scheduler running DataStore operations every 30 minutes
- Global error handlers and logging configuration
- Modular route registration

**Routes Structure**:
- `routes/main.py`: Page rendering routes (/, /dashboard, /result, /stream.mjpg)
- `routes/api.py`: RESTful API endpoints with comprehensive error handling

**Utils Module Structure**:
- `DataRead.py`: Enhanced with memory caching and file modification tracking
- `DataStore.py`: Rolling data storage with 30-minute intervals
- `GetImage.py`: Real-time image processing with frame counter
- `GetSensorData.py`: Test data generation utilities

**Frontend Architecture**:
- Modern ES6+ class-based JavaScript (`static/js/script.js`)
- Glassmorphism design system (`static/css/styles.css`)
- Responsive design with mobile-first approach
- Progressive Web App features (Service Worker ready)

## Technology Stack

### Backend
- **Flask**: Web framework with modular structure
- **Python 3.9+**: Modern Python features
- **APScheduler**: Background job scheduling
- **Logging**: Structured logging with rotation

### Frontend
- **Tailwind CSS**: Utility-first CSS framework
- **Apache ECharts**: Advanced data visualization with WebGL
- **AG-Grid**: Enterprise-grade data tables
- **Lucide Icons**: Modern icon system
- **AOS**: Animate On Scroll library

### Development Tools
- **Flask Debug Mode**: Auto-reload and detailed error pages
- **Browser DevTools**: Performance monitoring and debugging
- **Modern JavaScript**: ES6+ features, async/await, modules

## Development Commands

**Start the server (new modular structure)**:
```bash
python -m flask --app core/factory.py run --debug --host=0.0.0.0 --port=5000
```

**Alternative legacy start**:
```bash
python app.py
```

**Install dependencies**:
```bash
pip install -r requirements.txt
```

**Test individual modules**:
```bash
python utils/DataRead.py        # Test sensor data reading with caching
python utils/GetImage.py        # Test image processing
python utils/DataStore.py       # Test data storage operations
python utils/GetSensorData.py   # Generate test sensor data
```

**Frontend development**:
- Live reload enabled in debug mode
- Browser DevTools for JavaScript debugging
- Network tab for API endpoint testing
- Console for error monitoring

## Key Endpoints

### Page Routes
- `/` - Modern interactive homepage with live metrics
- `/dashboard` - Advanced data visualization dashboard with AG-Grid
- `/result` - Professional video streaming interface
- `/stream.mjpg` - MJPEG video stream for real-time image display

### API Routes (Enhanced)
- `/api/sensor-data` - REST API for all sensor data with error handling
- `/api/sensors?limit=N` - Get latest N sensor readings with pagination
- `/api/sensors/latest` - Get most recent sensor reading
- `/healthz` - Health check endpoint

## Data Formats

**Sensor Data Structure** (Enhanced):
```python
{
    "timestamp_Beijing": "2025-08-24 23:30",  # Beijing timezone
    "sway_speed_dps": 30.87,                  # Degrees per second (float)
    "temperature_C": 22.79,                   # Celsius (float)
    "humidity_RH": 71.19,                     # Relative humidity % (float)
    "pressure_hPa": 1014.81,                  # Hectopascals (float)
    "lux": 8603.65                            # Light intensity (float)
}
```

**API Response Formats**:
```python
# Single record
{
    "timestamp_Beijing": "2025-08-24 23:30",
    "sway_speed_dps": 30.87,
    # ... other fields
}

# Multiple records
{
    "rows": [...],      # Array of sensor records
    "count": 672        # Total count
}

# Error response
{
    "error": "Error message"
}
```

## Configuration

**Timing Settings** (Enhanced in `AppConfig`):
- DataStore interval: 30 minutes (configurable via `datastore_interval_minutes`)
- Video stream frame rate: ~5 FPS (configurable via `stream_frame_interval_sec`)
- API cache timeout: Based on file modification time
- Frontend refresh: 5 minutes for data, 30 seconds for charts

**Frontend Configuration**:
- Chart refresh interval: 30 seconds
- Connection timeout: 10 seconds
- Retry attempts: 3
- Debounce delay: 300ms

**File Locations**:
- Sensor data: `utils/data/data.txt`
- Test images: `utils/data/test_image.jpg`
- Image counter: `utils/data/TestImageNumber.txt`
- Application logs: `app.log`
- Static assets: `static/css/`, `static/js/`, `static/images/`

## Error Handling & Logging

**Backend Error Handling**:
- Global 404/500 error handlers with JSON responses
- Try-catch blocks in all API endpoints
- File not found handling with graceful fallbacks
- Structured logging with timestamps and levels

**Frontend Error Handling**:
- API call retry mechanisms with exponential backoff
- Graceful degradation when services are unavailable
- User-friendly error notifications
- Console logging for debugging

**Logging Strategy**:
- Application logs: `app.log` with rotation (5MB, 3 backups)
- Console output in development mode
- Structured log messages with context
- Error tracking for monitoring

## Performance Optimizations

**Backend Performance**:
- File modification time caching in `DataRead.py`
- Background job scheduling to prevent blocking
- Efficient CSV reading with type conversion
- Memory-based caching for frequently accessed data

**Frontend Performance**:
- WebGL-accelerated charts for better rendering
- Lazy loading with Intersection Observer
- Debounced resize handlers
- Progressive enhancement (WebSocket → SSE → Polling)
- Resource cleanup and memory management

**Network Optimizations**:
- CDN usage for external libraries
- Efficient API endpoint design
- Proper HTTP status codes and error responses
- Connection pooling and timeout handling

## Security Considerations

**Backend Security**:
- Input validation and sanitization
- Proper error handling without information leakage
- File path validation to prevent directory traversal
- Resource limits and timeout configurations

**Frontend Security**:
- Content Security Policy ready
- XSS prevention through proper data handling
- Secure API communication patterns
- No sensitive data exposure in client-side code

## Browser Support

**Modern Browser Features**:
- ES6+ JavaScript (Chrome 61+, Firefox 55+, Safari 11+)
- CSS Grid and Flexbox layouts
- WebGL for chart acceleration
- Service Worker API (for future PWA features)
- Modern JavaScript APIs (fetch, Promise, async/await)

**Graceful Degradation**:
- Fallbacks for older browsers
- Progressive enhancement patterns
- Feature detection before usage
- Alternative layouts for unsupported features

## Troubleshooting

**Common Issues & Solutions**:

1. **Tailwind CSS not working**:
   - Ensure `<script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,line-clamp"></script>` is loaded
   - Check browser console for script loading errors

2. **Data not displaying**:
   - Verify `utils/data/data.txt` exists and has valid CSV data
   - Check API endpoints: `/api/sensor-data`, `/api/sensors/latest`
   - Monitor browser console for JavaScript errors

3. **Charts not rendering**:
   - Ensure ECharts library is loaded
   - Check for JavaScript errors in browser console
   - Verify chart container elements exist in DOM

4. **AG-Grid not working**:
   - Use `new agGrid.Grid()` constructor (not `agGrid.createGrid`)
   - Ensure AG-Grid CSS files are loaded
   - Check for proper column definitions

**Development Tips**:
- Use Flask debug mode for auto-reload: `--debug`
- Monitor browser console for frontend errors
- Use Network tab to debug API calls
- Check `app.log` for backend error details

## Future Enhancements

**Planned Improvements**:
- WebSocket real-time data streaming
- Progressive Web App (PWA) features
- Advanced data export formats (Excel, PDF)
- User authentication and role-based access
- Mobile-optimized interfaces
- Database integration for better data persistence

**Monitoring & Analytics**:
- Performance monitoring dashboard
- Error tracking and alerting
- Usage analytics and reporting
- System health monitoring

## Important Notes

- Use virtual environment (venv) to manage dependencies
- Test all changes in development mode before production
- Monitor browser console for JavaScript errors
- Keep dependencies updated for security
- Follow Python PEP 8 style guidelines
- Use modern JavaScript ES6+ features
- Implement proper error handling in all new code
- Test responsiveness across different screen sizes
- Validate data formats and API responses
- Use structured logging for debugging