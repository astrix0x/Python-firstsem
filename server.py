# server.py

import socket
import threading
import struct
import time
from cryptography.fernet import Fernet, InvalidToken

class EncryptedSocket:
    """
    Wrapper for socket to handle AES encryption/decryption using Fernet.
    Chunks data into messages for encryption, emulates stream with buffering.
    """
    def __init__(self, sock, key):
        self.sock = sock
        self.fernet = Fernet(key)
        self.recv_buffer = b''
        self.lock = threading.Lock()  # For thread safety if needed

    def sendall(self, data):
        """
        Encrypt and send data in chunks of 4096 bytes.
        """
        while data:
            chunk = data[:4096]
            data = data[4096:]
            try:
                encrypted = self.fernet.encrypt(chunk)
            except Exception as e:
                raise ValueError(f"Encryption error: {e}")
            len_bytes = struct.pack('>I', len(encrypted))
            self.sock.sendall(len_bytes + encrypted)

    def recv(self, bufsize):
        """
        Receive and decrypt messages, buffer to emulate stream recv.
        Returns up to bufsize bytes.
        """
        with self.lock:
            while len(self.recv_buffer) < bufsize:
                try:
                    len_bytes = self._read_exact(4)
                    length = struct.unpack('>I', len_bytes)[0]
                    encrypted = self._read_exact(length)
                    decrypted = self.fernet.decrypt(encrypted)
                    self.recv_buffer += decrypted
                except (EOFError, InvalidToken):
                    break
                except Exception as e:
                    break
            data = self.recv_buffer[:bufsize]
            self.recv_buffer = self.recv_buffer[bufsize:]
            return data

    def _read_exact(self, n):
        buf = b''
        while len(buf) < n:
            more = self.sock.recv(n - len(buf))
            if not more:
                raise EOFError("Unexpected end of stream")
            buf += more
        return buf

    def close(self):
        self.sock.close()

def handle_connection(client_sock, addr, key, log_queue, clients, clients_queue, clients_lock):
    """
    Handle a single encrypted SOCKS5 connection.
    Decrypts stream, processes SOCKS5, forwards to destination.
    """
    log_queue.put(f"New connection from {addr}")
    enc_sock = EncryptedSocket(client_sock, key)
    dest_sock = None
    try:
        # SOCKS5 greeting
        data = enc_sock.recv(2)
        if len(data) < 2 or data[0] != 5:
            raise ValueError("Invalid SOCKS5 version")
        nmethods = data[1]
        enc_sock.recv(nmethods)  # Read methods, ignore since no auth
        enc_sock.sendall(b'\x05\x00')  # No authentication

        # SOCKS5 request
        data = enc_sock.recv(4)
        if len(data) < 4:
            raise ValueError("Incomplete request")
        version, cmd, rsv, atyp = data
        if version != 5 or cmd != 1:
            raise ValueError("Unsupported SOCKS5 command")
        if atyp == 1:  # IPv4
            addr_b = enc_sock.recv(4)
            if len(addr_b) < 4:
                raise ValueError("Incomplete address")
            dest_addr = socket.inet_ntoa(addr_b)
        elif atyp == 3:  # Domain name
            len_b = enc_sock.recv(1)
            if len(len_b) < 1:
                raise ValueError("Incomplete domain length")
            dest_addr = enc_sock.recv(ord(len_b)).decode('utf-8')
        else:
            raise ValueError("Unsupported address type")
        port_b = enc_sock.recv(2)
        if len(port_b) < 2:
            raise ValueError("Incomplete port")
        dest_port = struct.unpack('>H', port_b)[0]

        log_queue.put(f"Connecting to {dest_addr}:{dest_port}")

        # Connect to destination
        dest_sock = socket.create_connection((dest_addr, dest_port), timeout=10)

        # Send success response (bound to 0.0.0.0:0)
        enc_sock.sendall(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')

        # Bidirectional relay
        def relay_a_to_b(a, b):
            while True:
                try:
                    data = a.recv(4096)
                    if not data:
                        break
                    b.sendall(data)
                except:
                    break

        t1 = threading.Thread(target=relay_a_to_b, args=(enc_sock, dest_sock))
        t1.start()
        relay_a_to_b(dest_sock, enc_sock)
        t1.join()

    except Exception as e:
        log_queue.put(f"Error handling connection from {addr}: {e}")
        if not dest_sock:  # If before response, send failure
            try:
                enc_sock.sendall(b'\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00')
            except:
                pass
    finally:
        client_sock.close()
        if dest_sock:
            dest_sock.close()
        log_queue.put(f"Connection closed from {addr}")
        with clients_lock:
            clients.pop(addr, None)
            clients_queue.put(dict(clients))  # Copy for queue

def run_server(host, port, key, log_queue, stop_event, clients_queue):
    """
    Main server loop: Listen for connections, spawn threads for handling.
    """
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server_sock.bind((host, port))
        server_sock.listen(5)
        log_queue.put(f"Server listening on {host}:{port}")
    except Exception as e:
        log_queue.put(f"Failed to start server: {e}")
        return

    clients = {}
    clients_lock = threading.Lock()

    while not stop_event.is_set():
        try:
            server_sock.settimeout(1.0)
            client_sock, addr = server_sock.accept()
            with clients_lock:
                clients[addr] = time.time()
                clients_queue.put(dict(clients))
            t = threading.Thread(target=handle_connection, args=(client_sock, addr, key, log_queue, clients, clients_queue, clients_lock))
            t.daemon = True
            t.start()
        except socket.timeout:
            continue
        except Exception as e:
            log_queue.put(f"Server error: {e}")
            break

    server_sock.close()
    log_queue.put("Server stopped")

# Limitations compared to OpenVPN and WireGuard:
# - This is a simple TCP-based tunnel with manual key sharing; no automated key exchange, certificates, or diffie-hellman for forward secrecy.
# - Uses TCP only, which can suffer from head-of-line blocking; no UDP support for lower latency and better performance in lossy networks.
# - Encryption is message-based with overhead (padding, HMAC), less efficient than stream ciphers in WireGuard.
# - Python implementation is slower and not optimized for high throughput compared to native C implementations.
# - No advanced features like IP routing, NAT traversal, compression, or multi-protocol support.
# - Lacks robust error handling, reconnection logic, and security audits; for academic demonstration only, not production use.
# - If the shared key is compromised, all past and future sessions can be decrypted (no PFS).