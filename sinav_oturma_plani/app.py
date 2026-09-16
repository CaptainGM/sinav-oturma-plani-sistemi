"""Uygulamanın kompozisyon kökü: tüm ekran mixin'lerini birleştiren
SinavTakvimiApp sınıfı."""
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from .styles import configure_styles, generate_app_icon
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
        self.root.geometry("1200x700")

        self.style = ttk.Style(self.root)
        configure_styles(self.style)

        # PhotoImage referanslarını self üzerinde tutuyoruz; yerel değişkende
        # tutulsalardı fonksiyon dönüşünde çöp toplanır, görsel boş çıkardı.
        base_icon = generate_app_icon(512)
        self.app_icon_img = ImageTk.PhotoImage(base_icon.resize((64, 64), Image.LANCZOS))
        self.login_icon_img = ImageTk.PhotoImage(base_icon.resize((160, 160), Image.LANCZOS))
        self.root.iconphoto(True, self.app_icon_img)

        self.db = DatabaseManager()
        self.current_user = None
        self.current_role = None
        self.current_bolum = None

        self.show_login_screen()


    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()


    def check_derslik_requirement(self):
        """Derslik girişi yapılmış mı kontrol et"""
        if not self.current_bolum:
            return False

        cursor = self.db.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM derslikler WHERE bolum_adi=%s", (self.current_bolum,))
        count = cursor.fetchone()[0]
        cursor.close()

        return count > 0

    def log_activity(self, islem, detay=None):
        """Kim ne zaman ne yaptı kaydı (aktivite_log). Kritik işlemlerde
        (giriş, program/oturma planı oluşturma, silme, gözetmen atama) çağrılır.
        Loglama arızası ana işlemi asla engellememeli, bu yüzden hata yutulur."""
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("""
                INSERT INTO aktivite_log (kullanici, bolum_adi, islem, detay)
                VALUES (%s, %s, %s, %s)
            """, (self.current_user, self.current_bolum, islem, detay))
            self.db.connection.commit()
            cursor.close()
        except Exception as e:
            print(f"Uyarı: aktivite kaydı yazılamadı: {e}")

    def run_background_task(self, title, worker):
        """Uzun süren bir işi (ör. büyük Excel yükleme) ayrı bir thread'de
        çalıştırırken bir ilerleme çubuğu gösterir; arayüz donmaz.

        `worker(progress_callback)` arka plan thread'inde çalışır ve bitince
        kullanıcıya gösterilecek sonuç mesajını (str) döndürmelidir.
        `progress_callback(current, total, message=None)` ilerlemeyi bir
        kuyruğa yazar; Tkinter widget'ları SADECE ana thread'deki poll()
        içinde güncellenir (Tkinter thread-safe değildir, worker içinden
        doğrudan widget güncellemek/işaret vermek YANLIŞTIR).

        Pencere modal (grab_set) tutulur: işlem bitmeden aynı DB bağlantısını
        başka bir ekrandan eşzamanlı kullanmayı engeller."""
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

