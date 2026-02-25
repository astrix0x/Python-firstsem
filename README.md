## Secure VPN Tunnel

A secure encrypted VPN tunnel built with Python using AES-128 encryption and the SOCKS5 proxy protocol.

Built as part of BSc(Hons) Ethical Hacking and Cyber Security — Introduction to Programming (ST4017CMD) at Softwarica College of IT & E-Commerce in collaboration with Coventry University.

---

## Video Demo

**Video Link:** Will paste soon **

**GitHub Repository:** https://github.com/astrix0x/Python-firstsem

---

## What It Does

This project creates an encrypted tunnel between a client machine and a server machine. All traffic that passes through the tunnel is encrypted using AES-128-CBC so that anyone monitoring the network can only see unreadable encrypted data.

- Traffic between client and server is **AES-128-CBC encrypted**
- Uses the **SOCKS5 proxy protocol** — works with any SOCKS5 compatible browser
- Multi-threaded server supports multiple clients at the same time
- Simple **GUI** built with Tkinter for both server and client

---

## How It Works

```
Browser (Windows)
      |
      | SOCKS5
      v
  client.py  ── AES-128 encrypted tunnel ──►  server.py  ──►  Internet
(127.0.0.1:1080)                              (Kali Linux)
```

1. Browser sends traffic to the local SOCKS5 proxy (client.py on port 1080)
2. Client encrypts it and sends it through the tunnel to the server
3. Server decrypts it and forwards it to the real destination
4. Response comes back encrypted and client decrypts it for the browser

---

## File Structure

```
Python-firstsem/
├── screenshots/
│   ├── client_gui.png
│   ├── server_gui.png
│   ├── wireshark_with_VPN.png
│   └── wireshark_without_VPN.png
├── Dockerfile
├── README.md
├── VPN_forLinux
├── VPN_forWindows.exe
├── client.py
├── gui.py
├── icon.ico
├── requirements.txt
├── server.py
└── start.sh
```

---

## Requirements

- Python 3.11 or above
- cryptography library

```bash
pip install cryptography
```

---

## How to Run

### Option 1 — Run with Python (recommended)

**On the Server machine (Kali Linux):**

```bash
python3 gui.py
```

1. Go to the **Server** tab
2. Set a port (default: 9999)
3. Click **Start Server**
4. Copy the encryption key shown

**On the Client machine (Windows):**

```bash
python3 gui.py
```

1. Go to the **Client** tab
2. Enter the server IP address
3. Enter the server port
4. Paste the encryption key
5. Click **Connect**

---

### Option 2 — Run Server with Docker

```bash
# Build the image
sudo docker build -t vpn-server .

# Run on default port 9999
sudo docker run -p 9999:9999 vpn-server

# Run on a custom port (example: 8888)
sudo docker run -p 8888:8888 -e PORT=8888 vpn-server
```

The server will print the IP, port, and encryption key in the terminal. Use these in the client GUI to connect.

---

### Browser Proxy Setup (Firefox recommended)

After connecting the client, configure Firefox:

```
Settings → Network Settings → Manual proxy configuration
SOCKS Host : 127.0.0.1
Port       : 1080
Select     : SOCKS v5
Tick       : Proxy DNS over SOCKS5
```

---

## Verifying Encryption with Wireshark

**Without VPN** — filter in Wireshark:
```
ip.addr == <client-ip>
```
You can see websites visited, URLs, and page content in plain text.

**With VPN** — filter in Wireshark:
```
ip.addr == <client-ip> && tcp.port == 9999
```
All traffic appears as encrypted bytes starting with `gAAAAAB` — nothing readable.

---

## Encryption Details

| Property | Value |
|---|---|
| Algorithm | AES-128-CBC |
| Authentication | HMAC-SHA256 |
| Library | Python cryptography (Fernet) |
| Key size | 128 bits |

---

## Limitations

- Works per application (browser only) — not system wide
- Requires manual browser proxy configuration
- Key must be shared securely between server and client
- IP only changes if server is on a different internet connection

---

## License

Educational use only. Built for university coursework at Softwarica College of IT & E-Commerce.
