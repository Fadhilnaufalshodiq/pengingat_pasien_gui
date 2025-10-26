import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import pyttsx3
import pystray  # Untuk system tray
from PIL import Image  # Untuk icon tray

# Konfigurasi global
DEFAULT_INTERVAL_MIN = 10
ALERT_REPEAT_DURATION = 30
ALERT_REPEAT_INTERVAL = 2
TTS_RATE = 150

# Variabel global
_running = False
_next_direction_right = True
_next_alarm_time = None
_engine = None

def init_tts():
    global _engine
    try:
        _engine = pyttsx3.init()
        _engine.setProperty('rate', TTS_RATE)
    except Exception as e:
        _engine = None
        print("Error inisialisasi TTS:", e)

def say_text(text):
    try:
        if _engine:
            _engine.say(text)
            _engine.runAndWait()
    except Exception as e:
        print("Error TTS:", e)

def alert_repeat_loop(text, stop_event, repeat_duration=ALERT_REPEAT_DURATION):
    start = time.time()
    while not stop_event.is_set() and (time.time() - start) < repeat_duration and _running:
        say_text(text)
        for _ in range(int(ALERT_REPEAT_INTERVAL * 10)):
            if stop_event.is_set() or not _running:
                break
            time.sleep(0.1)

def format_mmss(secs):
    if secs is None or secs <= 0:
        return "00:00"
    m = int(secs // 60)
    s = int(secs % 60)
    return f"{m:02d}:{s:02d}"

class PengingatGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pengingat Pasien - ICU")
        self.geometry("450x200")  # Sedikit diperbesar untuk label baru
        self.resizable(False, False)
        self.configure(bg="#eaf6ff")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)  # Handle close event

        # Variabel model
        self.interval_min = tk.IntVar(value=DEFAULT_INTERVAL_MIN)
        self.repeat_sound = tk.BooleanVar(value=True)
        self.start_dir = tk.StringVar(value="KANAN")

        # Variabel internal
        self._stop_event = threading.Event()
        self._alerting = False
        self._countdown_job = None
        self._tray_icon = None  # Untuk system tray

        self._build_ui()
        self._setup_tray()  # Setup system tray
        self.update_ui()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Card.TFrame", background="#e8f8ff")
        style.configure("Title.TLabel", background="#2b6cb0", foreground="white", font=("Segoe UI", 12, "bold"))
        style.configure("Label.TLabel", background="#e8f8ff", font=("Segoe UI", 10))
        style.configure("Status.TLabel", background="#e8f8ff", font=("Segoe UI", 12, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"))

        # Header
        header = tk.Frame(self, bg="#2b6cb0", height=40)
        header.pack(fill="x")
        title = tk.Label(header, text=" PENGINGAT PASIEN", bg="#2b6cb0", fg="white", font=("Segoe UI", 12, "bold"))
        title.pack(anchor="w", padx=10, pady=6)

        # Body
        body = ttk.Frame(self, padding=12, style="Card.TFrame")
        body.pack(fill="both", expand=True, padx=10, pady=8)

        # Kolom kiri: Kontrol
        left_col = ttk.Frame(body, style="Card.TFrame")
        left_col.grid(row=0, column=0, sticky="nw")

        ttk.Label(left_col, text="Interval (menit):", style="Label.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Spinbox(left_col, from_=1, to=120, width=6, textvariable=self.interval_min).grid(row=0, column=1, padx=8, pady=6, sticky="w")

        ttk.Label(left_col, text="Mulai arah:", style="Label.TLabel").grid(row=1, column=0, sticky="w")
        rd_frame = ttk.Frame(left_col, style="Card.TFrame")
        rd_frame.grid(row=1, column=1, sticky="w", padx=8)
        ttk.Radiobutton(rd_frame, text="KANAN", value="KANAN", variable=self.start_dir).pack(side="left")
        ttk.Radiobutton(rd_frame, text="KIRI", value="KIRI", variable=self.start_dir).pack(side="left", padx=6)

        ttk.Checkbutton(left_col, text="Ulangi suara sampai STOP", variable=self.repeat_sound).grid(row=2, column=0, columnspan=2, pady=6, sticky="w")

        # Kolom kanan: Tombol
        btn_frame = ttk.Frame(body, style="Card.TFrame")
        btn_frame.grid(row=0, column=1, sticky="ne", padx=(20, 0))
        self.start_btn = ttk.Button(btn_frame, text="START", command=self.start)
        self.start_btn.pack(side="top", fill="x", pady=(0, 6))
        self.stop_btn = ttk.Button(btn_frame, text="STOP", command=self.stop, state="disabled")
        self.stop_btn.pack(side="top", fill="x")
        ttk.Button(btn_frame, text="Test Suara (kanan)", command=self._test_right).pack(side="top", fill="x", pady=(8, 3))
        ttk.Button(btn_frame, text="Test Suara (kiri)", command=self._test_left).pack(side="top", fill="x")

        # Area status
        status_frame = ttk.Frame(body, style="Card.TFrame")
        status_frame.grid(row=1, column=0, columnspan=2, pady=(12, 0), sticky="we")
        self.status_label = ttk.Label(status_frame, text="Status: STOP", style="Status.TLabel")
        self.status_label.pack(anchor="w")
        self.count_label = ttk.Label(status_frame, text="Waktu sampai rotasi: --:--", style="Label.TLabel")
        self.count_label.pack(anchor="w", pady=(6, 0))
        # Label baru untuk countdown detik
        self.seconds_label = ttk.Label(status_frame, text="Detik tersisa: --", style="Label.TLabel")
        self.seconds_label.pack(anchor="w", pady=(6, 0))

    def _setup_tray(self):
        """Setup system tray icon."""
        # Buat icon sederhana (ganti dengan path gambar jika ada)
        image = Image.new('RGB', (64, 64), color='blue')  # Icon biru sederhana
        menu = pystray.Menu(
            pystray.MenuItem('Show', self._show_window),
            pystray.MenuItem('Exit', self._exit_app)
        )
        self._tray_icon = pystray.Icon("ICU Reminder", image, "Pengingat Pasien ICU", menu)
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _show_window(self):
        """Show window dari tray."""
        self.deiconify()
        self.lift()

    def _hide_window(self):
        """Hide window ke tray."""
        self.withdraw()

    def _exit_app(self):
        """Exit aplikasi dari tray."""
        self._tray_icon.stop()
        self.destroy()

    def _on_close(self):
        """Handle close window: minimize ke tray."""
        self._hide_window()

    def _test_right(self):
        direction = "kanan"
        text = f"Tolong balikkan badan pasien ke {direction}"
        threading.Thread(target=say_text, args=(text,), daemon=True).start()

    def _test_left(self):
        direction = "kiri"
        text = f"Tolong balikkan badan pasien ke {direction}"
        threading.Thread(target=say_text, args=(text,), daemon=True).start()

    def start(self):
        global _running, _next_direction_right, _next_alarm_time
        if _running:
            return
        _running = True
        self._stop_event.clear()
        _next_direction_right = True if self.start_dir.get() == "KANAN" else False
        _next_alarm_time = time.time()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_label.config(text="Status: RUNNING")
        threading.Thread(target=self._alarm_loop, daemon=True).start()
        self.update_ui()

    def stop(self):
        global _running, _next_alarm_time
        self._stop_event.set()
        _running = False
        _next_alarm_time = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_label.config(text="Status: STOP")
        self.count_label.config(text="Waktu sampai rotasi: --:--")
        self.seconds_label.config(text="Detik tersisa: --")

    def update_ui(self, alerting=False):
        self._alerting = alerting
        if self._countdown_job:
            try:
                self.after_cancel(self._countdown_job)
            except Exception:
                pass
        self._do_update()

    def _do_update(self):
        global _next_alarm_time, _next_direction_right
        direction = "kanan" if _next_direction_right else "kiri"
        if getattr(self, "_alerting", False):
            self.status_label.config(text=f"ALERT! Balikkan ke {direction} (durasi: {ALERT_REPEAT_DURATION}s)", foreground="#b30000")
        else:
            self.status_label.config(text=f"Status: RUNNING - Selanjutnya: {direction}", foreground="#003366" if _running else "#333333")

        if _next_alarm_time:
            remaining = max(0, _next_alarm_time - time.time())
            self.count_label.config(text=f"Waktu sampai rotasi: {format_mmss(remaining)} → Selanjutnya: {direction}")
            self.seconds_label.config(text=f"Detik tersisa: {int(remaining)}")
        else:
            self.count_label.config(text="Waktu sampai rotasi: --:--")
            self.seconds_label.config(text="Detik tersisa: --")

        self._countdown_job = self.after(1000, self._do_update)  # Update setiap 1 detik untuk detik

    def _alarm_loop(self):
        global _running, _next_direction_right, _next_alarm_time
        while _running and not self._stop_event.is_set():
            if _next_alarm_time is None or _next_alarm_time <= time.time():
                _next_alarm_time = time.time() + (self.interval_min.get() * 60)
            while _running and time.time() < _next_alarm_time:
                if self._stop_event.is_set():
                    return
                time.sleep(0.5)

            if not _running or self._stop_event.is_set():
                break

            # Jalankan alert
            direction = "kanan" if _next_direction_right else "kiri"
            text = f"Tolong balikkan badan pasien ke {direction}"
            stop_evt = threading.Event()
            alert_thread = threading.Thread(target=alert_repeat_loop, args=(text, stop_evt), daemon=True)
            alert_thread.start()

            self.update_ui(alerting=True)
            start_alert = time.time()
            while time.time() - start_alert < ALERT_REPEAT_DURATION and not self._stop_event.is_set() and _running:
                time.sleep(0.3)

            stop_evt.set()
            alert_thread.join(timeout=0.5)

            # Popup "Sudah dikerjakan?"
            self._show_done_popup(direction)

            # Toggle arah dan jadwalkan berikutnya jika lanjut
            _next_direction_right = not _next_direction_right
            _next_alarm_time = time.time() + (self.interval_min.get() * 60)
            self.update_ui(alerting=False)

        self.stop()

    def _show_done_popup(self, direction):
        """Popup untuk konfirmasi sudah dikerjakan dan lanjutkan."""
        # Dialog custom untuk checkbox "sudah"
        done_window = tk.Toplevel(self)
        done_window.title("Konfirmasi")
        done_window.geometry("300x150")
        done_window.attributes("-topmost", True)
        ttk.Label(done_window, text=f"Apakah sudah membalikkan badan pasien ke {direction}?").pack(pady=10)
        done_var = tk.BooleanVar()
        ttk.Checkbutton(done_window, text="Sudah", variable=done_var).pack(pady=5)
        def on_ok():
            if done_var.get():
                done_window.destroy()
                self._show_continue_popup()
            else:
                messagebox.showwarning("Peringatan", "Centang 'Sudah' untuk melanjutkan.")
        ttk.Button(done_window, text="OK", command=on_ok).pack(pady=10)
        done_window.wait_window()  # Tunggu sampai ditutup

    def _show_continue_popup(self):
        """Popup konfirmasi lanjutkan."""
        result = messagebox.askyesno("Lanjutkan?", "Lanjutkan ke rotasi berikutnya?")
        if not result:
            self.stop()

def main():
    init_tts()
    app = PengingatGUI()
    app.mainloop()

if __name__ == "__main__":
    main()
