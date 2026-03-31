import subprocess
import json
import binascii
import sys
import signal
from PySide6.QtCore import QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication
from typing import Any, Dict
from gbf_party import Party
from gbf_parser import Parser
from gbf_gui import GBFDpsMeter as gbf_gui


INTERFACE = "enp1s0"
KEYLOG_FILE = "/home/sky/code/granblue/gbf_keys.log"
DUMP_FILE = "./all_gbf_dump3.json"


def find_interface():
    pass


def get_parser(json_data: Dict[str, any]) -> None:
    p = Parser(json_data)
    return p

def get_party(par: Parser):
    return par.parse_party()

def get_dmg(par: Parser, party: Party):
    par.parse_damage(party)

class CaptureThread(QThread):
    update_signal = Signal(object)

    def __init__(self):
        super().__init__()
        # Use your existing helper functions
        self.parser = get_parser({})
        self.active_party = None
        self.keep_running = True # Flag to control the loop
        self.process = None

    def run(self):
        with open(KEYLOG_FILE, 'w') as f:
            f.write("") 

        cmd = [
            "sudo", "tshark",
            "-i", INTERFACE,
            "-o", f"tls.keylog_file:{KEYLOG_FILE}",
            "-f", "host steam.granbluefantasy.com",
            "-T", "fields",
            "-e", "http2.data.data",
            "-l"
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)

        for line in iter(process.stdout.readline, ""):
            clean_line = line.strip()
            if not line:
                continue
            try:
                clean_line = clean_line.replace(":", "")
                decode = binascii.unhexlify(clean_line).decode('utf-8', errors='ignore')
                
                if decode.startswith("{"):
                    json_data = json.loads(decode)
                    self.parser.set_data(json_data)
                    
                    found_party = get_party(self.parser)
                    if found_party:
                        self.active_party = found_party
                        self.active_party.get_member_names() 
            
                    if self.active_party:
                        get_dmg(self.parser, self.active_party)
                        # Notify the GUI that data has changed
                        self.update_signal.emit(self.active_party)
                        
            except Exception as e:
                continue

    def stop(self):
        self.keep_running = False
        if self.process:
            self.process.terminate() # Tell tshark to stop
            self.process.wait()      # Wait for it to clean up
        self.wait()

class LiveMeter(gbf_gui):
    def __init__(self):
        super().__init__() 
        self.setWindowTitle("CYPHER // LIVE MONITOR")
        self.thread = CaptureThread()
        self.thread.update_signal.connect(self.update_ui_live)
        self.thread.start()

    @Slot(object)
    def update_ui_live(self, party: Party):
        members = party.get_members_list()
        if not members:
            return

        # Use the sorting and bar logic from your existing GUI
        sorted_members = sorted(members, key=lambda x: x.get_total_dmg(), reverse=True)
        max_dmg = max(m.get_total_dmg() for m in members) if members else 1
        
        # Update the rows (from Turn 16 code)
        for i, member in enumerate(sorted_members):
            if i < len(self.rows):
                self.rows[i].update_from_char(member, max_dmg, i+1)

# ── Entry Point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = LiveMeter()
    window.show()
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None) 
    signal.signal(signal.SIGINT, lambda *args: app.quit())

    app.aboutToQuit.connect(window.thread.stop)

    sys.exit(app.exec())
