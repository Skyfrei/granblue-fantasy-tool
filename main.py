import subprocess
import json
import binascii
import sys
import signal
from PySide6.QtCore import QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication
from typing import Any, Dict
from gbf_party import Party, Quest
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

def get_quest(par: Parser):
    return par.parse()

def update(par: Parser, quest: Quest):
    par.parse_damage(quest)

class CaptureThread(QThread):
    update_signal = Signal(object)

    def __init__(self):
        super().__init__()
        # Use your existing helper functions
        self.parser = get_parser({})
        self.active_quest = None
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
                        
                        if self.active_quest is None:
                            temp_quest = get_quest(self.parser)
                            if temp_quest and temp_quest.get_party().get_members_list():
                                self.active_quest = temp_quest

                        if self.active_quest:
                            update(self.parser, self.active_quest)
                            self.update_signal.emit(self.active_quest)
                    
                    except json.JSONDecodeError:
                        continue
                        
            except Exception as e:
                print(e)
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
