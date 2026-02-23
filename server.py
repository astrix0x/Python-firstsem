"""
server.py - VPN Server
Run this on Kali Linux.

How it works:
- Listens for encrypted connections from the client
- Client sends SOCKS5 requests through the encrypted tunnel
- Server connects to the real website on behalf of the client
- All traffic exits from Kali's IP, not the client's IP

Usage:
    python3 server.py
"""

import socket
import struct
import threading
from cryptography.fernet import Fernet, InvalidToken


# ── Encryption ────────────────────────────────────────────────────────────────

class EncryptedSocket:
    """Wraps a TCP socket with AES-128 encryption (Fernet).
    
    Every message is sent as: [4-byte length][encrypted data]
    This framing is needed because TCP is a stream with no message boundaries.
    """

    def __init__(self, sock, key: bytes):
        self.sock   = sock
        self.fernet = Fernet(key)

    def send(self, data: bytes):
        encrypted = self.fernet.encrypt(data)
        self.sock.sendall(struct.pack(">I", len(encrypted)) + encrypted)

    def recv(self) -> bytes:
        length = struct.unpack(">I", self._read_exact(4))[0]
        return self.fernet.decrypt(self._read_exact(length))

    def _read_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise EOFError("Connection closed")
            buf += chunk
        return buf

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


# ── Client handler ────────────────────────────────────────────────────────────

def handle_client(client_sock, addr, key, log):
    log(f"Connection from {addr[0]}:{addr[1]}")
    enc      = EncryptedSocket(client_sock, key)
    dst_sock = None

    try:
        # SOCKS5 greeting: VER NMETHODS METHODS...
        header = enc.recv()
        if not header or header[0] != 5:
            raise ValueError("Not a SOCKS5 connection")
        enc.send(b"\x05\x00")  # accept, no auth

        # SOCKS5 request: VER CMD RSV ATYP [addr] PORT
        req = enc.recv()
        if len(req) < 4 or req[0] != 5 or req[1] != 1:
            raise ValueError("Only SOCKS5 CONNECT supported")

        atyp = req[3]
        if atyp == 1:      # IPv4 - 4 bytes
            dst_host = socket.inet_ntoa(req[4:8])
            dst_port = struct.unpack(">H", req[8:10])[0]
        elif atyp == 3:    # Domain - 1 byte length + domain
            dlen     = req[4]
            dst_host = req[5:5 + dlen].decode()
            dst_port = struct.unpack(">H", req[5 + dlen:7 + dlen])[0]
        elif atyp == 4:    # IPv6 - 16 bytes
            dst_host = socket.inet_ntop(socket.AF_INET6, req[4:20])
            dst_port = struct.unpack(">H", req[20:22])[0]
        else:
            raise ValueError(f"Unknown address type: {atyp}")

        log(f"  {addr[0]} -> {dst_host}:{dst_port}")

        # Connect to real destination
        dst_sock = socket.create_connection((dst_host, dst_port), timeout=10)

        # SOCKS5 success reply
        enc.send(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")

        # Relay traffic in both directions
        stop = threading.Event()

        def client_to_dst():
            while not stop.is_set():
                try:
                    data = enc.recv()
                    if not data:
                        break
                    dst_sock.sendall(data)
                except Exception:
                    break
            stop.set()

        def dst_to_client():
            while not stop.is_set():
                try:
                    data = dst_sock.recv(4096)
                    if not data:
                        break
                    enc.send(data)
                except Exception:
                    break
            stop.set()

        t1 = threading.Thread(target=client_to_dst, daemon=True)
        t2 = threading.Thread(target=dst_to_client, daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    except Exception as e:
        log(f"Error ({addr[0]}): {e}")
    finally:
        enc.close()
        if dst_sock:
            try:
                dst_sock.close()
            except OSError:
                pass
        log(f"Closed {addr[0]}:{addr[1]}")


# ── Server ────────────────────────────────────────────────────────────────────

class VPNServer:
    def __init__(self, port: int, key: bytes, log=None):
        self.port  = port
        self.key   = key
        self.log   = log or print
        self._stop = threading.Event()
        self._sock = None

    def start(self):
        self._stop.clear()
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._stop.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass

    def _run(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._sock.bind(("0.0.0.0", self.port))
            self._sock.listen(10)
        except OSError as e:
            self.log(f"Cannot start server: {e}")
            return

        self.log(f"Server started on port {self.port}")
        self.log(f"Waiting for client connections...")

        while not self._stop.is_set():
            try:
                self._sock.settimeout(1.0)
                conn, addr = self._sock.accept()
                threading.Thread(
                    target=handle_client,
                    args=(conn, addr, self.key, self.log),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except OSError:
                break

        self.log("Server stopped.")