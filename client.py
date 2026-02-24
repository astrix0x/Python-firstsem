import socket
import struct
import threading
from cryptography.fernet import Fernet, InvalidToken



class EncryptedSocket:
    """Wraps a TCP socket with AES-128 encryption (Fernet)."""

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


# Per-connection handler

def handle_browser(browser_sock, addr, server_ip, server_port, key, log):
    """Handle one browser connection — tunnel it through the VPN server."""
    log(f"Browser connected from {addr[0]}:{addr[1]}")
    tunnel = None

    try:
        # Open encrypted tunnel to VPN server
        raw = socket.create_connection((server_ip, server_port), timeout=10)
        tunnel = EncryptedSocket(raw, key)

        # Read SOCKS5 greeting from browser and forward it encrypted to server
        greeting = _read_exact(browser_sock, 2)
        nmethods = greeting[1]
        methods  = _read_exact(browser_sock, nmethods)
        tunnel.send(greeting + methods)

        # Get server's reply and forward to browser
        reply = tunnel.recv()
        browser_sock.sendall(reply)

        # Read browser's CONNECT request and forward encrypted to server
        request = _read_socks5_request(browser_sock)
        tunnel.send(request)

        # Get server's success reply and forward to browser
        response = tunnel.recv()
        browser_sock.sendall(response)

        if len(response) < 2 or response[1] != 0:
            raise ConnectionError("Server rejected the connection request")

        # Now relay all data in both directions
        stop = threading.Event()

        def browser_to_server():
            while not stop.is_set():
                try:
                    data = browser_sock.recv(4096)
                    if not data:
                        break
                    tunnel.send(data)
                except Exception:
                    break
            stop.set()

        def server_to_browser():
            while not stop.is_set():
                try:
                    data = tunnel.recv()
                    if not data:
                        break
                    browser_sock.sendall(data)
                except Exception:
                    break
            stop.set()

        t1 = threading.Thread(target=browser_to_server, daemon=True)
        t2 = threading.Thread(target=server_to_browser, daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

    except ConnectionRefusedError:
        log(f"Cannot reach server at {server_ip}:{server_port} - is the server running?")
    except Exception as e:
        log(f"Error: {e}")
    finally:
        try:
            browser_sock.close()
        except OSError:
            pass
        if tunnel:
            tunnel.close()
        log(f"Closed {addr[0]}:{addr[1]}")


def _read_exact(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise EOFError("Browser closed connection")
        buf += chunk
    return buf


def _read_socks5_request(sock):
    """Read a full SOCKS5 request from the browser."""
    header = _read_exact(sock, 4)
    atyp   = header[3]
    if atyp == 1:      # IPv4
        rest = _read_exact(sock, 4 + 2)
    elif atyp == 3:    # Domain
        dlen = _read_exact(sock, 1)
        rest = dlen + _read_exact(sock, dlen[0] + 2)
    elif atyp == 4:    # IPv6
        rest = _read_exact(sock, 16 + 2)
    else:
        rest = b""
    return header + rest


# Client 
class VPNClient:
    def __init__(self, server_ip, server_port, key, local_port=1080, log=None):
        self.server_ip   = server_ip
        self.server_port = server_port
        self.key         = key
        self.local_port  = local_port
        self.log         = log or print
        self._stop       = threading.Event()
        self._sock       = None

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
            self._sock.bind(("127.0.0.1", self.local_port))
            self._sock.listen(10)
        except OSError as e:
            self.log(f"Cannot start client: {e}")
            return

        self.log(f"Client started - listening on 127.0.0.1:{self.local_port}")
        self.log(f"Set your browser SOCKS5 proxy to 127.0.0.1:{self.local_port}")

        while not self._stop.is_set():
            try:
                self._sock.settimeout(1.0)
                browser_sock, addr = self._sock.accept()
                threading.Thread(
                    target=handle_browser,
                    args=(browser_sock, addr,
                          self.server_ip, self.server_port,
                          self.key, self.log),
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except OSError:
                break

        self.log("Client stopped.")