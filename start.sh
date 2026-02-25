#!/bin/bash

echo ""
echo "============================================"
echo "        Secure VPN Tunnel - Server          "
echo "============================================"
echo ""


IP=$(hostname -I | awk '{print $1}')

echo "  Server IP   : $IP"
echo "  Server Port : 9999"
echo ""
echo "  Starting server..."
echo ""


python3 server.py --port 9999
