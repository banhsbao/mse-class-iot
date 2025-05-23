from flask import Flask, jsonify, request, render_template
import sqlite3
import threading
import time
import random
import json
from datetime import datetime
import os
import requests
from gradio_client import Client

app = Flask(__name__)

# Configuration
DATABASE = os.environ.get('DATABASE', 'iot.db')
DUMMY_DATA_ENABLED = False
WEBHOOK_ENABLED = True  # New config for webhook
EMAIL_ENABLED = True    # New config for email notifications

# Mailgun configuration
MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY', '')
MAILGUN_DOMAIN = os.environ.get('MAILGUN_DOMAIN', '')
MAILGUN_SENDER = os.environ.get('MAILGUN_SENDER', '')
EMAIL_RATE_LIMIT = 60  # seconds

# Gradio client
try:
    GRADIO_CLIENT = Client("https://datdang-water-quality-predict.hf.space")
except Exception as e:
    print(f"Warning: Could not initialize Gradio client: {e}")
    GRADIO_CLIENT = None

def predict_water_quality(tds, ph, humidity, temperature):
    try:
        if GRADIO_CLIENT is None:
            # Fallback logic if Gradio client is not available
            if tds > 1000 or ph < 6.5 or ph > 8.5:
                return 'BAD'
            elif tds > 500 or ph < 7.0 or ph > 8.0:
                return 'WARNING'
            else:
                return 'GOOD'
                
        # Try to get prediction from Gradio
        prediction = GRADIO_CLIENT.predict(
            tds,
            ph,
            humidity,
            temperature,
            api_name="/predict"
        )
        return prediction
    except Exception as e:
        print(f"Error predicting water quality: {e}")
        # Fallback to basic logic
        if tds > 1000 or ph < 6.5 or ph > 8.5:
            return 'BAD'
        elif tds > 500 or ph < 7.0 or ph > 8.0:
            return 'WARNING'
        else:
            return 'GOOD'

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
    
    # Create email_recipients table
    c.execute('''
    CREATE TABLE IF NOT EXISTS email_recipients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        last_notified TIMESTAMP
    )
    ''')
    
    for i in range(1, 21):
        node_id = f"node_{i}"
        c.execute("INSERT OR IGNORE INTO nodes (node_id, latitude, longitude, last_updated) VALUES (?, ?, ?, ?)",
                 (node_id, 10.0 + random.random(), 106.0 + random.random(), datetime.now()))
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DATABASE}")

# Function to send email notification
def send_email_notification(node_id, status):
    if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
        print("Mailgun configuration is incomplete. Skipping email notification.")
        return
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get recipients that haven't been notified in the last EMAIL_RATE_LIMIT seconds
    current_time = datetime.now()
    rate_limit_time = current_time.timestamp() - EMAIL_RATE_LIMIT
    
    c.execute('''
    SELECT email, last_notified FROM email_recipients
    WHERE last_notified IS NULL OR last_notified < ?
    ''', (rate_limit_time,))
    
    recipients = c.fetchall()
    
    if not recipients:
        conn.close()
        return
    
    # Prepare email content
    subject = f"🔥 URGENT: Node {node_id} Status = {status} – Investigate Now"
    text = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f5f5f5; color: #333333; padding: 20px;">
            <div style="max-width: 700px; margin: auto; border: 2px solid #ff4d4f; border-radius: 10px; padding: 20px; background-color: #ffffff;">
            <h2 style="color: #ff4d4f;">🚨 SYSTEM ALERT – CRITICAL NODE STATUS 🚨</h2>

            <p><strong>⚠️ Alert Code:</strong> #AX-NODE-FAILURE</p>
            <p><strong>Node ID:</strong> {node_id}</p>
            <p><strong>Status Reported:</strong> {status}</p>
            <p><strong>Timestamp:</strong> {current_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Severity:</strong> <span style="color: #ff4d4f;">🟥 HIGH</span></p>

            <hr style="border-color: #e0e0e0;" />

            <h3 style="color: #fa8c16;">🧠 Contextual Analysis</h3>
            <p>
                Our anomaly detection engine has intercepted an irregular activity pattern originating from Node <strong>{node_id}</strong>.
                The reported status of <strong>{status}</strong> indicates a possible deviation from standard operational thresholds.
                This could be an early indicator of:
            </p>
            <ul>
                <li>Power instability</li>
                <li>Firmware corruption</li>
                <li>Environmental anomaly (e.g., temp spike, humidity breach)</li>
                <li>Malicious access attempt or unauthorized tampering</li>
            </ul>
            <p>This alert was auto-generated by the <strong>Sentinel Aegis Monitoring Framework</strong>, operating under enhanced surveillance protocols.</p>

            <h3 style="color: #1890ff;">💡 Recommended Actions</h3>
            <ol>
                <li>Log into the <strong>IoT Monitoring Console</strong> immediately. <br />(Console &gt; Nodes &gt; <strong>{node_id}</strong>)</li>
                <li>Run diagnostics or isolate the node if critical thresholds are being exceeded.</li>
                <li>Escalate to Engineering or CyberSec Ops if tampering or persistent faults are detected.</li>
            </ol>

            <p style="color: #ff4d4f;"><strong>🛡 This is not a drill.</strong><br />
            Infrastructure integrity depends on rapid response. Every second counts. Our system will continue to monitor this node for escalation or recovery signals.</p>

            <blockquote style="color: #555555; font-style: italic; border-left: 4px solid #cccccc; padding-left: 15px;">
                "The quiet before failure is never silence — it's a whisper. This was that whisper."
            </blockquote>

            <p style="text-align: right;">— End of transmission —</p>
            </div>
        </body>
        </html>
        """
    # Send email to each recipient
    for recipient in recipients:
        try:
            response = requests.post(
                f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
                auth=("api", MAILGUN_API_KEY),
                data={
                    "from": MAILGUN_SENDER,
                    "to": recipient['email'],
                    "subject": subject,
                    "html": text
                }
            )
            
            # Update last notified timestamp
            if response.status_code == 200:
                c.execute('''
                UPDATE email_recipients
                SET last_notified = ?
                WHERE email = ?
                ''', (current_time.timestamp(), recipient['email']))
                
                print(f"Email sent to {recipient['email']} for node {node_id}")
            else:
                print(f"Failed to send email to {recipient['email']}: {response.text}")
                
        except Exception as e:
            print(f"Error sending email to {recipient['email']}: {str(e)}")
    
    conn.commit()
    conn.close()

def generate_dummy_data():
    while DUMMY_DATA_ENABLED:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        c.execute("SELECT node_id FROM nodes")
        nodes = c.fetchall()
        
        for node in nodes:
            node_id = node[0]
            tds = random.uniform(100, 500)
            ph = random.uniform(6.0, 8.5)
            humidity = random.uniform(30, 90)
            temp = random.uniform(20, 35)            
            status = random.choices(['GOOD', 'WARNING', 'BAD'], [0.7, 0.2, 0.1])[0]
            
            c.execute('''
            INSERT INTO sensor_data (node_id, tds, ph, humidity, temp, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (node_id, tds, ph, humidity, temp, status, datetime.now()))
        
        conn.commit()
        conn.close()
        time.sleep(1)
    print("Dummy data generation stopped")

def check_node_status():
    while True:
        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()
        
        c.execute('''
        SELECT DISTINCT s.node_id 
        FROM sensor_data s 
        WHERE s.status IS NULL
        ''')
        
        nodes_to_update = c.fetchall()
        
        for node in nodes_to_update:
            node_id = node[0]
            
            status = random.choices(['GOOD', 'WARNING', 'BAD'], [0.7, 0.2, 0.1])[0]
            
            c.execute('''
            UPDATE sensor_data
            SET status = ?
            WHERE node_id = ? AND status IS NULL
            ''', (status, node_id))
            
            if status == 'BAD':
                send_email_notification(node_id, status)
            
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
           sd.tds, sd.ph, sd.humidity, sd.temp, sd.status, sd.timestamp
    FROM nodes n
    LEFT JOIN (
        SELECT s.node_id, s.tds, s.ph, s.humidity, s.temp, s.status, s.timestamp,
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

@app.route('/api/email-recipients', methods=['GET'])
def get_email_recipients():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT id, email FROM email_recipients')
    recipients = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify(recipients)

@app.route('/api/email-recipients', methods=['POST'])
def add_email_recipient():
    data = request.json
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
    
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        c.execute('INSERT INTO email_recipients (email) VALUES (?)', (email,))
        conn.commit()
        new_id = c.lastrowid
        conn.close()
        
        return jsonify({"id": new_id, "email": email}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({"error": "Email already exists"}), 409
    except Exception as e:
        conn.close()
        return jsonify({"error": str(e)}), 500

@app.route('/api/email-recipients/<int:recipient_id>', methods=['DELETE'])
def delete_email_recipient(recipient_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    c.execute('SELECT id FROM email_recipients WHERE id = ?', (recipient_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({"error": "Recipient not found"}), 404
    
    c.execute('DELETE FROM email_recipients WHERE id = ?', (recipient_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True}), 200

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

@app.route('/email-settings')
def email_settings():
    return render_template('email-settings.html')

@app.route('/api/webhook/data', methods=['POST'])
def webhook_data():
    if not WEBHOOK_ENABLED:
        return jsonify({"error": "Webhook is disabled"}), 403
        
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        for node in data:
            node_id = node.get('nodeId')
            node_data = node.get('data', [])
            
            for measurement in node_data:
                # Check if node exists
                c.execute('SELECT node_id FROM nodes WHERE node_id = ?', (node_id,))
                if not c.fetchone():
                    # Add new node with random coordinates near Ho Chi Minh City
                    lat = 10.0 + random.random()
                    lon = 106.0 + random.random()
                    c.execute('''
                    INSERT INTO nodes (node_id, latitude, longitude, last_updated)
                    VALUES (?, ?, ?, ?)
                    ''', (node_id, lat, lon, datetime.now()))
                
                # Get water quality prediction
                prediction = predict_water_quality(
                    measurement.get('tds', 0),
                    measurement.get('ph', 0),
                    measurement.get('humidity', 0),
                    measurement.get('temperature', 0)
                )
                
                # Insert sensor data with prediction as status
                c.execute('''
                INSERT INTO sensor_data 
                (node_id, tds, ph, humidity, temp, status, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    node_id,
                    measurement.get('tds'),
                    measurement.get('ph'),
                    measurement.get('humidity'),
                    measurement.get('temperature'),
                    prediction,
                    datetime.fromtimestamp(measurement.get('timestamp'))
                ))
                
                # Send email notification if status is BAD and email is enabled
                if prediction == 'BAD' and EMAIL_ENABLED:
                    send_email_notification(node_id, prediction)
        
        conn.commit()
        return jsonify({"message": "Data updated"})
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/webhook/toggle', methods=['POST'])
def toggle_webhook():
    global WEBHOOK_ENABLED
    data = request.json
    if 'enabled' in data:
        WEBHOOK_ENABLED = data['enabled']
        return jsonify({"webhook_enabled": WEBHOOK_ENABLED})
    return jsonify({"error": "Missing enabled parameter"}), 400

@app.route('/api/email/toggle', methods=['POST'])
def toggle_email():
    global EMAIL_ENABLED
    data = request.json
    if 'enabled' in data:
        EMAIL_ENABLED = data['enabled']
        return jsonify({"email_enabled": EMAIL_ENABLED})
    return jsonify({"error": "Missing enabled parameter"}), 400

@app.route('/api/settings/status', methods=['GET'])
def get_settings_status():
    return jsonify({
        "webhook_enabled": WEBHOOK_ENABLED,
        "email_enabled": EMAIL_ENABLED,
        "dummy_data_enabled": DUMMY_DATA_ENABLED
    })

@app.route('/api/nodes/<node_id>', methods=['PUT'])
def update_node(node_id):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        # Check if node exists
        c.execute('SELECT node_id FROM nodes WHERE node_id = ?', (node_id,))
        if not c.fetchone():
            return jsonify({"error": "Node not found"}), 404
            
        # Update node information
        c.execute('''
        UPDATE nodes 
        SET latitude = ?, longitude = ?, last_updated = ?
        WHERE node_id = ?
        ''', (data.get('latitude'), data.get('longitude'), datetime.now(), node_id))
        
        conn.commit()
        return jsonify({"message": "Node updated successfully"})
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/nodes', methods=['POST'])
def create_node():
    data = request.json
    if not data or 'node_id' not in data:
        return jsonify({"error": "Node ID is required"}), 400
        
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        # Check if node already exists
        c.execute('SELECT node_id FROM nodes WHERE node_id = ?', (data['node_id'],))
        if c.fetchone():
            return jsonify({"error": "Node ID already exists"}), 409
            
        # Create new node
        c.execute('''
        INSERT INTO nodes (node_id, latitude, longitude, last_updated)
        VALUES (?, ?, ?, ?)
        ''', (
            data['node_id'],
            data.get('latitude', 10.0 + random.random()),  # Default to random location near HCMC
            data.get('longitude', 106.0 + random.random()),
            datetime.now()
        ))
        
        conn.commit()
        return jsonify({"message": "Node created successfully"}), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/nodes/<node_id>', methods=['DELETE'])
def delete_node(node_id):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    
    try:
        # Check if node exists
        c.execute('SELECT node_id FROM nodes WHERE node_id = ?', (node_id,))
        if not c.fetchone():
            return jsonify({"error": "Node not found"}), 404
            
        # Delete node and its sensor data
        c.execute('DELETE FROM sensor_data WHERE node_id = ?', (node_id,))
        c.execute('DELETE FROM nodes WHERE node_id = ?', (node_id,))
        
        conn.commit()
        return jsonify({"message": "Node deleted successfully"})
        
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/node-management')
def node_management():
    return render_template('node-management.html')

if __name__ == '__main__':
    init_db()    
    status_thread = threading.Thread(target=check_node_status, daemon=True)
    status_thread.start() 
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True) 