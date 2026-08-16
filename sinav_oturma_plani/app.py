"""Uygulamanın kompozisyon kökü: tüm ekran mixin'lerini birleştiren
SinavTakvimiApp sınıfı."""
import queue
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from .styles import configure_styles, get_app_icon, get_login_background, get_panel_background
from .database import DatabaseManager
from .ui.auth import AuthMixin
from .ui.dashboard import DashboardMixin
from .ui.instructors import InstructorMixin
from .ui.classrooms import ClassroomMixin
from .ui.courses import CourseMixin
from .ui.students import StudentMixin
from .ui.scheduler import SchedulerMixin
from .ui.seating import SeatingMixin


class SinavTakvimiApp(AuthMixin, DashboardMixin, InstructorMixin, ClassroomMixin,
                       CourseMixin, StudentMixin, SchedulerMixin, SeatingMixin):
    def __init__(self, root):
        self.root = root
        self.root.title("Dinamik Sınav Takvimi Sistemi - Kocaeli Üniversitesi")
        self.root.geometry("1280x760")
        self.root.minsize(1024, 640)

        self.style = ttk.Style(self.root)
        configure_styles(self.style)

        # PhotoImage referansları self üzerinde tutulmalı, aksi halde çöp
        # toplanır ve görseller boş çıkar.
        base_icon = get_app_icon(512)
        self.app_icon_img = ImageTk.PhotoImage(base_icon.resize((64, 64), Image.LANCZOS))
        self.header_icon_img = ImageTk.PhotoImage(base_icon.resize((44, 44), Image.LANCZOS))
        self.login_icon_img = ImageTk.PhotoImage(base_icon.resize((150, 150), Image.LANCZOS))
        self.root.iconphoto(True, self.app_icon_img)
        self.login_bg_source = get_login_background()
        self.panel_bg_source = get_panel_background()

        self.db = DatabaseManager()
        self.current_user = None
        self.current_role = None
        self.current_bolum = None

        self.show_login_screen()


    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        # Ana menüden çıkışta üst menü çubuğu ekranda kalmasın.
        self.root.config(menu=tk.Menu(self.root))


    def check_derslik_requirement(self):
        if not self.current_bolum:
            return False

        return self.db.derslikler.count_documents({'bolum_adi': self.current_bolum}) > 0

    def log_activity(self, islem, detay=None):
        # Loglama arızası ana işlemi engellememeli.
        try:
            self.db.aktivite_log.insert_one({
                'kullanici': self.current_user,
                'bolum_adi': self.current_bolum,
                'islem': islem,
                'detay': detay,
                'created_at': datetime.now(),
            })
        except Exception as e:
            print(f"Uyarı: aktivite kaydı yazılamadı: {e}")

    def run_background_task(self, title, worker):
        """Uzun süren bir işi ilerleme çubuğuyla ayrı bir thread'de çalıştırır.

        `worker(progress_callback)` bitince gösterilecek sonuç mesajını döndürür.
        Tkinter thread-safe olmadığı için widget'lar sadece ana thread'deki
        poll() içinde güncellenir."""
        progress_window = tk.Toplevel(self.root)
        progress_window.title(title)
        progress_window.geometry("420x140")
        progress_window.resizable(False, False)
        progress_window.grab_set()

        status_var = tk.StringVar(value="Başlatılıyor...")
        tk.Label(progress_window, textvariable=status_var, font=("Segoe UI", 10)).pack(pady=(24, 10))

        progress_bar = ttk.Progressbar(progress_window, mode="determinate", length=360, maximum=100)
        progress_bar.pack(pady=5)

        q = queue.Queue()

        def progress_callback(current, total, message=None):
            q.put(("progress", current, total, message))

        def run():
            try:
                result_message = worker(progress_callback)
                q.put(("done", result_message))
            except Exception as e:
                q.put(("error", str(e)))

        threading.Thread(target=run, daemon=True).start()

        def poll():
            try:
                while True:
                    item = q.get_nowait()
                    if item[0] == "progress":
                        _, current, total, message = item
                        progress_bar['value'] = int(current / total * 100) if total else 0
                        status_var.set(message or f"{current}/{total}")
                    elif item[0] == "done":
                        progress_window.grab_release()
                        progress_window.destroy()
                        messagebox.showinfo("Sonuç", item[1])
                        return
                    elif item[0] == "error":
                        progress_window.grab_release()
                        progress_window.destroy()
                        messagebox.showerror("Hata", item[1])
                        return
            except queue.Empty:
                pass
            progress_window.after(100, poll)

        progress_window.after(100, poll)

