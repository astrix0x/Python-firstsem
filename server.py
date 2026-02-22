import socket
import threading
import struct
import time
from cryptography.fernet import Fernet, InvalidToken

class EncryptedSocket:
    """Wrapper for socket with AES encryption using Fernet (same as your original)."""
    def __init__(self, sock, key):
        self.sock = sock
        self.fernet = Fernet(key)
        self.recv_buffer = b''
        self.lock = threading.Lock()

    def sendall(self, data):
        while data:
            chunk = data[:4096]
            data = data[4096:]
            encrypted = self.fernet.encrypt(chunk)
            len_bytes = struct.pack('>I', len(encrypted))
            self.sock.sendall(len_bytes + encrypted)

    def recv(self, bufsize):
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
                except Exception:
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


class VPNServer:
    """GUI-compatible encrypted SOCKS5 server."""
    def __init__(self, host, port, key, log_callback=None):
        self.host = host
        self.port = port
        self.key = key
        self.log = log_callback if log_callback else print
        self.stop_event = threading.Event()
        self.server_thread = None
        self.server_sock = None
        self.clients = {}
        self.clients_lock = threading.Lock()

    def start(self):
        self.server_thread = threading.Thread(target=self._run, daemon=True)
        self.server_thread.start()
        self.log(f"Server starting on {self.host}:{self.port}")

    def stop(self):
        self.stop_event.set()
        if self.server_sock:
            self.server_sock.close()
        self.log("Server stopped")

    def _run(self):
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(5)
        except Exception as e:
            self.log(f"Failed to start server: {e}")
            return

        self.log(f"Server listening on {self.host}:{self.port}")

        while not self.stop_event.is_set():
            try:
                self.server_sock.settimeout(1.0)
                client_sock, addr = self.server_sock.accept()
                with self.clients_lock:
                    self.clients[addr] = time.time()
                t = threading.Thread(
                    target=self.handle_connection,
                    args=(client_sock, addr),
                    daemon=True
                )
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                self.log(f"Server error: {e}")
                break

    def handle_connection(self, client_sock, addr):
        self.log(f"New connection from {addr}")
        enc_sock = EncryptedSocket(client_sock, self.key)
        dest_sock = None
        try:
            # SOCKS5 handshake
            data = enc_sock.recv(2)
            if len(data) < 2 or data[0] != 5:
                raise ValueError("Invalid SOCKS5 version")
            nmethods = data[1]
            enc_sock.recv(nmethods)
            enc_sock.sendall(b'\x05\x00')

            # SOCKS5 request
            data = enc_sock.recv(4)
            if len(data) < 4:
                raise ValueError("Incomplete request")
            version, cmd, rsv, atyp = data
            if version != 5 or cmd != 1:
                raise ValueError("Unsupported command")

            if atyp == 1:  # IPv4
                addr_b = enc_sock.recv(4)
                dest_addr = socket.inet_ntoa(addr_b)
            elif atyp == 3:  # Domain
                len_b = enc_sock.recv(1)
                dest_addr = enc_sock.recv(ord(len_b)).decode()
            else:
                raise ValueError("Unsupported address type")

            port_b = enc_sock.recv(2)
            dest_port = struct.unpack('>H', port_b)[0]

            self.log(f"Connecting to {dest_addr}:{dest_port}")
            dest_sock = socket.create_connection((dest_addr, dest_port), timeout=10)

            enc_sock.sendall(b'\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')

            # Bidirectional relay
            def relay(a, b):
                while True:
                    try:
                        data = a.recv(4096)
                        if not data:
                            break
                        b.sendall(data)
                    except:
                        break

            t1 = threading.Thread(target=relay, args=(enc_sock, dest_sock))
            t1.start()
            relay(dest_sock, enc_sock)
            t1.join()

        except Exception as e:
            self.log(f"Error with {addr}: {e}")
        finally:
            client_sock.close()
            if dest_sock:
                dest_sock.close()
            self.log(f"Connection closed from {addr}")
            with self.clients_lock:
                self.clients.pop(addr, None)