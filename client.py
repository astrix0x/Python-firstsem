# client.py

import socket
import threading
from cryptography.fernet import Fernet
import struct

# EncryptedSocket class (same as in server.py for consistency)
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

def handle_local_connection(local_sock, addr, remote_host, remote_port, key, log_queue):
    """
    Handle a single local connection: Forward to remote over encrypted channel.
    Does not parse SOCKS5; transparently forwards encrypted.
    """
    log_queue.put(f"Local connection from {addr}")
    remote_sock = None
    try:
        remote_sock = socket.create_connection((remote_host, remote_port), timeout=10)
        enc_remote = EncryptedSocket(remote_sock, key)

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

        while True:
            data = enc_remote.recv(4096)
            if not data:
                break
            local_sock.sendall(data)

        t.join()
    except Exception as e:
        log_queue.put(f"Error in client connection from {addr}: {e}")
    finally:
        local_sock.close()
        if remote_sock:
            remote_sock.close()
        log_queue.put(f"Local connection closed from {addr}")

def run_client(local_host, local_port, remote_host, remote_port, key, log_queue, stop_event):
    """
    Main client loop: Listen locally for SOCKS5 connections, forward each to remote.
    """
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        client_sock.bind((local_host, local_port))
        client_sock.listen(10)
        log_queue.put(f"Client listening on {local_host}:{local_port}")
    except Exception as e:
        log_queue.put(f"Failed to start client: {e}")
        return

    while not stop_event.is_set():
        try:
            client_sock.settimeout(1.0)
            local_sock, addr = client_sock.accept()
            t = threading.Thread(target=handle_local_connection, args=(local_sock, addr, remote_host, remote_port, key, log_queue))
            t.daemon = True
            t.start()
        except socket.timeout:
            continue
        except Exception as e:
            log_queue.put(f"Client error: {e}")
            break

    client_sock.close()
    log_queue.put("Client stopped")

# Limitations: Same as in server.py comments.