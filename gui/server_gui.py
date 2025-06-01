import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import time
import json
import os
import yaml

# Buforowanie i agregacja odczytów (przykładowa struktura)
from collections import defaultdict, deque
from datetime import datetime, timedelta

CONFIG_FILE = "gui_config.yaml"

class SensorBuffer:
    def __init__(self):
        self.data = defaultdict(lambda: deque(maxlen=1000))  # czujnik: lista (timestamp, value, unit)

    def add(self, sensor_id, value, unit, timestamp):
        self.data[sensor_id].append((timestamp, value, unit))

    def get_last(self, sensor_id):
        if self.data[sensor_id]:
            t, v, u = self.data[sensor_id][-1]
            return v, u, t
        return None, None, None

    def get_avg(self, sensor_id, hours):
        now = datetime.now()
        values = [v for t, v, u in self.data[sensor_id]
                  if now - t <= timedelta(hours=hours)]
        if values:
            return sum(values) / len(values)
        return None

    def get_all_sensors(self):
        return list(self.data.keys())

# Prosty serwer TCP w wątku
import socket

class ThreadedServer(threading.Thread):
    def __init__(self, port, on_data, status_queue):
        super().__init__(daemon=True)
        self.port = port
        self.on_data = on_data
        self.status_queue = status_queue
        self._stop_event = threading.Event()

    def run(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("", self.port))
                s.listen()
                self.status_queue.put(("info", f"Serwer nasłuchuje na porcie {self.port}"))
                while not self._stop_event.is_set():
                    s.settimeout(1.0)
                    try:
                        client, addr = s.accept()
                    except socket.timeout:
                        continue
                    threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
        except Exception as e:
            self.status_queue.put(("error", f"Błąd serwera: {e}"))

    def handle_client(self, client, addr):
        try:
            with client:
                data = b""
                while True:
                    chunk = client.recv(4096)
                    if not chunk:
                        break
                    data += chunk
                    if b"\n" in data:
                        break
                msg = data.decode().strip()
                try:
                    payload = json.loads(msg)
                    # Oczekiwany format: {"sensor": "id", "value": 12.3, "unit": "C", "timestamp": "..."}
                    sensor_id = payload.get("sensor")
                    value = float(payload.get("value"))
                    unit = payload.get("unit", "")
                    ts = payload.get("timestamp")
                    if ts:
                        timestamp = datetime.fromisoformat(ts)
                    else:
                        timestamp = datetime.now()
                    self.on_data(sensor_id, value, unit, timestamp)
                    self.status_queue.put(("info", f"Odebrano dane z {sensor_id}: {value} {unit}"))
                except Exception as e:
                    self.status_queue.put(("error", f"Błąd parsowania JSON: {e}"))
                try:
                    client.sendall(b"ACK\n")
                except Exception as e:
                    self.status_queue.put(("error", f"Błąd wysyłania ACK: {e}"))
        except Exception as e:
            self.status_queue.put(("error", f"Błąd obsługi klienta: {e}"))

    def stop(self):
        self._stop_event.set()

# GUI
class ServerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Serwer TCP - GUI")
        self.geometry("800x400")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.sensor_buffer = SensorBuffer()
        self.status_queue = queue.Queue()
        self.server_thread = None

        self._load_config()

        self._build_widgets()
        self._update_table()
        self._poll_status()

    def _build_widgets(self):
        # Górny panel
        top = tk.Frame(self)
        top.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(top, text="Port TCP:").pack(side=tk.LEFT)
        self.port_var = tk.StringVar(value=str(self.port))
        self.port_entry = tk.Entry(top, textvariable=self.port_var, width=8)
        self.port_entry.pack(side=tk.LEFT, padx=5)

        self.start_btn = tk.Button(top, text="Start", command=self.start_server)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        self.stop_btn = tk.Button(top, text="Stop", command=self.stop_server, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Tabela czujników
        columns = ("sensor", "last_value", "unit", "timestamp", "avg1h", "avg12h")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col, label in zip(columns,
            ["Sensor", "Ostatnia wartość", "Jednostka", "Timestamp", "Średnia 1h", "Średnia 12h"]):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=120)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Pasek statusu
        self.status_var = tk.StringVar()
        status_bar = tk.Label(self, textvariable=self.status_var, anchor="w", relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def start_server(self):
        try:
            port = int(self.port_var.get())
            if self.server_thread and self.server_thread.is_alive():
                self.status_var.set("Serwer już działa.")
                return
            self.server_thread = ThreadedServer(
                port, self.sensor_buffer.add, self.status_queue
            )
            self.server_thread.start()
            self.status_var.set(f"Serwer uruchomiony na porcie {port}")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.DISABLED)
        except Exception as e:
            self.status_var.set(f"Błąd uruchamiania serwera: {e}")

    def stop_server(self):
        if self.server_thread:
            self.server_thread.stop()
            self.server_thread = None
            self.status_var.set("Serwer zatrzymany.")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.NORMAL)

    def _update_table(self):
        # Odświeżanie tabeli co 3 sekundy
        for row in self.tree.get_children():
            self.tree.delete(row)
        for sensor in self.sensor_buffer.get_all_sensors():
            v, u, t = self.sensor_buffer.get_last(sensor)
            avg1h = self.sensor_buffer.get_avg(sensor, 1)
            avg12h = self.sensor_buffer.get_avg(sensor, 12)
            self.tree.insert("", "end", values=(
                sensor,
                f"{v:.2f}" if v is not None else "",
                u or "",
                t.strftime("%Y-%m-%d %H:%M:%S") if t else "",
                f"{avg1h:.2f}" if avg1h is not None else "",
                f"{avg12h:.2f}" if avg12h is not None else "",
            ))
        self.after(3000, self._update_table)

    def _poll_status(self):
        # Odbieranie komunikatów statusu/błędów z wątku serwera
        try:
            while True:
                level, msg = self.status_queue.get_nowait()
                if level == "info":
                    self.status_var.set(msg)
                else:
                    self.status_var.set(msg)
                    messagebox.showerror("Błąd serwera", msg)
        except queue.Empty:
            pass
        self.after(500, self._poll_status)

    def _load_config(self):
        self.port = 9000
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    cfg = yaml.safe_load(f)
                    self.port = int(cfg.get("port", 9000))
            except Exception:
                pass

    def _save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                yaml.safe_dump({"port": int(self.port_var.get())}, f)
        except Exception:
            pass

    def on_close(self):
        self._save_config()
        self.stop_server()
        self.destroy()

if __name__ == "__main__":
    app = ServerGUI()
    app.mainloop()