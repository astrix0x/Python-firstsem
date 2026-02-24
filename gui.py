import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import os
from cryptography.fernet import Fernet

from server import VPNServer
from client import VPNClient

KEY_FILE = "vpn.key"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("VPN")
        self.root.geometry("700x600")
        self.root.resizable(True, True)

        self._server = None
        self._client = None
        self._key    = None
        self._queue  = queue.Queue()

        self._build()
        self._poll()
        self._load_key()

    def _build(self):
        nb = ttk.Notebook(self.root)
        nb.pack(fill="both", expand=True, padx=6, pady=6)

        srv_tab = ttk.Frame(nb)
        cli_tab = ttk.Frame(nb)
        nb.add(srv_tab, text="Server")
        nb.add(cli_tab, text="Client")

        self._build_server(srv_tab)
        self._build_client(cli_tab)

        self._status = tk.StringVar(value="Ready.")
        tk.Button(self.root, text="Exit", command=self._exit, width=10).pack(side="bottom", pady=(0, 4))
        tk.Label(self.root, textvariable=self._status,
                 relief="sunken", anchor="w",
                 font=("TkDefaultFont", 8)).pack(fill="x", side="bottom")

    def _build_server(self, f):
        ttk.Separator(f, orient="horizontal").pack(fill="x", padx=10, pady=(14, 8))

        # Port
        row = tk.Frame(f)
        row.pack(anchor="w", padx=10)
        tk.Label(row, text="Port:", width=10, anchor="w").pack(side="left")
        self._srv_port = tk.StringVar(value="9000")
        tk.Entry(row, textvariable=self._srv_port, width=10).pack(side="left")

        # Buttons
        btn = tk.Frame(f)
        btn.pack(anchor="w", padx=10, pady=6)
        self._btn_srv_start = tk.Button(btn, text="Start Server",
                                        command=self._start_server, width=14)
        self._btn_srv_start.pack(side="left", padx=(0, 4))
        self._btn_srv_stop = tk.Button(btn, text="Stop Server",
                                       command=self._stop_server,
                                       width=14, state="disabled")
        self._btn_srv_stop.pack(side="left")

        # Status
        self._srv_status = tk.StringVar(value="Stopped")
        tk.Label(f, textvariable=self._srv_status).pack(anchor="w", padx=10)

        ttk.Separator(f, orient="horizontal").pack(fill="x", padx=10, pady=8)

        # Key
        tk.Label(f, text="Encryption Key:").pack(anchor="w", padx=10)
        key_row = tk.Frame(f)
        key_row.pack(fill="x", padx=10, pady=4)
        self._key_var = tk.StringVar()
        tk.Entry(key_row, textvariable=self._key_var,
                 state="readonly", font=("Courier", 8)).pack(
            side="left", fill="x", expand=True)
        tk.Button(key_row, text="Copy",
                  command=self._copy_key, width=6).pack(side="left", padx=(4, 0))

        tk.Button(f, text="Generate New Key",
                  command=self._new_key).pack(anchor="w", padx=10, pady=(4, 0))

        ttk.Separator(f, orient="horizontal").pack(fill="x", padx=10, pady=8)

        tk.Label(f, text="Log:").pack(anchor="w", padx=10)
        self._srv_log = scrolledtext.ScrolledText(
            f, height=7, state="disabled", font=("Courier", 8))
        self._srv_log.pack(fill="both", expand=True, padx=10, pady=(0, 6))

    def _build_client(self, f):
        ttk.Separator(f, orient="horizontal").pack(fill="x", padx=10, pady=(14, 8))

        # Fields
        fields = tk.Frame(f)
        fields.pack(anchor="w", padx=10)

        tk.Label(fields, text="Server IP:",
                 width=12, anchor="w").grid(row=0, column=0, pady=3)
        self._cli_ip = tk.StringVar(value="")
        tk.Entry(fields, textvariable=self._cli_ip,
                 width=28).grid(row=0, column=1, sticky="w")

        tk.Label(fields, text="Server Port:",
                 width=12, anchor="w").grid(row=1, column=0, pady=3)
        self._cli_port = tk.StringVar(value="9000")
        tk.Entry(fields, textvariable=self._cli_port,
                 width=8).grid(row=1, column=1, sticky="w")

        tk.Label(fields, text="Local Port:",
                 width=12, anchor="w").grid(row=2, column=0, pady=3)
        self._cli_local = tk.StringVar(value="1080")
        tk.Entry(fields, textvariable=self._cli_local,
                 width=8).grid(row=2, column=1, sticky="w")

        tk.Label(fields, text="Key:",
                 width=12, anchor="w").grid(row=3, column=0, pady=3)
        self._cli_key = tk.StringVar()
        tk.Entry(fields, textvariable=self._cli_key,
                 font=("Courier", 8), width=36).grid(row=3, column=1, sticky="w")

        # Buttons
        btn = tk.Frame(f)
        btn.pack(anchor="w", padx=10, pady=6)
        self._btn_cli_start = tk.Button(btn, text="Connect",
                                        command=self._start_client, width=14)
        self._btn_cli_start.pack(side="left", padx=(0, 4))
        self._btn_cli_stop = tk.Button(btn, text="Disconnect",
                                       command=self._stop_client,
                                       width=14, state="disabled")
        self._btn_cli_stop.pack(side="left")

        # Status
        self._cli_status = tk.StringVar(value="Disconnected")
        tk.Label(f, textvariable=self._cli_status).pack(anchor="w", padx=10)

        ttk.Separator(f, orient="horizontal").pack(fill="x", padx=10, pady=6)

        tk.Label(f, text="Log:").pack(anchor="w", padx=10)
        self._cli_log = scrolledtext.ScrolledText(
            f, height=7, state="disabled", font=("Courier", 8))
        self._cli_log.pack(fill="both", expand=True, padx=10, pady=(0, 6))

    #  Server actions
    def _start_server(self):
        try:
            port = int(self._srv_port.get().strip())
            assert 1 <= port <= 65535
        except Exception:
            messagebox.showerror("Error", "Enter a valid port number (1-65535).")
            return

        if not self._key:
            self._load_or_create_key()

        def log(msg):
            self._queue.put(("srv", msg))

        self._server = VPNServer(port, self._key, log=log)
        self._server.start()

        self._srv_status.set("Running on port " + str(port))
        self._btn_srv_start.config(state="disabled")
        self._btn_srv_stop.config(state="normal")
        self._status.set(f"Server running on port {port}.")

    def _stop_server(self):
        if self._server:
            self._server.stop()
            self._server = None
        self._srv_status.set("Stopped")
        self._btn_srv_start.config(state="normal")
        self._btn_srv_stop.config(state="disabled")
        self._status.set("Server stopped.")

    # Client actions 
    def _start_client(self):
        ip = self._cli_ip.get().strip()
        if not ip:
            messagebox.showerror("Error", "Enter the server IP address.")
            return

        try:
            port       = int(self._cli_port.get().strip())
            local_port = int(self._cli_local.get().strip())
            assert 1 <= port <= 65535
            assert 1 <= local_port <= 65535
        except Exception:
            messagebox.showerror("Error", "Enter valid port numbers.")
            return

        raw_key = self._cli_key.get().strip()
        if not raw_key:
            messagebox.showerror("Error", "Enter the encryption key.")
            return
        try:
            key = raw_key.encode()
            Fernet(key)
        except Exception:
            messagebox.showerror("Error", "Invalid key. Copy it exactly from the Server tab.")
            return

        def log(msg):
            self._queue.put(("cli", msg))

        self._client = VPNClient(ip, port, key, local_port, log=log)
        self._client.start()

        self._cli_status.set("Connected to " + ip)
        self._btn_cli_start.config(state="disabled")
        self._btn_cli_stop.config(state="normal")
        self._status.set(f"Connected. Set browser SOCKS5 proxy to 127.0.0.1:{local_port}")

    def _stop_client(self):
        if self._client:
            self._client.stop()
            self._client = None
        self._cli_status.set("Disconnected")
        self._btn_cli_start.config(state="normal")
        self._btn_cli_stop.config(state="disabled")
        self._status.set("Disconnected.")

    # Key management

    def _load_key(self):
        if os.path.exists(KEY_FILE):
            self._key = open(KEY_FILE, "rb").read().strip()
            self._key_var.set(self._key.decode())

    def _load_or_create_key(self):
        if os.path.exists(KEY_FILE):
            self._key = open(KEY_FILE, "rb").read().strip()
        else:
            self._key = Fernet.generate_key()
            open(KEY_FILE, "wb").write(self._key)
        self._key_var.set(self._key.decode())

    def _new_key(self):
        self._key = Fernet.generate_key()
        open(KEY_FILE, "wb").write(self._key)
        self._key_var.set(self._key.decode())
        self._status.set("New key generated.")

    def _copy_key(self):
        key = self._key_var.get().strip()
        if len(key) > 10:
            self.root.clipboard_clear()
            self.root.clipboard_append(key)
            self._status.set("Key copied to clipboard.")
        else:
            messagebox.showinfo("No key", "Start the server first to generate a key.")

    # Exit 

    def _exit(self):
        if self._server:
            self._server.stop()
        if self._client:
            self._client.stop()
        self.root.destroy()

    # Log polling 

    def _poll(self):
        while not self._queue.empty():
            target, msg = self._queue.get_nowait()
            widget = self._srv_log if target == "srv" else self._cli_log
            widget.config(state="normal")
            widget.insert(tk.END, msg + "\n")
            widget.see(tk.END)
            widget.config(state="disabled")
        self.root.after(100, self._poll)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()