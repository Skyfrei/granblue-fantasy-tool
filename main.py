import subprocess
import json
import binascii
import sys
import signal
import gzip
from PySide6.QtCore import QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication
from typing import Any, Dict
from gbf_party import Party, Quest
from gbf_parser import Parser
from gbf_gui import GBFDpsMeter as gbf_gui


INTERFACE = "enp1s0"
KEYLOG_FILE = "/home/sky/code/granblue/gbf_keys.log"
DUMP_FILE = "./all_gbf_dump4.json"


def find_interface():
    pass

def get_parser(json_data: Dict[str, any]) -> None:
    p = Parser(json_data)
    return p

def get_quest(par: Parser):
    return par.parse()

def has_quest_changed(par: Parser, q: Quest) -> bool:
    new_raid_id = par.data.get("raid_id", "")
    if new_raid_id != "" and new_raid_id != q.get_quest_id():
        return True
    return False

def update(par: Parser, quest: Quest):
    if has_quest_changed(par, quest):
        return True
    par.parse_damage(quest)
    return False

class CaptureThread(QThread):
    update_signal = Signal(object)

    def __init__(self):
        super().__init__()
        # Use your existing helper functions
        self.parser = get_parser({})
        self.quest_list = list()
        self.active_quest = None
        self.process = None
        self.keep_running = True
        self.packet_buffer = b""
    
    def run(self):
        with open(KEYLOG_FILE, 'w') as f:
            f.write("") 

        cmd = [
            "tshark",
            "-i", INTERFACE,
            "-o", f"tls.keylog_file:{KEYLOG_FILE}",
            "-f", "host steam.granbluefantasy.com",
            "-T", "fields",
            "-e", "http2.data.data",
            "-l"
        ]

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        with open(DUMP_FILE, 'a') as f:
            for line in iter(process.stdout.readline, ""):
                if not self.keep_running:
                    break
                clean_line = line.strip()
                if not line:
                    continue

                try:
                    self.packet_buffer = binascii.unhexlify(clean_line)
                except Exception as e:
                    continue
                try:
                    decode = self.packet_buffer.decode('utf-8', errors='ignore')
                    if decode.startswith("{") and decode.endswith("}"):
                        try:
                            json_data = json.loads(decode)
                            #json.dump(json_data, f, indent=2)
                            #f.write("\n\n")
                            #f.flush()
                            self.parser.set_data(json_data)
                            if self.active_quest is None:
                                temp_quest = get_quest(self.parser)
                                if temp_quest and temp_quest.get_party().get_members_list():
                                    self.active_quest = temp_quest

                            if self.active_quest:
                                needs_reload = update(self.parser, self.active_quest)
                                if needs_reload:
                                    self.active_quest = None
                                else:
                                    self.update_signal.emit(self.active_quest)
                        
                        except Exception as e:
                            print(e)  
                            continue
                            
                except Exception as e:
                    print(binascii.unhexlify(clean_line))
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
