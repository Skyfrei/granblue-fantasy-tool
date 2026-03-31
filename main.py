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
    return par.parse()

def get_dmg(par: Parser, party: Party):
    par.parse_damage(party)

class CaptureThread(QThread):
    update_signal = Signal(object)

    def __init__(self):
        super().__init__()
        # Use your existing helper functions
        self.parser = get_parser({})
        self.active_party = None
        self.process = None
        self.keep_running = True

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
            if not self.keep_running:
                break

            clean_line = line.strip()
            if not line:
                continue
            try:
                decode = binascii.unhexlify(clean_line).decode('utf-8', errors='ignore')
                if decode.startswith("{") and decode.endswith("}"):
                    try:
                        json_data = json.loads(decode)
                        self.parser.set_data(json_data)
                        
                        if self.active_party is None:
                            temp_party = get_party(self.parser)
                            if temp_party and temp_party.get_members_list():
                                self.active_party = temp_party

                        if self.active_party:
                            get_dmg(self.parser, self.active_party)
                            self.update_signal.emit(self.active_party)
                    
                    except json.JSONDecodeError:
                        # This catches the "Expecting property name" error
                        # and just moves to the next packet.
                        continue
                        
            except Exception as e:
                continue

    def stop(self):
        self.keep_running = False
        if self.process:
            print("Stopping TShark...")
            self.process.terminate()
            self.process.wait()
        self.wait()

class LiveMeter(gbf_gui):
    def __init__(self):
        super().__init__() 
        self.setWindowTitle("Granblue Fantasy Tool")
        self.thread = CaptureThread()
        self.thread.update_signal.connect(self.update_ui_live)
        self.thread.start()

    def closeEvent(self, event):
        print("Closing... Cleaning up threads.")
        self.thread.stop()
        event.accept()


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
