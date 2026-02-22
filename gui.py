import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import logging
from cryptography.fernet import Fernet
from server import VPNServer
from client import VPNClient

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


class VPNApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Academic Encrypted VPN Prototype")
        self.root.geometry("600x400")

        # Initialize key
        self.key = Fernet.generate_key()

        self.server = None
        self.client = None

        # Notebook tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(expand=True, fill="both")

        self.server_tab = ttk.Frame(self.notebook)
        self.client_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.server_tab, text="Server")
        self.notebook.add(self.client_tab, text="Client")

        # Build GUI
        self.build_server_tab()
        self.build_client_tab()

    # ---------------- Server Tab ----------------
    def build_server_tab(self):
        frame = self.server_tab

        ttk.Label(frame, text="Server Port:").pack(pady=5)
        self.server_port_entry = ttk.Entry(frame)
        self.server_port_entry.insert(0, "9000")
        self.server_port_entry.pack(pady=5)

        ttk.Button(frame, text="Start Server", command=self.start_server).pack(pady=5)
        ttk.Button(frame, text="Stop Server", command=self.stop_server).pack(pady=5)
        ttk.Button(frame, text="Generate New Key", command=self.generate_key).pack(pady=5)

        ttk.Label(frame, text="Server Logs:").pack(pady=5)
        self.server_log = scrolledtext.ScrolledText(frame, height=10)
        self.server_log.pack(expand=True, fill="both", padx=5, pady=5)

    # ---------------- Client Tab ----------------
    def build_client_tab(self):
        frame = self.client_tab

        ttk.Label(frame, text="Server IP:").pack(pady=5)
        self.client_ip_entry = ttk.Entry(frame)
        self.client_ip_entry.insert(0, "127.0.0.1")
        self.client_ip_entry.pack(pady=5)

        ttk.Label(frame, text="Server Port:").pack(pady=5)
        self.client_port_entry = ttk.Entry(frame)
        self.client_port_entry.insert(0, "9000")
        self.client_port_entry.pack(pady=5)

        ttk.Button(frame, text="Start Client", command=self.start_client).pack(pady=5)
        ttk.Button(frame, text="Stop Client", command=self.stop_client).pack(pady=5)

        ttk.Label(frame, text="Client Logs:").pack(pady=5)
        self.client_log = scrolledtext.ScrolledText(frame, height=10)
        self.client_log.pack(expand=True, fill="both", padx=5, pady=5)

    # ---------------- Key Generation ----------------
    def generate_key(self):
        self.key = Fernet.generate_key()
        messagebox.showinfo("Key Generated", f"New AES Key Generated:\n{self.key.decode()}")

    # ---------------- Server Control ----------------
    def start_server(self):
        try:
            port = int(self.server_port_entry.get().strip())
            if not (1 <= port <= 65535):
                raise ValueError("Port must be 1-65535")
            self.server = VPNServer("0.0.0.0", port, self.key, log_callback=self.log_server)
            self.server.start()
            self.log_server(f"Server started on port {port}")
        except ValueError as e:
            messagebox.showerror("Invalid Port", str(e))

    def stop_server(self):
        if self.server:
            self.server.stop()
            self.log_server("Server stopped")
            self.server = None

    # ---------------- Client Control ----------------
    def start_client(self):
        try:
            ip = self.client_ip_entry.get().strip()
            port = int(self.client_port_entry.get().strip())
            if not (1 <= port <= 65535):
                raise ValueError("Port must be 1-65535")
            self.client = VPNClient(ip, port, self.key, log_callback=self.log_client)
            self.client.start()
            self.log_client(f"Client started, connecting to {ip}:{port}")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))

    def stop_client(self):
        if self.client:
            self.client.stop()
            self.log_client("Client stopped")
            self.client = None

    # ---------------- Logging ----------------
    def log_server(self, msg):
        self.server_log.insert(tk.END, f"{msg}\n")
        self.server_log.see(tk.END)
        logging.info(msg)

    def log_client(self, msg):
        self.client_log.insert(tk.END, f"{msg}\n")
        self.client_log.see(tk.END)
        logging.info(msg)


if __name__ == "__main__":
    root = tk.Tk()
    app = VPNApp(root)
    root.mainloop()