#!/bin/bash

# Script to run IoT Monitoring System on Raspberry Pi

echo "Starting IoT Monitoring System..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Please log out and log back in to apply the docker group changes or restart the system."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Installing Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose
fi

# Build and run the Docker container
echo "Building and starting the application..."
docker-compose up -d --build

# Get the Raspberry Pi's IP address
IP_ADDRESS=$(hostname -I | awk '{print $1}')

echo "======================================================"
echo "IoT Monitoring System is now running!"
echo "Access the application at: http://$IP_ADDRESS:5000"
echo "=======================================================" 