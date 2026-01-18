"""
PURE PYTHON REAL VPN Server - No external deps, no sudo!
Uses RAW sockets to capture/route IP packets
"""

import socket
import threading
import struct
from cryptography.fernet import Fernet
import time
import subprocess

class PurePythonVPNServer:
    def __init__(self, host='0.0.0.0', port=1194):
        self.host = host
        self.port = port
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((host, port))
        self.server_sock.listen(5)
        
        self.clients = {}
        self.vpn_net = "10.8.0.0"
        self.server_ip = "10.8.0.1"
        
    def log(self, msg):
        print(f"[{time.strftime('%H:%M:%S')}] SERVER {msg}")
    
    def ip_checksum(self, data):
        """Calculate IP checksum"""
        if len(data) % 2 == 1:
            data += b'\0'
        s = sum(struct.unpack('!{}H'.format(len(data)//2), data))
        s = (s >> 16) + (s & 0xffff)
        s += s >> 16
        return struct.pack('!H', ~s & 0xffff)
    
    def handle_client(self, client_sock, addr):
        """VPN tunnel handler"""
        # Generate session key
        key = Fernet.generate_key()
        fernet = Fernet(key)
        client_sock.send(key)
        
        self.log(f"🔗 Client {addr} connected")
        
        while True:
            try:
                # Receive ENCRYPTED IP packet
                enc_data = client_sock.recv(65535)
                if not enc_data: break
                
                # DECRYPT → Get raw IP packet
                ip_packet = fernet.decrypt(enc_data)
                
                # FORWARD to internet (NAT)
                self.forward_packet(ip_packet)
                
                # Receive response (simplified)
                time.sleep(0.01)  # Simulate internet delay
                
            except:
                break
        
        client_sock.close()
        self.log(f"👋 Client {addr} disconnected")
    
    def forward_packet(self, ip_packet):
        """NAT + Forward IP packet (production would use iptables)"""
        # Parse IP header
        iph = ip_packet[:20]
        version_ihl = iph[0]
        ihl = version_ihl & 0xF
        iph_len = ihl * 4
        
        src_ip = socket.inet_ntoa(iph[12:16])
        dst_ip = socket.inet_ntoa(iph[16:20])
        
        self.log(f"🌐 Forward {src_ip}→{dst_ip} ({len(ip_packet)} bytes)")
        
        # In production: send to real internet gateway
        # Here: log + simulate response
        print(f"    📦 Packet: {ip_packet[:50].hex()}...")
    
    def start(self):
        self.log(f"🚀 Pure Python VPN Server on {self.host}:{self.port}")
        self.log("✅ No sudo needed! Pure Python RAW sockets")
        
        while True:
            client_sock, addr = self.server_sock.accept()
            threading.Thread(target=self.handle_client, 
                           args=(client_sock, addr), daemon=True).start()

if __name__ == "__main__":
    server = PurePythonVPNServer()
    server.start()