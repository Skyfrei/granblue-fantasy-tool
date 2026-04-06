
# Granblue Fantasy Tool

A standalone desktop application for Granblue Fantasy (GBF) that reads game packets
in real time to display DPS, damage per turn, raid info, grid data, and more.
No browser extension required.

## Features

- DPS checker - track damage output per player in real time
- Damage per turn calculator
- Raid info viewer - see raid details as they arrive
- Raid comparison - compare multiple raid sessions side by side
- Party grid tracker - inspect weapon grid and party composition
- Asset requestor - fetch GBF game assets on demand
- Standalone - runs separately from the browser, zero browser interaction

## How It Works

The tool uses TShark or Wireshark to sniff network packets sent from the
Granblue Fantasy domain. It parses those packets and presents the data
through a desktop GUI built with PyQt5. No modifications to the game or
browser are made.

Start this program before opening Granblue Fantasy in your browser.

## Requirements

- Python 3
- PyQt5
- TShark (part of Wireshark) installed and accessible in your PATH
- Windows or Linux

## Installation

### Windows

1. Download and install [Wireshark](https://www.wireshark.org/) (includes TShark).
2. Install Python dependencies with `pip install -r requirements.txt`.
3. Run `python main.py` before opening Granblue Fantasy in your browser.

### Linux

1. Install TShark: `sudo apt install tshark` (or your distro equivalent).
2. Add your user to the `wireshark` group if packet capture fails:
   `sudo usermod -aG wireshark $USER` then log out and back in.
3. Install Python dependencies with `pip install -r requirements.txt`.
4. Run `python main.py` before opening Granblue Fantasy in your browser.


## License
This project is licensed under CC BY-NC 4.0. Free to use and modify. Commercial use is not permitted.


https://github.com/user-attachments/assets/7b31afa8-485c-43fb-a78d-ca016f72d339

