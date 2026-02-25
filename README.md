#  Secure VPN Tunnel

A secure encrypted VPN tunnel built with Python using AES-128 encryption and the SOCKS5 proxy protocol.

Built as part of BSc(Hons) Ethical Hacking and Cybersecurity — Introduction to Programming (ST4017CMD) at Softwarica College of IT & E-Commerce in collaboration with Coventry University.

---

##  Video and Repository Link

**Video Link:** *will paste soon...*

**GitHub Repository:** https://github.com/astrix0x/Python-firstsem

---

## What It Does

This project creates an encrypted tunnel between a client computer and a server computer. All internet traffic that goes through the tunnel is encrypted using AES-128-CBC encryption. This means that even if someone is watching the network, they can only see random encrypted data and cannot read what you are doing.

-  All traffic is **AES-128-CBC encrypted**
-  Uses the **SOCKS5 proxy protocol**
-  Supports multiple clients at the same time
-  Easy to use **GUI** — no command line needed

---

## How It Works

```
Your Browser
      |
      | (sends traffic to local proxy)
      v
  client.py  ──── encrypted tunnel ────►  server.py  ────►  Internet
(127.0.0.1:1080)                         (Server Machine)
```

1. You set your browser to use a local proxy on port 1080
2. The client encrypts your traffic and sends it to the server
3. The server decrypts it and visits the website for you
4. The response comes back encrypted through the tunnel

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
├── LICENSE
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

##  How to Run

There are 3 ways to run this project. Pick the one that works best for you.

---

###  Option 1 — Standalone Executable (Easiest — No Python needed)

This is the easiest option. You do not need to install Python or anything else. Just download and run.

#### On Windows:
1. Download `VPN_forWindows.exe` from the repository
2. Double click it to open
3. If you see a warning from Windows Defender:
   - Click **More info**
   - Then click **Run anyway**
4. The VPN window will open

#### On Linux (Kali):
1. Download `VPN_forLinux` from the repository
2. Double click it to open
3. If double clicking does not work, open a terminal in the same folder and run:
```bash
chmod +x VPN_forLinux
./VPN_forLinux
```
4. The VPN window will open

---

###  Option 2 — Run with Python

Use this option if you have Python installed on your computer.

#### Step 1 — Make sure Python is installed
Open a terminal and type:
```bash
python3 --version
```
If you see a version number like `Python 3.11.x` you are good to go. If not, download Python from https://www.python.org/downloads/

#### Step 2 — Install the required library
```bash
pip install cryptography
```

#### Step 3 — Download the files
Download or clone the repository:
```bash
git clone https://github.com/astrix0x/Python-firstsem.git
cd Python-firstsem
```

#### Step 4 — Run the application
```bash
python3 gui.py
```

---

### Option 3 — Run Server with Docker

Use this option if you want to run the server inside a Docker container.

#### Step 1 — Make sure Docker is installed
```bash
docker --version
```
If Docker is not installed, download it from https://www.docker.com/get-started/

#### Step 2 — Build the Docker image
Open a terminal in the project folder and run:
```bash
sudo docker build -t vpn-server .
```
Wait for it to finish building.

#### Step 3 — Run the server
```bash
sudo docker run -p 9999:9999 vpn-server
```
You will see the server IP, port, and encryption key printed in the terminal. Copy the key — you will need it for the client.

#### Custom port (optional):
```bash
sudo docker run -p 8888:8888 -e PORT=8888 vpn-server
```

---
## Don't Have Firefox? Use Chrome or Edge Instead

If you do not want to install Firefox, you can use Chrome or Edge instead.
However you will need to launch them from the terminal with a special command.

### On Chrome:
1. Close Chrome completely if it is already open
2. Open a terminal and run:
```bash
chrome --proxy-server="socks5://127.0.0.1:1080"
```

### On Edge:
1. Close Edge completely if it is already open
2. Open a terminal and run:
```bash
msedge --proxy-server="socks5://127.0.0.1:1080"
```

> **Note:** Firefox is recommended because it has built in SOCKS5 proxy settings that are simple to configure. Chrome and Edge require launching from the terminal with a special command every time you want to use the VPN.

---

## Using the Application

Once the application is open you will see two tabs — **Server** and **Client**.

### Running the Server (on the server machine):
1. Click the **Server** tab
2. Enter a port number (default is 9999)
3. Click **Start Server**
4. Copy the **Encryption Key** shown — you will share this with the client

### Running the Client (on the client machine):
1. Click the **Client** tab
2. Enter the **Server IP** address (the IP of the machine running the server)
3. Enter the **Server Port** (must match what the server is using)
4. Paste the **Encryption Key** copied from the server
5. Click **Connect**
6. The status will change to **Connected**

---

## Setting Up Firefox to Use the VPN

After connecting the client, you need to tell Firefox to send traffic through the VPN:

1. Open Firefox
2. Click the **three lines** (menu) in the top right
3. Click **Settings**
4. Search for **proxy** in the search bar
5. Click **Settings** next to Network Settings
6. Select **Manual proxy configuration**
7. Fill in:
   - SOCKS Host: `127.0.0.1`
   - Port: `1080`
8. Select **SOCKS v5**
9. Tick **Proxy DNS over SOCKS5**
10. Click **OK**

Now all your Firefox traffic goes through the encrypted VPN tunnel.

To turn off the VPN, go back to these settings and select **No proxy**.

---

## 🔍 Verifying It Works (Wireshark)

You can use Wireshark to confirm the encryption is working.

**Without VPN** — use this filter in Wireshark:
```
ip.addr == <your-ip>
```
You will see websites, URLs, and content in plain readable text.

**With VPN** — use this filter in Wireshark:
```
ip.addr == <your-ip> && tcp.port == 9999
```
You will only see encrypted data starting with `gAAAAAB` — nothing readable at all.

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

- Works for the browser only — not all apps on the computer
- You need to set the proxy manually in the browser
- The encryption key must be shared between server and client
- Your IP address only changes if the server is on a different internet connection

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for full details.

In simple words: you are free to use, copy, and modify this project as long as you give credit to the original author.

---

## Author

Built by Aashish Acharya aka astrix0x/Frosty a first year BSc(Hons) Ethical Hacking and Cybersecurity student at Softwarica College of IT & E-Commerce Softwarica (Affiliated with Coventry University)
