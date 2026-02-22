import socket
import threading
from cryptography.fernet import Fernet
import struct

class EncryptedSocket:
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
                except:
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


class VPNClient:
    """GUI-compatible encrypted SOCKS5 client."""
    def __init__(self, server_ip, server_port, key, log_callback=None, local_port=1080):
        self.server_ip = server_ip
        self.server_port = server_port
        self.key = key
        self.local_port = local_port
        self.log = log_callback if log_callback else print
        self.stop_event = threading.Event()
        self.client_thread = None

    def start(self):
        self.client_thread = threading.Thread(target=self._run, daemon=True)
        self.client_thread.start()
        self.log(f"Client starting on 127.0.0.1:{self.local_port}")

    def stop(self):
        self.stop_event.set()
        self.log("Client stopped")

    def _run(self):
        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            client_sock.bind(("127.0.0.1", self.local_port))
            client_sock.listen(10)
            self.log(f"Client listening locally on 127.0.0.1:{self.local_port}")
        except Exception as e:
            self.log(f"Failed to start client: {e}")
            return

        while not self.stop_event.is_set():
            try:
                client_sock.settimeout(1.0)
                local_sock, addr = client_sock.accept()
                t = threading.Thread(
                    target=self.handle_local_connection,
                    args=(local_sock, addr),
                    daemon=True
                )
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                self.log(f"Client error: {e}")
                break

        client_sock.close()
        self.log("Client stopped")

    def handle_local_connection(self, local_sock, addr):
        self.log(f"Local connection from {addr}")
        remote_sock = None
        try:
            remote_sock = socket.create_connection((self.server_ip, self.server_port), timeout=10)
            enc_remote = EncryptedSocket(remote_sock, self.key)

            # Relay local -> remote
            def relay_local_to_remote():
                while True:
                    try:
                        data = local_sock.recv(4096)
                        if not data:
                            break
                        enc_remote.sendall(data)
                    except:
                        break
                try:
                    remote_sock.shutdown(socket.SHUT_WR)
                except:
                    pass

            t = threading.Thread(target=relay_local_to_remote)
            t.daemon = True
            t.start()

            # Relay remote -> local
            while True:
                data = enc_remote.recv(4096)
                if not data:
                    break
                local_sock.sendall(data)

            t.join()
        except Exception as e:
            self.log(f"Error in client connection from {addr}: {e}")
        finally:
            local_sock.close()
            if remote_sock:
                remote_sock.close()
            self.log(f"Local connection closed from {addr}")