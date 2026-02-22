# gui.py

import tkinter as tk
from tkinter import ttk
import threading
import queue
from cryptography.fernet import Fernet, InvalidToken
import base64
import sys
import os

# Import server and client modules
import server
import client

def generate_key(entry):
    """
    Generate a new Fernet key and insert into entry.
    """
    key = Fernet.generate_key()
    entry.delete(0, tk.END)
    entry.insert(0, key.decode('utf-8'))

def log_to_text(queue, text_widget):
    """
    Utility to update log text from queue.
    """
    while not queue.empty():
        msg = queue.get()
        text_widget.insert(tk.END, msg + '\n')
        text_widget.see(tk.END)

def update_clients(queue, listbox):
    """
    Update clients listbox from queue.
    """
    while not queue.empty():
        clients = queue.get()
        listbox.delete(0, tk.END)
        for addr in clients:
            listbox.insert(tk.END, f"{addr[0]}:{addr[1]}")

def main():
    root = tk.Tk()
    root.title("VPN Control Panel")

    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=10, pady=10)

    # Queues for thread communication
    server_log_queue = queue.Queue()
    client_log_queue = queue.Queue()
    server_clients_queue = queue.Queue()

    # Events for stop
    server_stop_event = threading.Event()
    client_stop_event = threading.Event()

    # Threads
    server_thread = [None]  # Mutable for nonlocal
    client_thread = [None]

    # Server Tab
    server_tab = ttk.Frame(notebook)
    notebook.add(server_tab, text='VPN Server')

    ttk.Label(server_tab, text="Listen Port:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
    server_port_entry = ttk.Entry(server_tab)
    server_port_entry.insert(0, "8888")
    server_port_entry.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(server_tab, text="Encryption Key:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
    server_key_entry = ttk.Entry(server_tab, width=60)
    server_key_entry.grid(row=1, column=1, padx=5, pady=5)
    ttk.Button(server_tab, text="Generate Key", command=lambda: generate_key(server_key_entry)).grid(row=1, column=2, padx=5, pady=5)

    server_status_label = ttk.Label(server_tab, text="Status: Disconnected", foreground="red")
    server_status_label.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='w')

    def start_server():
        if server_thread[0] and server_thread[0].is_alive():
            return
        try:
            port = int(server_port_entry.get())
            key_str = server_key_entry.get()
            key = base64.urlsafe_b64decode(key_str + '=' * ((4 - len(key_str) % 4) % 4))  # Pad if needed
            Fernet(key)  # Validate
        except ValueError:
            server_log_queue.put("Invalid port")
            return
        except (InvalidToken, ValueError):
            server_log_queue.put("Invalid encryption key")
            return
        server_stop_event.clear()
        server_thread[0] = threading.Thread(target=server.run_server, args=('0.0.0.0', port, key, server_log_queue, server_stop_event, server_clients_queue))
        server_thread[0].daemon = True
        server_thread[0].start()
        server_status_label.config(text="Status: Connected", foreground="green")

    def stop_server():
        if not server_thread[0] or not server_thread[0].is_alive():
            return
        server_stop_event.set()
        server_thread[0].join(timeout=5)
        server_thread[0] = None
        server_status_label.config(text="Status: Disconnected", foreground="red")

    ttk.Button(server_tab, text="Start Server", command=start_server).grid(row=2, column=2, padx=5, pady=5)
    ttk.Button(server_tab, text="Stop Server", command=stop_server).grid(row=2, column=3, padx=5, pady=5)

    ttk.Label(server_tab, text="Connected Clients:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
    clients_listbox = tk.Listbox(server_tab, height=5, width=50)
    clients_listbox.grid(row=4, column=0, columnspan=4, padx=5, pady=5, sticky='ew')

    ttk.Label(server_tab, text="Server Logs:").grid(row=5, column=0, padx=5, pady=5, sticky='w')
    server_logs_text = tk.Text(server_tab, height=10, width=80)
    server_logs_text.grid(row=6, column=0, columnspan=4, padx=5, pady=5, sticky='ew')

    # Client Tab
    client_tab = ttk.Frame(notebook)
    notebook.add(client_tab, text='VPN Client')

    ttk.Label(client_tab, text="Server IP:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
    client_ip_entry = ttk.Entry(client_tab)
    client_ip_entry.insert(0, "127.0.0.1")
    client_ip_entry.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(client_tab, text="Server Port:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
    client_port_entry = ttk.Entry(client_tab)
    client_port_entry.insert(0, "8888")
    client_port_entry.grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(client_tab, text="Local Port:").grid(row=2, column=0, padx=5, pady=5, sticky='e')
    local_port_entry = ttk.Entry(client_tab)
    local_port_entry.insert(0, "1080")
    local_port_entry.grid(row=2, column=1, padx=5, pady=5)

    ttk.Label(client_tab, text="Encryption Key:").grid(row=3, column=0, padx=5, pady=5, sticky='e')
    client_key_entry = ttk.Entry(client_tab, width=60)
    client_key_entry.grid(row=3, column=1, padx=5, pady=5)
    ttk.Button(client_tab, text="Generate Key", command=lambda: generate_key(client_key_entry)).grid(row=3, column=2, padx=5, pady=5)

    client_status_label = ttk.Label(client_tab, text="Status: Disconnected", foreground="red")
    client_status_label.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky='w')

    def start_client():
        if client_thread[0] and client_thread[0].is_alive():
            return
        try:
            remote_ip = client_ip_entry.get()
            remote_port = int(client_port_entry.get())
            local_port = int(local_port_entry.get())
            key_str = client_key_entry.get()
            key = base64.urlsafe_b64decode(key_str + '=' * ((4 - len(key_str) % 4) % 4))
            Fernet(key)
        except ValueError:
            client_log_queue.put("Invalid port or IP")
            return
        except (InvalidToken, ValueError):
            client_log_queue.put("Invalid encryption key")
            return
        client_stop_event.clear()
        client_thread[0] = threading.Thread(target=client.run_client, args=('127.0.0.1', local_port, remote_ip, remote_port, key, client_log_queue, client_stop_event))
        client_thread[0].daemon = True
        client_thread[0].start()
        client_status_label.config(text="Status: Connected", foreground="green")

    def stop_client():
        if not client_thread[0] or not client_thread[0].is_alive():
            return
        client_stop_event.set()
        client_thread[0].join(timeout=5)
        client_thread[0] = None
        client_status_label.config(text="Status: Disconnected", foreground="red")

    ttk.Button(client_tab, text="Start Client", command=start_client).grid(row=4, column=2, padx=5, pady=5)
    ttk.Button(client_tab, text="Stop Client", command=stop_client).grid(row=4, column=3, padx=5, pady=5)

    ttk.Label(client_tab, text="Client Logs:").grid(row=5, column=0, padx=5, pady=5, sticky='w')
    client_logs_text = tk.Text(client_tab, height=10, width=80)
    client_logs_text.grid(row=6, column=0, columnspan=4, padx=5, pady=5, sticky='ew')

    # Update function for GUI
    def update_gui():
        log_to_text(server_log_queue, server_logs_text)
        log_to_text(client_log_queue, client_logs_text)
        update_clients(server_clients_queue, clients_listbox)
        root.after(200, update_gui)

    update_gui()

    # Clean shutdown
    def on_close():
        stop_server()
        stop_client()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    main()