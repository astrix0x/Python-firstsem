#!/bin/bash

# Use PORT env variable if set, otherwise default to 9999
PORT=${PORT:-9999}

echo ""
echo "============================================"
echo "        Secure VPN Tunnel - Server          "
echo "============================================"
echo ""

# Get the container IP address
IP=$(hostname -I | awk '{print $1}')

echo "  Server IP   : $IP"
echo "  Server Port : $PORT"
echo ""
echo "  Starting server..."
echo ""

# Run the server - it will print the key automatically
python3 server.py --port $PORT