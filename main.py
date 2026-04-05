import subprocess
import json
import binascii
import sys
import signal
import os
import platform
import gzip
import shutil

import psutil

from PySide6.QtCore import QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from typing import Any, Dict
from gbf_party import Party, Quest
from gbf_parser import Parser
from gbf_gui import GBFDpsMeter as gbf_gui


HOME_DIR = os.path.expanduser("~")
KEYLOG_FILE = os.path.join(HOME_DIR, "code/granblue-fantasy-tool/gbf_keys.log")
DUMP_FILE = "./all_gbf_dump4.json"

def find_interface():
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    best_match = None
    for name, info in stats.items():
        if info.isup and "loopback" not in name.lower() and "lo" != name:
            if name in addrs:
                for addr in addrs[name]:
                    if addr.family == 2:
                        return name 
                        
    for name, info in stats.items():
        if info.isup: return name
        
    return "1"

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


def set_windows_user_env(key, value):
    try:
        subprocess.run(["setx", key, value], check=True, capture_output=True)
        return True
    except Exception as e:
        print(f"Failed to set Windows env: {e}")
        return False

def set_linux_user_env(key, value):
    try:
        shell_path = os.environ.get("SHELL", "")
        if "fish" in shell_path:
            config_path = os.path.expanduser("~/.config/fish/config.fish")
            export_line = f'set -gx {key} "{value}"\n'
            match_str = f"set -gx {key}"
        else:
            config_path = os.path.expanduser("~/.bashrc")
            export_line = f'export {key}="{value}"\n'
            match_str = f"export {key}="
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                if any(match_str in line for line in f):
                    return True
        with open(config_path, "a") as f:
            f.write(f"\n# GBF Tool Keylog\n{export_line}")
        
        print(f"Environment variable set in {config_path}. Please restart your shell.")
        return True
    except Exception as e:
        print(f"Failed to set Linux env: {e}")
        return False

class CaptureThread(QThread):
    update_signal = Signal(object)

    def __init__(self):
        super().__init__()
        self.init_env()
        self.interface = find_interface()
        self.parser = get_parser({})
        self.quest_list = list()
        self.active_quest = None
        self.process = None
        self.keep_running = True
        self.packet_buffer = b""

   
    def init_env(self):
        key = "SSLKEYLOGFILE"
        path = os.path.abspath("gbf_keys.log")
        if os.environ.get(key) == path:
            return
        success = False
        if platform.system() == "Windows":
            success = set_windows_user_env(key, path)
        else:
            success = set_linux_user_env(key, path)

    def run(self):
        with open(KEYLOG_FILE, 'w') as f:
            f.write("") 

        cmd = [
            "tshark",
            "-i", self.interface,
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
                            json.dump(json_data, f, indent=2)
                            f.write("\n\n")
                            f.flush()
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
        if os.path.exists(KEYLOG_FILE):
            try:
                os.remove(KEYLOG_FILE)
                print(f"Successfully deleted: {KEYLOG_FILE}")
            except Exception as e:
                print(f"Error deleting keylog file: {e}")
        event.accept()


# ── Entry Point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    if not shutil.which("tshark"):
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Icon.Critical)
        error_dialog.setWindowTitle("Missing Dependency: TShark")
        error_dialog.setText("TShark was not found on your system.")
        error_dialog.setInformativeText(
            "This tool requires Wireshark/TShark to function.\n\n"
            "Please install Wireshark or TShark."
        )
        error_dialog.setStandardButtons(QMessageBox.StandardButton.Ok)
        
        error_dialog.exec()
        sys.exit(0)

    window = LiveMeter()
    window.show()
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None) 
    signal.signal(signal.SIGINT, lambda *args: app.quit())

    app.aboutToQuit.connect(window.thread.stop)

    sys.exit(app.exec())
