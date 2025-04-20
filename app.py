from flask import Flask, jsonify, request, render_template
import sqlite3
import threading
import time
import random
import json
from datetime import datetime
import os

app = Flask(__name__)

# Configuration
DATABASE = os.environ.get('DATABASE', 'iot.db')
DUMMY_DATA_ENABLED = False

# Database initialization
def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    # Create nodes table
    c.execute('''
    CREATE TABLE IF NOT EXISTS nodes (
        node_id TEXT PRIMARY KEY,
        latitude REAL,
        longitude REAL,
        last_updated TIMESTAMP
    )
    ''')
    
    # Create sensor_data table
    c.execute('''
    CREATE TABLE IF NOT EXISTS sensor_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT,
        tds REAL,
        ph REAL,
        humidity REAL,
        temp REAL,
        status TEXT,
        timestamp TIMESTAMP,
        FOREIGN KEY (node_id) REFERENCES nodes (node_id)
    )
    ''')
    
    # Insert some demo nodes if they don't exist
    for i in range(1, 21):
        node_id = f"node_{i}"
        c.execute("INSERT OR IGNORE INTO nodes (node_id, latitude, longitude, last_updated) VALUES (?, ?, ?, ?)",
                 (node_id, 10.0 + random.random(), 106.0 + random.random(), datetime.now()))
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DATABASE}")

# Function to generate dummy data
def generate_dummy_data():
    while DUMMY_DATA_ENABLED:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Get all nodes
        c.execute("SELECT node_id FROM nodes")
        nodes = c.fetchall()
        
        # Generate data for each node
        for node in nodes:
            node_id = node[0]
            tds = random.uniform(100, 500)
            ph = random.uniform(6.0, 8.5)
            humidity = random.uniform(30, 90)
            temp = random.uniform(20, 35)
            
            # Insert data
            c.execute('''
            INSERT INTO sensor_data (node_id, tds, ph, humidity, temp, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (node_id, tds, ph, humidity, temp, datetime.now()))
        
        conn.commit()
        conn.close()
        time.sleep(1)
    print("Dummy data generation stopped")

# Check status of nodes periodically
def check_node_status():
    while True:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        # Find nodes without status
        c.execute('''
        SELECT DISTINCT s.node_id 
        FROM sensor_data s 
        WHERE s.status IS NULL
        ''')
        
        nodes_to_update = c.fetchall()
        
        # Update status to GOOD (in a real scenario, this would call an external API)
        for node in nodes_to_update:
            node_id = node[0]
            c.execute('''
            UPDATE sensor_data
            SET status = 'GOOD'
            WHERE node_id = ? AND status IS NULL
            ''', (node_id,))
            
        conn.commit()
        conn.close()
        time.sleep(30)

# API Routes
@app.route('/api/nodes', methods=['GET'])
def get_nodes():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all nodes with their most recent sensor data
    c.execute('''
    SELECT n.node_id, n.latitude, n.longitude, 
           sd.tds, sd.ph, sd.humidity, sd.temp
    FROM nodes n
    LEFT JOIN (
        SELECT s.node_id, s.tds, s.ph, s.humidity, s.temp,
               MAX(s.timestamp) as latest_time
        FROM sensor_data s
        GROUP BY s.node_id
    ) as sd ON n.node_id = sd.node_id
    ''')
    
    nodes = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify(nodes)

@app.route('/api/nodes/<node_id>', methods=['GET'])
def get_node_details(node_id):
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get node info
    c.execute('SELECT * FROM nodes WHERE node_id = ?', (node_id,))
    node = c.fetchone()
    
    if not node:
        conn.close()
        return jsonify({"error": "Node not found"}), 404
    
    # Get recent sensor data
    c.execute('''
    SELECT * FROM sensor_data 
    WHERE node_id = ? 
    ORDER BY timestamp DESC 
    LIMIT 100
    ''', (node_id,))
    
    sensor_data = [dict(row) for row in c.fetchall()]
    
    result = dict(node)
    result['sensor_data'] = sensor_data
    
    conn.close()
    return jsonify(result)

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get all nodes with their most recent data
    c.execute('''
    SELECT n.node_id, n.latitude, n.longitude, 
           sd.tds, sd.ph, sd.humidity, sd.temp, sd.status, sd.timestamp
    FROM nodes n
    LEFT JOIN (
        SELECT s.node_id, s.tds, s.ph, s.humidity, s.temp, s.status, s.timestamp,
               MAX(s.timestamp) as latest_time
        FROM sensor_data s
        GROUP BY s.node_id
    ) as sd ON n.node_id = sd.node_id
    LIMIT 20
    ''')
    
    dashboard_data = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify(dashboard_data)

@app.route('/api/dummy-data/enable', methods=['POST'])
def enable_dummy_data():
    global DUMMY_DATA_ENABLED
    DUMMY_DATA_ENABLED = True
    
    # Start the dummy data thread if it's not already running
    if not any(t.name == "dummy_data_thread" for t in threading.enumerate()):
        t = threading.Thread(target=generate_dummy_data, name="dummy_data_thread", daemon=True)
        t.start()
    
    return jsonify({"status": "Dummy data generation enabled"})

@app.route('/api/dummy-data/disable', methods=['POST'])
def disable_dummy_data():
    global DUMMY_DATA_ENABLED
    DUMMY_DATA_ENABLED = False
    return jsonify({"status": "Dummy data generation disabled"})

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/node-details.html')
def node_details():
    return render_template('node-details.html')

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Start background thread for status checking
    status_thread = threading.Thread(target=check_node_status, daemon=True)
    status_thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True) 