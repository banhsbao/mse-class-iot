# IoT Monitoring System

A system for monitoring IoT nodes using Flask, SQLite, and Docker on Raspberry Pi.

## Features

- View nodes on a map with sensor data
- Dashboard with real-time node status
- Detailed node view with historical data and charts
- Dummy data generation for testing (toggle on/off)
- Automatic status checking for nodes

## API Endpoints

- `GET /api/nodes` - List all nodes with their latest sensor data
- `GET /api/nodes/<node_id>` - Get detailed information for a specific node
- `GET /api/dashboard` - Get dashboard data for up to 20 nodes
- `POST /api/dummy-data/enable` - Enable dummy data generation
- `POST /api/dummy-data/disable` - Disable dummy data generation

## Prerequisites

- Docker and Docker Compose
- Raspberry Pi (recommended) or any machine with Docker support

## Getting Started

1. Clone this repository:
   ```
   git clone <repository-url>
   cd iot-monitoring
   ```

2. Run with Docker Compose:
   ```
   docker-compose up -d
   ```

3. Access the application:
   - Web Interface: http://localhost:5000
   - API: http://localhost:5000/api/nodes

## Development

If you want to run the application directly without Docker:

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python app.py
   ```

## Data Storage

The application uses SQLite for data storage. In the Docker configuration, data is stored in a persistent volume.

## Project Structure

- `app.py` - Main Flask application
- `templates/` - HTML templates
- `static/` - Static assets
- `Dockerfile` - Docker configuration
- `docker-compose.yml` - Docker Compose configuration
- `requirements.txt` - Python dependencies

## License

This project is released under the MIT License. 