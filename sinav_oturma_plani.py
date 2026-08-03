import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime, timedelta
import hashlib
from PIL import Image, ImageDraw, ImageFont, ImageTk
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import random
from collections import defaultdict

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os 



try:
   
    pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf')) 
except Exception as e:
    
    print(f"Uyarı: Arial font dosyaları bulunamadı! Varsayılan font kullanılacak. Hata: {e}")

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
        self.create_tables()
        self.create_default_admin()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=os.environ.get('DB_HOST', 'localhost'),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASSWORD', ''),
                database=os.environ.get('DB_NAME', 'sinav_takvimi_db')
            )
            if self.connection.is_connected():
                print("Veritabanına başarıyla bağlanıldı")
        except Error as e:
            print(f"Hata: {e}")
            messagebox.showerror("Hata", f"Veritabanı bağlantı hatası: {e}")

    def create_tables(self):
        cursor = self.connection.cursor()

        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            sifre VARCHAR(255) NOT NULL,
            rol VARCHAR(50) NOT NULL,
            bolum VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bolumler (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bolum_adi VARCHAR(100) UNIQUE NOT NULL
        )
        """)

       
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ogretim_gorevlileri (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bolum_adi VARCHAR(100) NOT NULL,
            sicil_no VARCHAR(50) NOT NULL,
            ad_soyad VARCHAR(200) NOT NULL,
            unvan VARCHAR(100),
            email VARCHAR(255),
            telefon VARCHAR(20),
            UNIQUE KEY unique_ogretim (bolum_adi, sicil_no)
        )
        """)

        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS derslikler (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bolum_adi VARCHAR(100) NOT NULL,
            derslik_kodu VARCHAR(50) NOT NULL,
            derslik_adi VARCHAR(100) NOT NULL,
            kapasite INT NOT NULL,
            enine_sira INT NOT NULL,
            boyuna_sira INT NOT NULL,
            sira_yapisi INT NOT NULL,
            UNIQUE KEY unique_derslik (bolum_adi, derslik_kodu)
        )
        """)

        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dersler (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bolum_adi VARCHAR(100) NOT NULL,
            ders_kodu VARCHAR(50) NOT NULL,
            ders_adi VARCHAR(200) NOT NULL,
            hoca_adi VARCHAR(200),
            ogretim_gorevlisi_id INT,
            sinif VARCHAR(50),
            ders_tipi VARCHAR(50),
            FOREIGN KEY (ogretim_gorevlisi_id) REFERENCES ogretim_gorevlileri(id) ON DELETE SET NULL,
            UNIQUE KEY unique_ders (bolum_adi, ders_kodu)
        )
        """)

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ogrenciler (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bolum_adi VARCHAR(100) NOT NULL,
                ogrenci_no VARCHAR(50) NOT NULL,
                ad_soyad VARCHAR(200) NOT NULL,
                sinif VARCHAR(50),
                UNIQUE KEY unique_ogrenci (bolum_adi, ogrenci_no)
            )
        """)

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ogrenci_ders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ogrenci_id INT NOT NULL,
                ders_id INT NOT NULL,
                FOREIGN KEY (ogrenci_id) REFERENCES ogrenciler(id) ON DELETE CASCADE,
                FOREIGN KEY (ders_id) REFERENCES dersler(id) ON DELETE CASCADE,
                UNIQUE KEY unique_relation (ogrenci_id, ders_id)
            )
        """)

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sinav_programi (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bolum_adi VARCHAR(100) NOT NULL,
                ders_id INT NOT NULL,
                sinav_tarihi DATE NOT NULL,
                sinav_saati TIME NOT NULL,
                sinav_turu VARCHAR(50),
                sinav_suresi INT,
                derslik_id INT,
                atanan_ogrenci INT, -- Bu sütun eklenmeli
                FOREIGN KEY (ders_id) REFERENCES dersler(id) ON DELETE CASCADE,
                FOREIGN KEY (derslik_id) REFERENCES derslikler(id) ON DELETE SET NULL
            )
        """)

       
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oturma_plani (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sinav_id INT NOT NULL,
                ogrenci_id INT NOT NULL,
                derslik_id INT NOT NULL,
                sira_no INT NOT NULL,
                sutun_no INT NOT NULL, -- Sanal sütun numarası (örn: 11, 13)
                FOREIGN KEY (sinav_id) REFERENCES sinav_programi(id) ON DELETE CASCADE,
                FOREIGN KEY (ogrenci_id) REFERENCES ogrenciler(id) ON DELETE CASCADE,
                FOREIGN KEY (derslik_id) REFERENCES derslikler(id) ON DELETE CASCADE
            )
        """)

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS istisnai_sinav_sureleri (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bolum_adi VARCHAR(100) NOT NULL,
                ders_id INT NOT NULL,
                sinav_suresi INT NOT NULL,
                FOREIGN KEY (ders_id) REFERENCES dersler(id) ON DELETE CASCADE,
                UNIQUE KEY unique_ders_sure (bolum_adi, ders_id)
            )
        """)

        
        bolumler = [
            'Bilgisayar Müh.',
            'Yazılım Müh.',
            'Elektrik Müh.',
            'Elektronik Müh.',
            'İnşaat Müh.'
        ]

        for bolum in bolumler:
            try:
                cursor.execute("INSERT INTO bolumler (bolum_adi) VALUES (%s)", (bolum,))
            except:
                pass

        self.connection.commit()
        cursor.close()

    def create_default_admin(self):
        cursor = self.connection.cursor()
        hashed_pass = hashlib.sha256("admin123".encode()).hexdigest()
        try:
            cursor.execute("""
                INSERT INTO kullanicilar (email, sifre, rol, bolum)
                VALUES (%s, %s, %s, %s)
            """, ("admin@kocaeli.edu.tr", hashed_pass, "Admin", None))
            self.connection.commit()
        except:
            pass
        cursor.close()


class SinavTakvimiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Dinamik Sınav Takvimi Sistemi - Kocaeli Üniversitesi")
        self.root.geometry("1200x700")
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

    def show_main_menu(self):
        self.clear_screen()

        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

       
        user_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label=f"Kullanıcı: {self.current_user} ({self.current_role})", menu=user_menu)
        user_menu.add_command(label="Çıkış Yap", command=self.show_login_screen)

        if self.current_role == "Admin":
            admin_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Admin İşlemleri", menu=admin_menu)
            admin_menu.add_command(label="Yeni Kullanıcı Ekle", command=self.show_add_user_screen)
            admin_menu.add_command(label="Bölüm Seç", command=self.show_select_department)

       
        if self.current_role == "Bölüm Koordinatörü" or (self.current_role == "Admin" and self.current_bolum):
            
            koordinator_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Derslik İşlemleri", menu=koordinator_menu)
            koordinator_menu.add_command(label="Derslik Ekle", command=self.show_add_classroom)
            koordinator_menu.add_command(label="Derslik Düzenle", command=self.show_edit_classroom)
            koordinator_menu.add_command(label="Derslik Listele/Ara", command=self.show_classroom_list)

            
            if self.check_derslik_requirement():
                ders_menu = tk.Menu(menubar, tearoff=0)
                menubar.add_cascade(label="Ders İşlemleri", menu=ders_menu)
                ders_menu.add_command(label="Ders Ekle", command=self.show_add_course)
                ders_menu.add_command(label="Ders Düzenle", command=self.show_edit_course)
                ders_menu.add_command(label="Ders Listesi Yükle (Excel)", command=self.upload_course_excel)
                ders_menu.add_command(label="Ders Listesi Görüntüle", command=self.show_course_list)

                ogrenci_menu = tk.Menu(menubar, tearoff=0)
                menubar.add_cascade(label="Öğrenci İşlemleri", menu=ogrenci_menu)
                ogrenci_menu.add_command(label="Öğrenci Ekle", command=self.show_add_student)
                ogrenci_menu.add_command(label="Öğrenci Düzenle", command=self.show_edit_student)
                ogrenci_menu.add_command(label="Öğrenci Listesi Yükle (Excel)", command=self.upload_student_excel)
                ogrenci_menu.add_command(label="Öğrenci Listesi Görüntüle", command=self.show_student_list)
                ogrenci_menu.add_separator()
                ogrenci_menu.add_command(label="✨ Öğrenciye Ders Ata", command=self.show_assign_courses_to_student)

               
                ogretim_menu = tk.Menu(menubar, tearoff=0)
                menubar.add_cascade(label="Öğretim Görevlisi İşlemleri", menu=ogretim_menu)
                ogretim_menu.add_command(label="Öğretim Görevlisi Ekle", command=self.show_add_instructor)
                ogretim_menu.add_command(label="Öğretim Görevlisi Düzenle", command=self.show_edit_instructor)
                ogretim_menu.add_command(label="Öğretim Görevlisi Listele", command=self.show_instructor_list)

                sinav_menu = tk.Menu(menubar, tearoff=0)
                menubar.add_cascade(label="Sınav Programı", menu=sinav_menu)
                sinav_menu.add_command(label="Sınav Programı Oluştur", command=self.show_exam_scheduler)
                sinav_menu.add_command(label="Oturma Planı", command=self.show_seating_plan)

        welcome_frame = tk.Frame(self.root, bg="#ecf0f1")
        welcome_frame.pack(fill=tk.BOTH, expand=True)

        welcome_text = f"Hoş Geldiniz, {self.current_user}"
        if self.current_bolum:
            welcome_text += f"\nBölüm: {self.current_bolum}"

        tk.Label(welcome_frame, text=welcome_text, font=("Arial", 20), bg="#ecf0f1").pack(pady=50)

       
        if self.current_role in ["Bölüm Koordinatörü", "Admin"] and self.current_bolum and not self.check_derslik_requirement():
            warning_label = tk.Label(welcome_frame,
                                    text="⚠️ UYARI: Devam edebilmek için önce en az bir derslik girmelisiniz!",
                                    font=("Arial", 14, "bold"), bg="#ecf0f1", fg="#e74c3c")
            warning_label.pack(pady=20)

   

    def show_login_screen(self):
        self.clear_screen()

        login_frame = tk.Frame(self.root, bg="#2c3e50")
        login_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(login_frame, text="Sınav Takvimi Yönetim Sistemi",
                               font=("Arial", 24, "bold"), bg="#2c3e50", fg="white")
        title_label.pack(pady=40)

        form_frame = tk.Frame(login_frame, bg="#34495e", padx=50, pady=50)
        form_frame.pack(pady=20)

        tk.Label(form_frame, text="E-posta:", font=("Arial", 12), bg="#34495e", fg="white").grid(row=0, column=0, sticky="w", pady=10)
        email_entry = tk.Entry(form_frame, font=("Arial", 12), width=30)
        email_entry.grid(row=0, column=1, pady=10)

        tk.Label(form_frame, text="Şifre:", font=("Arial", 12), bg="#34495e", fg="white").grid(row=1, column=0, sticky="w", pady=10)
        password_entry = tk.Entry(form_frame, font=("Arial", 12), width=30, show="*")
        password_entry.grid(row=1, column=1, pady=10)

        def login():
            email = email_entry.get()
            password = password_entry.get()

            if not email or not password:
                messagebox.showerror("Hata", "Tüm alanları doldurun!")
                return

            hashed_pass = hashlib.sha256(password.encode()).hexdigest()
            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT id, email, rol, bolum FROM kullanicilar
                WHERE email=%s AND sifre=%s
            """, (email, hashed_pass))
            user = cursor.fetchone()
            cursor.close()

            if user:
                self.current_user = user[1]
                self.current_role = user[2]
                self.current_bolum = user[3]
                self.show_main_menu()
            else:
                messagebox.showerror("Hata", "Geçersiz kullanıcı adı veya şifre!")

        login_btn = tk.Button(form_frame, text="Giriş Yap", font=("Arial", 12),
                                bg="#27ae60", fg="white", width=20, command=login)
        login_btn.grid(row=2, column=0, columnspan=2, pady=20)

        info_label = tk.Label(login_frame, text="",
                                font=("Arial", 10), bg="#2c3e50", fg="#95a5a6")
        info_label.pack(pady=10)

    def show_add_user_screen(self):
        add_user_window = tk.Toplevel(self.root)
        add_user_window.title("Yeni Kullanıcı Ekle")
        add_user_window.geometry("500x400")

        tk.Label(add_user_window, text="E-posta:", font=("Arial", 11)).grid(row=0, column=0, padx=20, pady=10, sticky="w")
        email_entry = tk.Entry(add_user_window, font=("Arial", 11), width=30)
        email_entry.grid(row=0, column=1, padx=20, pady=10)

        tk.Label(add_user_window, text="Şifre:", font=("Arial", 11)).grid(row=1, column=0, padx=20, pady=10, sticky="w")
        pass_entry = tk.Entry(add_user_window, font=("Arial", 11), width=30, show="*")
        pass_entry.grid(row=1, column=1, padx=20, pady=10)

        tk.Label(add_user_window, text="Rol:", font=("Arial", 11)).grid(row=2, column=0, padx=20, pady=10, sticky="w")
        rol_var = tk.StringVar(value="Bölüm Koordinatörü")
        rol_combo = ttk.Combobox(add_user_window, textvariable=rol_var,
                                 values=["Admin", "Bölüm Koordinatörü"], state="readonly", width=28)
        rol_combo.grid(row=2, column=1, padx=20, pady=10)

        tk.Label(add_user_window, text="Bölüm:", font=("Arial", 11)).grid(row=3, column=0, padx=20, pady=10, sticky="w")

        cursor = self.db.connection.cursor()
        cursor.execute("SELECT bolum_adi FROM bolumler")
        bolumler = [row[0] for row in cursor.fetchall()]
        cursor.close()

        bolum_var = tk.StringVar()
        bolum_combo = ttk.Combobox(add_user_window, textvariable=bolum_var,
                                   values=bolumler, state="readonly", width=28)
        bolum_combo.grid(row=3, column=1, padx=20, pady=10)

        def save_user():
            email = email_entry.get()
            password = pass_entry.get()
            rol = rol_var.get()
            bolum = bolum_var.get() if rol == "Bölüm Koordinatörü" else None

            if not email or not password:
                messagebox.showerror("Hata", "E-posta ve şifre gerekli!")
                return

            if rol == "Bölüm Koordinatörü" and not bolum:
                messagebox.showerror("Hata", "Bölüm Koordinatörü için bölüm seçimi gerekli!")
                return

            hashed_pass = hashlib.sha256(password.encode()).hexdigest()
            cursor = self.db.connection.cursor()
            try:
                cursor.execute("""
                    INSERT INTO kullanicilar (email, sifre, rol, bolum)
                    VALUES (%s, %s, %s, %s)
                """, (email, hashed_pass, rol, bolum))
                self.db.connection.commit()
                messagebox.showinfo("Başarılı", "Kullanıcı eklendi!")
                add_user_window.destroy()
            except Error as e:
                messagebox.showerror("Hata", f"Kullanıcı eklenemedi: {e}")
            finally:
                cursor.close()

        tk.Button(add_user_window, text="Kaydet", font=("Arial", 12),
                  bg="#27ae60", fg="white", command=save_user).grid(row=4, column=0, columnspan=2, pady=20)

    def show_select_department(self):
        dept_window = tk.Toplevel(self.root)
        dept_window.title("Bölüm Seç")
        dept_window.geometry("400x200")

        tk.Label(dept_window, text="Yönetmek istediğiniz bölümü seçin:",
                 font=("Arial", 12)).pack(pady=20)

        cursor = self.db.connection.cursor()
        cursor.execute("SELECT bolum_adi FROM bolumler")
        bolumler = [row[0] for row in cursor.fetchall()]
        cursor.close()

        bolum_var = tk.StringVar()
        bolum_combo = ttk.Combobox(dept_window, textvariable=bolum_var,
                                   values=bolumler, state="readonly", width=30)
        bolum_combo.pack(pady=10)

        def select_dept():
            if bolum_var.get():
                self.current_bolum = bolum_var.get()
                dept_window.destroy()
                self.show_main_menu()

        tk.Button(dept_window, text="Seç", font=("Arial", 11),
                  bg="#3498db", fg="white", command=select_dept).pack(pady=20)



    def show_add_instructor(self):
        """Öğretim görevlisi ekleme ekranı"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        inst_window = tk.Toplevel(self.root)
        inst_window.title("Öğretim Görevlisi Ekle")
        inst_window.geometry("500x500")

        fields = [
            ("Sicil No:", tk.Entry(inst_window, font=("Arial", 11), width=30)),
            ("Ad Soyad:", tk.Entry(inst_window, font=("Arial", 11), width=30)),
            ("Unvan:", None),
            ("E-posta:", tk.Entry(inst_window, font=("Arial", 11), width=30)),
            ("Telefon:", tk.Entry(inst_window, font=("Arial", 11), width=30))
        ]

        entries = {}
        row = 0

        for label, widget in fields:
            tk.Label(inst_window, text=label, font=("Arial", 11)).grid(
                row=row, column=0, padx=20, pady=10, sticky="w")

            if label == "Unvan:":
                unvan_var = tk.StringVar(value="Öğr. Gör.")
                unvan_combo = ttk.Combobox(inst_window, textvariable=unvan_var,
                                           values=["Prof. Dr.", "Doç. Dr.", "Dr. Öğr. Üyesi",
                                                   "Öğr. Gör.", "Arş. Gör."],
                                           state="readonly", width=28)
                unvan_combo.grid(row=row, column=1, padx=20, pady=10)
                entries['unvan'] = unvan_var
            else:
                widget.grid(row=row, column=1, padx=20, pady=10)
                key = label.replace(":", "").replace(" ", "_").replace("-", "_").lower()
                entries[key] = widget

            row += 1

        def save_instructor():
            sicil = entries['sicil_no'].get().strip()
            ad_soyad = entries['ad_soyad'].get().strip()
            unvan = entries['unvan'].get()
            email = entries['e_posta'].get().strip()
            telefon = entries['telefon'].get().strip()

            if not all([sicil, ad_soyad]):
                messagebox.showerror("Hata", "Sicil no ve ad soyad zorunludur!")
                return

            try:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    INSERT INTO ogretim_gorevlileri (bolum_adi, sicil_no, ad_soyad, unvan, email, telefon)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (self.current_bolum, sicil, ad_soyad, unvan, email, telefon))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Öğretim görevlisi eklendi!")
                inst_window.destroy()
            except Error as e:
                if "Duplicate entry" in str(e):
                    messagebox.showerror("Hata", "Bu sicil no zaten mevcut!")
                else:
                    messagebox.showerror("Hata", f"Eklenemedi: {e}")

        tk.Button(inst_window, text="Kaydet", font=("Arial", 12),
                  bg="#27ae60", fg="white", command=save_instructor).grid(
                        row=row, column=0, columnspan=2, pady=20)

    def show_edit_instructor(self):
        """Öğretim görevlisi düzenleme ekranı"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        edit_window = tk.Toplevel(self.root)
        edit_window.title("Öğretim Görevlisi Düzenle")
        edit_window.geometry("600x550")

        tk.Label(edit_window, text="Öğretim Görevlisi Seçin:",
                 font=("Arial", 12, "bold")).pack(pady=10)

        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT id, sicil_no, ad_soyad, unvan, email, telefon
            FROM ogretim_gorevlileri WHERE bolum_adi=%s
        """, (self.current_bolum,))
        gorevliler = cursor.fetchall()
        cursor.close()

        if not gorevliler:
            messagebox.showinfo("Bilgi", "Henüz öğretim görevlisi bulunmuyor!")
            edit_window.destroy()
            return

        gorevli_dict = {}
        for g in gorevliler:
            display_text = f"{g[1]} - {g[2]} ({g[3]})"
            gorevli_dict[display_text] = g

        gorevli_var = tk.StringVar()
        gorevli_combo = ttk.Combobox(edit_window, textvariable=gorevli_var,
                                     values=list(gorevli_dict.keys()), state="readonly", width=50)
        gorevli_combo.pack(pady=10)

        edit_frame = tk.Frame(edit_window)
        edit_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        labels = ["Sicil No:", "Ad Soyad:", "Unvan:", "E-posta:", "Telefon:"]
        entries = {}

        for i, label in enumerate(labels):
            tk.Label(edit_frame, text=label, font=("Arial", 11)).grid(
                row=i, column=0, padx=10, pady=10, sticky="w")

            if label == "Unvan:":
                unvan_var = tk.StringVar()
                unvan_combo = ttk.Combobox(edit_frame, textvariable=unvan_var,
                                           values=["Prof. Dr.", "Doç. Dr.", "Dr. Öğr. Üyesi",
                                                   "Öğr. Gör.", "Arş. Gör."],
                                           state="readonly", width=28)
                unvan_combo.grid(row=i, column=1, padx=10, pady=10)
                entries[label] = unvan_var
            else:
                entry = tk.Entry(edit_frame, font=("Arial", 11), width=30)
                entry.grid(row=i, column=1, padx=10, pady=10)
                entries[label] = entry

        def load_data(event=None):
            selected = gorevli_var.get()
            if selected and selected in gorevli_dict:
                data = gorevli_dict[selected]
                entries["Sicil No:"].delete(0, tk.END)
                entries["Sicil No:"].insert(0, data[1])
                entries["Ad Soyad:"].delete(0, tk.END)
                entries["Ad Soyad:"].insert(0, data[2])
                entries["Unvan:"].set(data[3] or "Öğr. Gör.")
                entries["E-posta:"].delete(0, tk.END)
                entries["E-posta:"].insert(0, data[4] or "")
                entries["Telefon:"].delete(0, tk.END)
                entries["Telefon:"].insert(0, data[5] or "")

        gorevli_combo.bind('<<ComboboxSelected>>', load_data)

        def update_instructor():
            selected = gorevli_var.get()
            if not selected:
                messagebox.showerror("Hata", "Öğretim görevlisi seçin!")
                return

            gorevli_id = gorevli_dict[selected][0]
            sicil = entries["Sicil No:"].get().strip()
            ad_soyad = entries["Ad Soyad:"].get().strip()
            unvan = entries["Unvan:"].get()
            email = entries["E-posta:"].get().strip()
            telefon = entries["Telefon:"].get().strip()

            if not all([sicil, ad_soyad]):
                messagebox.showerror("Hata", "Sicil no ve ad soyad zorunludur!")
                return

            try:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    UPDATE ogretim_gorevlileri
                    SET sicil_no=%s, ad_soyad=%s, unvan=%s, email=%s, telefon=%s
                    WHERE id=%s AND bolum_adi=%s
                """, (sicil, ad_soyad, unvan, email, telefon, gorevli_id, self.current_bolum))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Öğretim görevlisi güncellendi!")
                edit_window.destroy()
            except Error as e:
                messagebox.showerror("Hata", f"Güncellenemedi: {e}")

        def delete_instructor():
            selected = gorevli_var.get()
            if not selected:
                messagebox.showerror("Hata", "Öğretim görevlisi seçin!")
                return

            if messagebox.askyesno("Onay", f"{selected} silinsin mi?"):
                gorevli_id = gorevli_dict[selected][0]
                cursor = self.db.connection.cursor()
                cursor.execute("DELETE FROM ogretim_gorevlileri WHERE id=%s AND bolum_adi=%s",
                               (gorevli_id, self.current_bolum))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Öğretim görevlisi silindi!")
                edit_window.destroy()

        btn_frame = tk.Frame(edit_window)
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="Güncelle", font=("Arial", 11),
                  bg="#27ae60", fg="white", command=update_instructor).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Sil", font=("Arial", 11),
                  bg="#e74c3c", fg="white", command=delete_instructor).pack(side=tk.LEFT, padx=5)

    def show_instructor_list(self):
        """Öğretim görevlisi listesi"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        list_window = tk.Toplevel(self.root)
        list_window.title("Öğretim Görevlisi Listesi")
        list_window.geometry("900x600")

        tk.Label(list_window, text=f"{self.current_bolum} - Öğretim Görevlileri",
                 font=("Arial", 14, "bold")).pack(pady=10)

        tree_frame = tk.Frame(list_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("Sicil No", "Ad Soyad", "Unvan", "E-posta", "Telefon")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                            yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)

        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT sicil_no, ad_soyad, unvan, email, telefon
            FROM ogretim_gorevlileri WHERE bolum_adi=%s
            ORDER BY ad_soyad
        """, (self.current_bolum,))

        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row)
        cursor.close()

        tree.pack(fill=tk.BOTH, expand=True)

  

    def show_add_classroom(self):
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        classroom_window = tk.Toplevel(self.root)
        classroom_window.title("Derslik Ekle")
        classroom_window.geometry("500x500")

        fields = [
            ("Derslik Kodu:", tk.Entry(classroom_window, font=("Arial", 11), width=30)),
            ("Derslik Adı:", tk.Entry(classroom_window, font=("Arial", 11), width=30)),
            ("Kapasite:", tk.Entry(classroom_window, font=("Arial", 11), width=30)),
            ("Enine Sıra Sayısı:", tk.Entry(classroom_window, font=("Arial", 11), width=30)),
            ("Boyuna Sıra Sayısı:", tk.Entry(classroom_window, font=("Arial", 11), width=30)),
            ("Sıra Yapısı (2 veya 3):", tk.Entry(classroom_window, font=("Arial", 11), width=30))
        ]

        entries = []
        for i, (label, entry) in enumerate(fields):
            tk.Label(classroom_window, text=label, font=("Arial", 11)).grid(row=i, column=0, padx=20, pady=10, sticky="w")
            entry.grid(row=i, column=1, padx=20, pady=10)
            entries.append(entry)

        def save_classroom():
            values = [e.get() for e in entries]
            if not all(values):
                messagebox.showerror("Hata", "Tüm alanları doldurun!")
                return

            try:
                kapasite = int(values[2])
                enine = int(values[3])
                boyuna = int(values[4])
                sira_yapi = int(values[5])

                if sira_yapi not in [2, 3]:
                    messagebox.showerror("Hata", "Sıra yapısı 2 veya 3 olmalı!")
                    return

                cursor = self.db.connection.cursor()
                cursor.execute("""
                    INSERT INTO derslikler (bolum_adi, derslik_kodu, derslik_adi, kapasite,
                                            enine_sira, boyuna_sira, sira_yapisi)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (self.current_bolum, values[0], values[1], kapasite, enine, boyuna, sira_yapi))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Derslik eklendi!")
                classroom_window.destroy()
                self.show_main_menu()  
            except ValueError:
                messagebox.showerror("Hata", "Sayısal değerler geçerli olmalı!")
            except Error as e:
                messagebox.showerror("Hata", f"Derslik eklenemedi: {e}")

        tk.Button(classroom_window, text="Kaydet", font=("Arial", 12),
                  bg="#27ae60", fg="white", command=save_classroom).grid(row=6, column=0, columnspan=2, pady=20)

    def show_edit_classroom(self):
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        edit_window = tk.Toplevel(self.root)
        edit_window.title("Derslik Düzenle")
        edit_window.geometry("600x600")

        
        tk.Label(edit_window, text="Düzenlenecek Dersliği Seçin:", font=("Arial", 12, "bold")).pack(pady=10)

        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT id, derslik_kodu, derslik_adi, kapasite, enine_sira, boyuna_sira, sira_yapisi
            FROM derslikler WHERE bolum_adi=%s
        """, (self.current_bolum,))
        derslikler = cursor.fetchall()
        cursor.close()

        if not derslikler:
            messagebox.showinfo("Bilgi", "Henüz derslik bulunmuyor!")
            edit_window.destroy()
            return

        derslik_dict = {}
        for d in derslikler:
            display_text = f"{d[1]} - {d[2]}"
            derslik_dict[display_text] = d

        derslik_var = tk.StringVar()
        derslik_combo = ttk.Combobox(edit_window, textvariable=derslik_var,
                                     values=list(derslik_dict.keys()), state="readonly", width=40)
        derslik_combo.pack(pady=10)

        
        edit_frame = tk.Frame(edit_window)
        edit_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        labels = ["Derslik Kodu:", "Derslik Adı:", "Kapasite:", "Enine Sıra:", "Boyuna Sıra:", "Sıra Yapısı:"]
        entries = []

        for i, label in enumerate(labels):
            tk.Label(edit_frame, text=label, font=("Arial", 11)).grid(row=i, column=0, padx=10, pady=10, sticky="w")
            entry = tk.Entry(edit_frame, font=("Arial", 11), width=30)
            entry.grid(row=i, column=1, padx=10, pady=10)
            entries.append(entry)

        def load_classroom_data(event=None):
            selected = derslik_var.get()
            if selected and selected in derslik_dict:
                data = derslik_dict[selected]
                entries[0].delete(0, tk.END)
                entries[0].insert(0, data[1])
                entries[1].delete(0, tk.END)
                entries[1].insert(0, data[2])
                entries[2].delete(0, tk.END)
                entries[2].insert(0, data[3])
                entries[3].delete(0, tk.END)
                entries[3].insert(0, data[4])
                entries[4].delete(0, tk.END)
                entries[4].insert(0, data[5])
                entries[5].delete(0, tk.END)
                entries[5].insert(0, data[6])

        derslik_combo.bind('<<ComboboxSelected>>', load_classroom_data)

        def update_classroom():
            selected = derslik_var.get()
            if not selected:
                messagebox.showerror("Hata", "Derslik seçin!")
                return

            derslik_id = derslik_dict[selected][0]
            values = [e.get() for e in entries]

            if not all(values):
                messagebox.showerror("Hata", "Tüm alanları doldurun!")
                return

            try:
                kapasite = int(values[2])
                enine = int(values[3])
                boyuna = int(values[4])
                sira_yapi = int(values[5])

                if sira_yapi not in [2, 3]:
                    messagebox.showerror("Hata", "Sıra yapısı 2 veya 3 olmalı!")
                    return

                cursor = self.db.connection.cursor()
                cursor.execute("""
                    UPDATE derslikler
                    SET derslik_kodu=%s, derslik_adi=%s, kapasite=%s,
                        enine_sira=%s, boyuna_sira=%s, sira_yapisi=%s
                    WHERE id=%s AND bolum_adi=%s
                """, (values[0], values[1], kapasite, enine, boyuna, sira_yapi, derslik_id, self.current_bolum))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Derslik güncellendi!")
                edit_window.destroy()
            except ValueError:
                messagebox.showerror("Hata", "Sayısal değerler geçerli olmalı!")
            except Error as e:
                messagebox.showerror("Hata", f"Derslik güncellenemedi: {e}")

        tk.Button(edit_window, text="Güncelle", font=("Arial", 12),
                  bg="#27ae60", fg="white", command=update_classroom).pack(pady=20)

    def show_classroom_list(self):
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        list_window = tk.Toplevel(self.root)
        list_window.title("Derslik Listesi")
        list_window.geometry("900x600")

        search_frame = tk.Frame(list_window)
        search_frame.pack(pady=10)

        tk.Label(search_frame, text="Derslik Kodu:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
        search_entry = tk.Entry(search_frame, font=("Arial", 11), width=20)
        search_entry.pack(side=tk.LEFT, padx=5)

        def search_classroom():
            kod = search_entry.get()
            if not kod:
                messagebox.showerror("Hata", "Derslik kodu girin!")
                return

            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT * FROM derslikler
                WHERE bolum_adi=%s AND derslik_kodu=%s
            """, (self.current_bolum, kod))
            result = cursor.fetchone()
            cursor.close()

            if result:
                self.visualize_classroom(result)
            else:
                messagebox.showinfo("Bilgi", "Derslik bulunamadı!")

        tk.Button(search_frame, text="Ara ve Görselleştir", font=("Arial", 11),
                  bg="#3498db", fg="white", command=search_classroom).pack(side=tk.LEFT, padx=5)

       
        tree_frame = tk.Frame(list_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("Kod", "Ad", "Kapasite", "Enine", "Boyuna", "Yapı")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)

        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT derslik_kodu, derslik_adi, kapasite, enine_sira, boyuna_sira, sira_yapisi
            FROM derslikler WHERE bolum_adi=%s
        """, (self.current_bolum,))

        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row)
        cursor.close()

        tree.pack(fill=tk.BOTH, expand=True)

        def delete_classroom():
            selected = tree.selection()
            if not selected:
                messagebox.showerror("Hata", "Silinecek dersliği seçin!")
                return

            item = tree.item(selected[0])
            kod = item['values'][0]

            if messagebox.askyesno("Onay", f"{kod} kodlu derslik silinsin mi?"):
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    DELETE FROM derslikler
                    WHERE bolum_adi=%s AND derslik_kodu=%s
                """, (self.current_bolum, kod))
                self.db.connection.commit()
                cursor.close()
                tree.delete(selected[0])
                messagebox.showinfo("Başarılı", "Derslik silindi!")

        tk.Button(list_window, text="Seçili Dersliği Sil", font=("Arial", 11),
                  bg="#e74c3c", fg="white", command=delete_classroom).pack(pady=10)

    def visualize_classroom(self, classroom_data):
        vis_window = tk.Toplevel(self.root)
        vis_window.title(f"Derslik Görselleştirme - {classroom_data[3]}")
        vis_window.geometry("800x600")

        info_text = f"""
Derslik: {classroom_data[3]} ({classroom_data[2]})
Kapasite: {classroom_data[4]}
Enine Sıra: {classroom_data[5]} | Boyuna Sıra: {classroom_data[6]}
Sıra Yapısı: {classroom_data[7]}'lü
        """

        tk.Label(vis_window, text=info_text, font=("Arial", 11), justify=tk.LEFT).pack(pady=10)

        canvas_frame = tk.Frame(vis_window)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        canvas_widget = tk.Canvas(canvas_frame, bg="white")
        canvas_widget.pack(fill=tk.BOTH, expand=True)

        enine = classroom_data[5]
        boyuna = classroom_data[6]
        sira_yapi = classroom_data[7]

        cell_width = 40
        cell_height = 30
        gap = 10

        for row in range(boyuna):
            for col in range(enine):
                x1 = col * (cell_width + gap) + 50
                y1 = row * (cell_height + gap) + 50
                x2 = x1 + cell_width
                y2 = y1 + cell_height

                
                color = "#3498db" if (col % sira_yapi) < (sira_yapi - 1) else "#95a5a6"
                canvas_widget.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
                canvas_widget.create_text((x1+x2)/2, (y1+y2)/2,
                                         text=f"{row+1},{col+1}", font=("Arial", 8))

    

    def show_add_course(self):
        """Manuel ders ekleme ekranı"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        course_window = tk.Toplevel(self.root)
        course_window.title("Ders Ekle")
        course_window.geometry("500x450")

        fields = [
            ("Ders Kodu:", tk.Entry(course_window, font=("Arial", 11), width=30)),
            ("Ders Adı:", tk.Entry(course_window, font=("Arial", 11), width=30)),
            ("Öğretim Üyesi:", tk.Entry(course_window, font=("Arial", 11), width=30)),
            ("Sınıf:", None),
            ("Ders Tipi:", None)
        ]

        entries = {}
        row = 0

        for label, widget in fields:
            tk.Label(course_window, text=label, font=("Arial", 11)).grid(
                row=row, column=0, padx=20, pady=10, sticky="w")

            if label == "Sınıf:":
                sinif_var = tk.StringVar(value="1")
                sinif_combo = ttk.Combobox(course_window, textvariable=sinif_var,
                                           values=["1", "2", "3", "4", "Hazırlık"],
                                           state="readonly", width=28)
                sinif_combo.grid(row=row, column=1, padx=20, pady=10)
                entries['sinif'] = sinif_var
            elif label == "Ders Tipi:":
                tip_var = tk.StringVar(value="Zorunlu")
                tip_combo = ttk.Combobox(course_window, textvariable=tip_var,
                                           values=["Zorunlu", "Seçmeli"],
                                           state="readonly", width=28)
                tip_combo.grid(row=row, column=1, padx=20, pady=10)
                entries['tip'] = tip_var
            else:
                widget.grid(row=row, column=1, padx=20, pady=10)
                entries[label.replace(":", "").replace(" ", "_").lower()] = widget

            row += 1

        def save_course():
            ders_kodu = entries['ders_kodu'].get().strip()
            ders_adı = entries['ders_adı'].get().strip()
            hoca_adı = entries['öğretim_üyesi'].get().strip()
            sinif = entries['sinif'].get()
            ders_tipi = entries['tip'].get()

            if not all([ders_kodu, ders_adı, hoca_adı]):
                messagebox.showerror("Hata", "Ders kodu, ders adı ve öğretim üyesi zorunludur!")
                return

            try:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    INSERT INTO dersler (bolum_adi, ders_kodu, ders_adi, hoca_adi, sinif, ders_tipi)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (self.current_bolum, ders_kodu, ders_adı, hoca_adı, sinif, ders_tipi))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Ders başarıyla eklendi!")
                course_window.destroy()
            except Error as e:
                if "Duplicate entry" in str(e):
                    messagebox.showerror("Hata", "Bu ders kodu zaten mevcut!")
                else:
                    messagebox.showerror("Hata", f"Ders eklenemedi: {e}")

        tk.Button(course_window, text="Kaydet", font=("Arial", 12),
                  bg="#27ae60", fg="white", command=save_course).grid(
                        row=row, column=0, columnspan=2, pady=20)

    def show_edit_course(self):
        """Ders düzenleme ekranı"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        edit_window = tk.Toplevel(self.root)
        edit_window.title("Ders Düzenle")
        edit_window.geometry("600x550")

        tk.Label(edit_window, text="Düzenlenecek Dersi Seçin:",
                 font=("Arial", 12, "bold")).pack(pady=10)

        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT id, ders_kodu, ders_adi, hoca_adi, sinif, ders_tipi
            FROM dersler WHERE bolum_adi=%s
        """, (self.current_bolum,))
        dersler = cursor.fetchall()
        cursor.close()

        if not dersler:
            messagebox.showinfo("Bilgi", "Henüz ders bulunmuyor!")
            edit_window.destroy()
            return

        ders_dict = {}
        for d in dersler:
            display_text = f"{d[1]} - {d[2]}"
            ders_dict[display_text] = d

        ders_var = tk.StringVar()
        ders_combo = ttk.Combobox(edit_window, textvariable=ders_var,
                                  values=list(ders_dict.keys()), state="readonly", width=50)
        ders_combo.pack(pady=10)

        edit_frame = tk.Frame(edit_window)
        edit_frame.pack(pady=20, padx=20, fill=tk.BOTH, expand=True)

        labels = ["Ders Kodu:", "Ders Adı:", "Öğretim Üyesi:", "Sınıf:", "Ders Tipi:"]
        entries = {}

        for i, label in enumerate(labels):
            tk.Label(edit_frame, text=label, font=("Arial", 11)).grid(
                row=i, column=0, padx=10, pady=10, sticky="w")

            if label == "Sınıf:":
                sinif_var = tk.StringVar()
                sinif_combo = ttk.Combobox(edit_frame, textvariable=sinif_var,
                                           values=["1", "2", "3", "4", "Hazırlık"],
                                           state="readonly", width=28)
                sinif_combo.grid(row=i, column=1, padx=10, pady=10)
                entries[label] = sinif_var
            elif label == "Ders Tipi:":
                tip_var = tk.StringVar()
                tip_combo = ttk.Combobox(edit_frame, textvariable=tip_var,
                                           values=["Zorunlu", "Seçmeli"],
                                           state="readonly", width=28)
                tip_combo.grid(row=i, column=1, padx=10, pady=10)
                entries[label] = tip_var
            else:
                entry = tk.Entry(edit_frame, font=("Arial", 11), width=30)
                entry.grid(row=i, column=1, padx=10, pady=10)
                entries[label] = entry

        def load_course_data(event=None):
            selected = ders_var.get()
            if selected and selected in ders_dict:
                data = ders_dict[selected]
                entries["Ders Kodu:"].delete(0, tk.END)
                entries["Ders Kodu:"].insert(0, data[1])
                entries["Ders Adı:"].delete(0, tk.END)
                entries["Ders Adı:"].insert(0, data[2])
                entries["Öğretim Üyesi:"].delete(0, tk.END)
                entries["Öğretim Üyesi:"].insert(0, data[3] or "")
                entries["Sınıf:"].set(data[4] or "1")
                entries["Ders Tipi:"].set(data[5] or "Zorunlu")

        ders_combo.bind('<<ComboboxSelected>>', load_course_data)

        def update_course():
            selected = ders_var.get()
            if not selected:
                messagebox.showerror("Hata", "Ders seçin!")
                return

            ders_id = ders_dict[selected][0]
            ders_kodu = entries["Ders Kodu:"].get().strip()
            ders_adi = entries["Ders Adı:"].get().strip()
            hoca_adi = entries["Öğretim Üyesi:"].get().strip()
            sinif = entries["Sınıf:"].get()
            ders_tipi = entries["Ders Tipi:"].get()

            if not all([ders_kodu, ders_adi]):
                messagebox.showerror("Hata", "Ders kodu ve adı zorunludur!")
                return

            try:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    UPDATE dersler
                    SET ders_kodu=%s, ders_adi=%s, hoca_adi=%s, sinif=%s, ders_tipi=%s
                    WHERE id=%s AND bolum_adi=%s
                """, (ders_kodu, ders_adi, hoca_adi, sinif, ders_tipi, ders_id, self.current_bolum))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Ders güncellendi!")
                edit_window.destroy()
            except Error as e:
                messagebox.showerror("Hata", f"Ders güncellenemedi: {e}")

        def delete_course():
            selected = ders_var.get()
            if not selected:
                messagebox.showerror("Hata", "Ders seçin!")
                return

            if messagebox.askyesno("Onay", f"{selected} dersi silinsin mi?"):
                ders_id = ders_dict[selected][0]
                cursor = self.db.connection.cursor()
                cursor.execute("DELETE FROM dersler WHERE id=%s AND bolum_adi=%s",
                               (ders_id, self.current_bolum))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Ders silindi!")
                edit_window.destroy()

        btn_frame = tk.Frame(edit_window)
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="Güncelle", font=("Arial", 11),
                  bg="#27ae60", fg="white", command=update_course).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Sil", font=("Arial", 11),
                  bg="#e74c3c", fg="white", command=delete_course).pack(side=tk.LEFT, padx=5)

    def upload_course_excel(self):
        """Ders listesi Excel yükle - Gelişmiş format tanıma"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        file_path = filedialog.askopenfilename(
            title="Ders Listesi Excel Dosyası Seç",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )

        if not file_path:
            return

        try:
            
            df_preview = pd.read_excel(file_path, nrows=10, header=None)

            
            header_row = None
            for i in range(len(df_preview)):
                row_values = df_preview.iloc[i].astype(str).str.upper().tolist()
                if any('DERS KODU' in str(val) for val in row_values):
                    header_row = i
                    break

            if header_row is None:
                messagebox.showerror(
                    "Hata",
                    "Excel dosyasında 'DERS KODU' sütun başlığı bulunamadı!\n\n"
                    "Dosyanızda şu sütunlar olmalı:\n"
                    "- DERS KODU\n"
                    "- DERSİN ADI\n"
                    "- DERSİ VEREN ÖĞR. ELEMANI"
                )
                return

            
            df = pd.read_excel(file_path, header=header_row)

            
            df.columns = df.columns.astype(str).str.strip()

           
            col_mapping = {}
            required = {
                'ders_kodu': ['DERS KODU', 'DERSKODU', 'KOD'],
                'ders_adi': ['DERSİN ADI', 'DERS ADI', 'DERSADI', 'DERS'],
                'hoca_adi': ['DERSİ VEREN ÖĞR. ELEMANI', 'HOCA', 'ÖĞRETIM ELEMANI', 'ÖĞRETİM ÜYESİ', 'DERS VEREN ÖĞR. ELEMANI']
            }

            used_cols = set()
            for key, alternatives in required.items():
                found = False
                for col in df.columns:
                    col_upper = str(col).upper()
                    if any(alt.upper() == col_upper for alt in alternatives):
                        col_mapping[key] = col
                        found = True
                        break

                if not found:
                    messagebox.showerror(
                        "Hata",
                        f"Gerekli sütun bulunamadı: {alternatives[0]}\n\n"
                        f"Dosyada bulunan sütunlar:\n{', '.join(df.columns)}"
                    )
                    return

            cursor = self.db.connection.cursor()
            success_count = 0
            error_list = []
            current_sinif = "1"  

            for index, row in df.iterrows():
                try:
                    
                    first_col = str(row[df.columns[0]]).strip()
                    if 'SINIF' in first_col.upper() or 'Sınıf' in first_col:
                        
                        import re
                        sinif_match = re.search(r'(\d+)', first_col)
                        if sinif_match:
                            current_sinif = sinif_match.group(1)
                        continue

                    
                    ders_kodu = str(row[col_mapping['ders_kodu']]).strip()
                    ders_adi = str(row[col_mapping['ders_adi']]).strip()
                    hoca_adi = str(row[col_mapping['hoca_adi']]).strip()

                    
                    if (not ders_kodu or ders_kodu == 'nan' or ders_kodu == '' or
                            'DERS KODU' in ders_kodu.upper()):
                        continue

                    ders_tipi = "Zorunlu"  

                    
                    cursor.execute("""
                        INSERT INTO dersler (bolum_adi, ders_kodu, ders_adi, hoca_adi, sinif, ders_tipi)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            ders_adi=%s, hoca_adi=%s, sinif=%s, ders_tipi=%s
                    """, (self.current_bolum, ders_kodu, ders_adi, hoca_adi, current_sinif, ders_tipi,
                          ders_adi, hoca_adi, current_sinif, ders_tipi))

                    success_count += 1

                except Error as e:
                    error_msg = f"Satır {index+2}: DB Hatası - {str(e)}"
                    error_list.append(error_msg)
                except Exception as e:
                    error_msg = f"Satır {index+2}: {str(e)}"
                    error_list.append(error_msg)

            self.db.connection.commit()
            cursor.close()

            message = f"✅ {success_count} ders başarıyla yüklendi!"
            if error_list:
                message += f"\n\n⚠️ {len(error_list)} satırda hata:\n" + "\n".join(error_list[:3])
                if len(error_list) > 3:
                    message += f"\n... ve {len(error_list)-3} hata daha"

            messagebox.showinfo("Sonuç", message)

        except Exception as e:
            messagebox.showerror("Hata", f"Excel okuma hatası:\n{str(e)}")


    def show_course_list(self):
        """Ders listesini göster"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        course_window = tk.Toplevel(self.root)
        course_window.title("Ders Listesi")
        course_window.geometry("1100x600")

        
        left_frame = tk.Frame(course_window)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(left_frame, text="Dersler", font=("Arial", 14, "bold")).pack(pady=5)

        tree_frame = tk.Frame(left_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        
        columns = ("Ders Kodu", "Ders Adı", "Hoca", "Sınıf")
        course_tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                   yscrollcommand=scrollbar.set, selectmode='browse')
        scrollbar.config(command=course_tree.yview)

        course_tree.heading("Ders Kodu", text="Ders Kodu")
        course_tree.heading("Ders Adı", text="Ders Adı")
        course_tree.heading("Hoca", text="Öğretim Üyesi")
        course_tree.heading("Sınıf", text="Sınıf")

        course_tree.column("Ders Kodu", width=100)
        course_tree.column("Ders Adı", width=250)
        course_tree.column("Hoca", width=200)
        course_tree.column("Sınıf", width=80)

        course_tree.pack(fill=tk.BOTH, expand=True)

        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT id, ders_kodu, ders_adi, hoca_adi, sinif FROM dersler
            WHERE bolum_adi=%s ORDER BY sinif, ders_kodu
        """, (self.current_bolum,))
        courses = cursor.fetchall()
        cursor.close()

        course_dict = {}
        for course in courses:
            ders_id = course[0]
            ders_kodu = course[1]
            ders_adi = course[2]
            hoca_adi = course[3] if course[3] else "Belirtilmemiş"
            sinif = course[4]

            item_id = course_tree.insert("", tk.END, values=(ders_kodu, ders_adi, hoca_adi, sinif))
            course_dict[item_id] = ders_id

        
        right_frame = tk.Frame(course_window)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(right_frame, text="Dersi Alan Öğrenciler", font=("Arial", 14, "bold")).pack(pady=5)

        student_tree_frame = tk.Frame(right_frame)
        student_tree_frame.pack(fill=tk.BOTH, expand=True)

        tree_scrollbar = tk.Scrollbar(student_tree_frame)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        student_columns = ("Öğrenci No", "Ad Soyad", "Sınıf")
        student_tree = ttk.Treeview(student_tree_frame, columns=student_columns, show="headings",
                                    yscrollcommand=tree_scrollbar.set)
        tree_scrollbar.config(command=student_tree.yview)

        for col in student_columns:
            student_tree.heading(col, text=col)
            student_tree.column(col, width=150)

        student_tree.pack(fill=tk.BOTH, expand=True)

        def on_course_select(event):
            selection = course_tree.selection()
            if not selection:
                return

            item_id = selection[0]
            ders_id = course_dict[item_id]

            
            for item in student_tree.get_children():
                student_tree.delete(item)

            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT o.ogrenci_no, o.ad_soyad, o.sinif
                FROM ogrenciler o
                JOIN ogrenci_ders od ON o.id = od.ogrenci_id
                WHERE od.ders_id=%s
                ORDER BY o.ogrenci_no
            """, (ders_id,))

            for student in cursor.fetchall():
                student_tree.insert("", tk.END, values=student)
            cursor.close()

        course_tree.bind('<<TreeviewSelect>>', on_course_select)

   

    def show_add_student(self):
        """Manuel öğrenci ekleme ekranı"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        student_window = tk.Toplevel(self.root)
        student_window.title("Öğrenci Ekle")
        student_window.geometry("500x400")

        tk.Label(student_window, text="Öğrenci No:", font=("Arial", 11)).grid(
            row=0, column=0, padx=20, pady=10, sticky="w")
        ogrenci_no_entry = tk.Entry(student_window, font=("Arial", 11), width=30)
        ogrenci_no_entry.grid(row=0, column=1, padx=20, pady=10)

        tk.Label(student_window, text="Ad Soyad:", font=("Arial", 11)).grid(
            row=1, column=0, padx=20, pady=10, sticky="w")
        ad_soyad_entry = tk.Entry(student_window, font=("Arial", 11), width=30)
        ad_soyad_entry.grid(row=1, column=1, padx=20, pady=10)

        tk.Label(student_window, text="Sınıf:", font=("Arial", 11)).grid(
            row=2, column=0, padx=20, pady=10, sticky="w")
        sinif_var = tk.StringVar(value="1")
        sinif_combo = ttk.Combobox(student_window, textvariable=sinif_var,
                                   values=["1", "2", "3", "4", "Hazırlık"],
                                   state="readonly", width=28)
        sinif_combo.grid(row=2, column=1, padx=20, pady=10)

        def save_student():
            ogrenci_no = ogrenci_no_entry.get().strip()
            ad_soyad = ad_soyad_entry.get().strip()
            sinif = sinif_var.get()

            if not all([ogrenci_no, ad_soyad]):
                messagebox.showerror("Hata", "Öğrenci no ve ad soyad zorunludur!")
                return

            try:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    INSERT INTO ogrenciler (bolum_adi, ogrenci_no, ad_soyad, sinif)
                    VALUES (%s, %s, %s, %s)
                """, (self.current_bolum, ogrenci_no, ad_soyad, sinif))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Öğrenci başarıyla eklendi!")
                student_window.destroy()
            except Error as e:
                if "Duplicate entry" in str(e):
                    messagebox.showerror("Hata", "Bu öğrenci numarası zaten mevcut!")
                else:
                    messagebox.showerror("Hata", f"Öğrenci eklenemedi: {e}")

        tk.Button(student_window, text="Kaydet", font=("Arial", 12),
                  bg="#27ae60", fg="white", command=save_student).grid(
                        row=3, column=0, columnspan=2, pady=20)

    def show_edit_student(self):
        """Öğrenci düzenleme ekranı"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        edit_window = tk.Toplevel(self.root)
        edit_window.title("Öğrenci Düzenle")
        edit_window.geometry("600x500")

        tk.Label(edit_window, text="Öğrenci Ara (No veya Ad):",
                 font=("Arial", 12, "bold")).pack(pady=10)

        search_frame = tk.Frame(edit_window)
        search_frame.pack(pady=5)

        search_entry = tk.Entry(search_frame, font=("Arial", 11), width=30)
        search_entry.pack(side=tk.LEFT, padx=5)

        result_listbox = tk.Listbox(edit_window, font=("Arial", 10), height=8)
        result_listbox.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        student_dict = {}

        def search_students():
            query = search_entry.get().strip()
            if not query:
                messagebox.showerror("Hata", "Arama terimi girin!")
                return

            result_listbox.delete(0, tk.END)
            student_dict.clear()

            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT id, ogrenci_no, ad_soyad, sinif
                FROM ogrenciler
                WHERE bolum_adi=%s AND (ogrenci_no LIKE %s OR ad_soyad LIKE %s)
            """, (self.current_bolum, f"%{query}%", f"%{query}%"))

            students = cursor.fetchall()
            cursor.close()

            for s in students:
                display_text = f"{s[1]} - {s[2]} (Sınıf: {s[3]})"
                result_listbox.insert(tk.END, display_text)
                student_dict[display_text] = s

            if not students:
                messagebox.showinfo("Bilgi", "Öğrenci bulunamadı!")

        tk.Button(search_frame, text="Ara", font=("Arial", 11),
                  bg="#3498db", fg="white", command=search_students).pack(side=tk.LEFT, padx=5)

        edit_frame = tk.LabelFrame(edit_window, text="Seçili Öğrenci Bilgileri",
                                   font=("Arial", 11, "bold"), padx=20, pady=10)
        edit_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(edit_frame, text="Öğrenci No:", font=("Arial", 10)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w")
        no_entry = tk.Entry(edit_frame, font=("Arial", 10), width=25)
        no_entry.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(edit_frame, text="Ad Soyad:", font=("Arial", 10)).grid(
            row=1, column=0, padx=10, pady=5, sticky="w")
        ad_entry = tk.Entry(edit_frame, font=("Arial", 10), width=25)
        ad_entry.grid(row=1, column=1, padx=10, pady=5)

        tk.Label(edit_frame, text="Sınıf:", font=("Arial", 10)).grid(
            row=2, column=0, padx=10, pady=5, sticky="w")
        sinif_var = tk.StringVar()
        sinif_combo = ttk.Combobox(edit_frame, textvariable=sinif_var,
                                   values=["1", "2", "3", "4", "Hazırlık"],
                                   state="readonly", width=23)
        sinif_combo.grid(row=2, column=1, padx=10, pady=5)

        selected_id = [None]

        def load_student_data(event):
            selection = result_listbox.curselection()
            if not selection:
                return

            selected_text = result_listbox.get(selection[0])
            if selected_text in student_dict:
                data = student_dict[selected_text]
                selected_id[0] = data[0]
                no_entry.delete(0, tk.END)
                no_entry.insert(0, data[1])
                ad_entry.delete(0, tk.END)
                ad_entry.insert(0, data[2])
                sinif_var.set(data[3])

        result_listbox.bind('<<ListboxSelect>>', load_student_data)

        def update_student():
            if not selected_id[0]:
                messagebox.showerror("Hata", "Öğrenci seçin!")
                return

            ogrenci_no = no_entry.get().strip()
            ad_soyad = ad_entry.get().strip()
            sinif = sinif_var.get()

            if not all([ogrenci_no, ad_soyad]):
                messagebox.showerror("Hata", "Tüm alanları doldurun!")
                return

            try:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    UPDATE ogrenciler
                    SET ogrenci_no=%s, ad_soyad=%s, sinif=%s
                    WHERE id=%s AND bolum_adi=%s
                """, (ogrenci_no, ad_soyad, sinif, selected_id[0], self.current_bolum))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Öğrenci güncellendi!")
                search_students()  
            except Error as e:
                messagebox.showerror("Hata", f"Öğrenci güncellenemedi: {e}")

        def delete_student():
            if not selected_id[0]:
                messagebox.showerror("Hata", "Öğrenci seçin!")
                return

            if messagebox.askyesno("Onay", "Öğrenci silinsin mi?"):
                cursor = self.db.connection.cursor()
                cursor.execute("DELETE FROM ogrenciler WHERE id=%s AND bolum_adi=%s",
                               (selected_id[0], self.current_bolum))
                self.db.connection.commit()
                cursor.close()
                messagebox.showinfo("Başarılı", "Öğrenci silindi!")
                search_students()  
                selected_id[0] = None

        btn_frame = tk.Frame(edit_window)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Güncelle", font=("Arial", 11),
                  bg="#27ae60", fg="white", command=update_student).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Sil", font=("Arial", 11),
                  bg="#e74c3c", fg="white", command=delete_student).pack(side=tk.LEFT, padx=5)

    def upload_student_excel(self):
        """Öğrenci listesi Excel yükle - Gerçek format uyumluluğu"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        file_path = filedialog.askopenfilename(
            title="Öğrenci Listesi Excel Dosyası Seç",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )

        if not file_path:
            return

        try:
            df = pd.read_excel(file_path)

            
            df.columns = df.columns.str.strip()

            
            required_cols = ['Öğrenci No', 'Ad Soyad', 'Sınıf', 'Ders']

            missing_cols = []
            for col in required_cols:
                if col not in df.columns:
                    missing_cols.append(col)

            if missing_cols:
                available_cols = list(df.columns)
                messagebox.showerror(
                    "Hata",
                    f"Eksik sütunlar: {', '.join(missing_cols)}\n\n"
                    f"Dosyada mevcut sütunlar: {', '.join(available_cols)}\n\n"
                    f"Gerekli sütunlar: Öğrenci No, Ad Soyad, Sınıf, Ders"
                )
                return

            cursor = self.db.connection.cursor()
            success_count = 0
            error_list = []

            for index, row in df.iterrows():
                try:
                    ogrenci_no = str(row['Öğrenci No']).strip()
                    ad_soyad = str(row['Ad Soyad']).strip()
                    sinif = str(row['Sınıf']).strip()
                    ders_kodu = str(row['Ders']).strip()

                    
                    if not ogrenci_no or ogrenci_no == 'nan' or ogrenci_no == '':
                        continue

                    
                    cursor.execute("""
                        INSERT INTO ogrenciler (bolum_adi, ogrenci_no, ad_soyad, sinif)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE ad_soyad=%s, sinif=%s
                    """, (self.current_bolum, ogrenci_no, ad_soyad, sinif, ad_soyad, sinif))

                    
                    cursor.execute("""
                        SELECT id FROM ogrenciler
                        WHERE bolum_adi=%s AND ogrenci_no=%s
                    """, (self.current_bolum, ogrenci_no))
                    ogrenci_result = cursor.fetchone()

                    if not ogrenci_result:
                        error_list.append(f"Satır {index+2}: Öğrenci kaydedilemedi - {ogrenci_no}")
                        continue

                    ogrenci_id = ogrenci_result[0]

                    
                    cursor.execute("""
                        SELECT id FROM dersler
                        WHERE bolum_adi=%s AND ders_kodu=%s
                    """, (self.current_bolum, ders_kodu))
                    ders_result = cursor.fetchone()

                    if ders_result:
                        ders_id = ders_result[0]
                        
                        cursor.execute("""
                            INSERT IGNORE INTO ogrenci_ders (ogrenci_id, ders_id)
                            VALUES (%s, %s)
                        """, (ogrenci_id, ders_id))
                        success_count += 1
                    else:
                        error_list.append(
                            f"Satır {index+2} ({ogrenci_no}): '{ders_kodu}' dersi veritabanında bulunamadı"
                        )

                except Error as e:
                    error_msg = f"Satır {index+2}: {str(e)}"
                    error_list.append(error_msg)
                    print(error_msg)
                except Exception as e:
                    error_msg = f"Satır {index+2}: {str(e)}"
                    error_list.append(error_msg)
                    print(error_msg)

            self.db.connection.commit()
            cursor.close()

            message = f"✅ {success_count} öğrenci-ders kaydı yapıldı!"
            if error_list:
                message += f"\n\n⚠️ {len(error_list)} satırda hata oluştu:\n" + "\n".join(error_list[:5])
                if len(error_list) > 5:
                    message += f"\n... ve {len(error_list)-5} hata daha"

            messagebox.showinfo("Sonuç", message)

        except Exception as e:
            messagebox.showerror("Hata", f"Excel okuma hatası: {e}")

    def show_student_list(self):
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        student_window = tk.Toplevel(self.root)
        student_window.title("Öğrenci Listesi")
        student_window.geometry("1000x700")

        
        search_frame = tk.Frame(student_window, bg="#34495e", pady=10)
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(search_frame, text="🔍 Öğrenci Ara:", font=("Arial", 11, "bold"),
                 bg="#34495e", fg="white").pack(side=tk.LEFT, padx=10)
        search_entry = tk.Entry(search_frame, font=("Arial", 11), width=25)
        search_entry.pack(side=tk.LEFT, padx=5)

        
        main_frame = tk.Frame(student_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        left_frame = tk.LabelFrame(main_frame, text="Öğrenci Listesi", 
                                   font=("Arial", 12, "bold"), padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        tree_scroll = tk.Scrollbar(left_frame)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        
        columns = ("Öğrenci No", "Ad Soyad", "Sınıf")
        student_tree = ttk.Treeview(left_frame, columns=columns, show="headings",
                                    yscrollcommand=tree_scroll.set, selectmode='browse')
        tree_scroll.config(command=student_tree.yview)

        student_tree.heading("Öğrenci No", text="Öğrenci No")
        student_tree.heading("Ad Soyad", text="Ad Soyad")
        student_tree.heading("Sınıf", text="Sınıf")

        student_tree.column("Öğrenci No", width=120)
        student_tree.column("Ad Soyad", width=200)
        student_tree.column("Sınıf", width=80)

        student_tree.pack(fill=tk.BOTH, expand=True)

        
        right_frame = tk.LabelFrame(main_frame, text="Seçili Öğrencinin Aldığı Dersler",
                                    font=("Arial", 12, "bold"), padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        
        info_label = tk.Label(right_frame, text="Bir öğrenci seçin...",
                              font=("Arial", 10, "italic"), fg="#7f8c8d")
        info_label.pack(pady=10)

        course_scroll = tk.Scrollbar(right_frame)
        course_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        course_columns = ("Ders Kodu", "Ders Adı")
        course_tree = ttk.Treeview(right_frame, columns=course_columns, show="headings",
                                   yscrollcommand=course_scroll.set)
        course_scroll.config(command=course_tree.yview)

        course_tree.heading("Ders Kodu", text="Ders Kodu")
        course_tree.heading("Ders Adı", text="Ders Adı")

        course_tree.column("Ders Kodu", width=100)
        course_tree.column("Ders Adı", width=250)

        course_tree.pack(fill=tk.BOTH, expand=True)

        
        def load_students(search_query=""):
          
            for item in student_tree.get_children():
                student_tree.delete(item)

            cursor = self.db.connection.cursor()
            
            if search_query.strip():
                
                cursor.execute("""
                    SELECT id, ogrenci_no, ad_soyad, sinif 
                    FROM ogrenciler
                    WHERE bolum_adi=%s AND (ogrenci_no LIKE %s OR ad_soyad LIKE %s)
                    ORDER BY ogrenci_no
                """, (self.current_bolum, f"%{search_query}%", f"%{search_query}%"))
            else:
               
                cursor.execute("""
                    SELECT id, ogrenci_no, ad_soyad, sinif 
                    FROM ogrenciler
                    WHERE bolum_adi=%s
                    ORDER BY ogrenci_no
                """, (self.current_bolum,))

            students = cursor.fetchall()
            cursor.close()

           
            for student in students:
                student_tree.insert("", tk.END, values=(student[1], student[2], student[3]),
                                   tags=(student[0],))  

            
            info_label.config(text=f"Toplam {len(students)} öğrenci bulundu")

       
        def on_student_select(event):
            selection = student_tree.selection()
            if not selection:
                return

            item = student_tree.item(selection[0])
            student_id = item['tags'][0]
            student_no = item['values'][0]
            student_name = item['values'][1]
            student_class = item['values'][2]

           
            info_label.config(
                text=f"📚 {student_name} ({student_no}) - {student_class}. Sınıf",
                font=("Arial", 11, "bold"), fg="#2c3e50"
            )

            
            for item in course_tree.get_children():
                course_tree.delete(item)

            
            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT d.ders_kodu, d.ders_adi
                FROM dersler d
                JOIN ogrenci_ders od ON d.id = od.ders_id
                WHERE od.ogrenci_id=%s
                ORDER BY d.ders_kodu
            """, (student_id,))

            courses = cursor.fetchall()
            cursor.close()

            if courses:
                for course in courses:
                    course_tree.insert("", tk.END, values=course)
            else:
                course_tree.insert("", tk.END, values=("---", "Bu öğrenciye ders atanmamış"))

       
        def search_students_command():
            query = search_entry.get()
            load_students(query)

        tk.Button(search_frame, text="Ara", font=("Arial", 10, "bold"),
                  bg="#3498db", fg="white", command=search_students_command).pack(side=tk.LEFT, padx=5)

        tk.Button(search_frame, text="Tümünü Göster", font=("Arial", 10),
                  bg="#95a5a6", fg="white",
                  command=lambda: [search_entry.delete(0, tk.END), load_students()]).pack(side=tk.LEFT, padx=5)

       
        student_tree.bind('<<TreeviewSelect>>', on_student_select)

        
        search_entry.bind('<Return>', lambda e: search_students_command())

        
        load_students()

        
        stat_frame = tk.Frame(student_window, bg="#ecf0f1", pady=10)
        stat_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)

        cursor = self.db.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM ogrenciler WHERE bolum_adi=%s", (self.current_bolum,))
        total = cursor.fetchone()[0]
        cursor.close()

        tk.Label(stat_frame, text=f"Toplam Kayıtlı Öğrenci: {total}",
                 font=("Arial", 10, "bold"), bg="#ecf0f1", fg="#2c3e50").pack()

    def show_assign_courses_to_student(self):
        """Öğrenciye ders atama ekranı"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        assign_window = tk.Toplevel(self.root)
        assign_window.title("Öğrenciye Ders Ata")
        assign_window.geometry("900x600")

       
        left_frame = tk.LabelFrame(assign_window, text="1. Öğrenci Seç",
                                   font=("Arial", 12, "bold"), padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        tk.Label(left_frame, text="Öğrenci No Ara:", font=("Arial", 10)).pack(pady=5)
        search_entry = tk.Entry(left_frame, font=("Arial", 10), width=20)
        search_entry.pack(pady=5)

        student_listbox = tk.Listbox(left_frame, font=("Arial", 10), height=15)
        student_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        student_dict = {}
        selected_student_id = [None]

        def search_students():
            query = search_entry.get().strip()
            student_listbox.delete(0, tk.END)
            student_dict.clear()

            cursor = self.db.connection.cursor()
            if query:
                cursor.execute("""
                    SELECT id, ogrenci_no, ad_soyad, sinif
                    FROM ogrenciler
                    WHERE bolum_adi=%s AND (ogrenci_no LIKE %s OR ad_soyad LIKE %s)
                """, (self.current_bolum, f"%{query}%", f"%{query}%"))
            else:
                cursor.execute("""
                    SELECT id, ogrenci_no, ad_soyad, sinif
                    FROM ogrenciler WHERE bolum_adi=%s
                """, (self.current_bolum,))

            students = cursor.fetchall()
            cursor.close()

            for s in students:
                display = f"{s[1]} - {s[2]} ({s[3]}. Sınıf)"
                student_listbox.insert(tk.END, display)
                student_dict[display] = s[0]

        tk.Button(left_frame, text="Ara / Tümünü Listele", font=("Arial", 10),
                  bg="#3498db", fg="white", command=search_students).pack(pady=5)

       
        right_frame = tk.LabelFrame(assign_window, text="2. Dersleri Seç (Multiple Selection)",
                                    font=("Arial", 12, "bold"), padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        course_listbox = tk.Listbox(right_frame, font=("Arial", 10), height=15,
                                    selectmode=tk.MULTIPLE)
        course_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        course_dict = {}

        def load_courses():
            course_listbox.delete(0, tk.END)
            course_dict.clear()

            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT id, ders_kodu, ders_adi, sinif
                FROM dersler WHERE bolum_adi=%s
                ORDER BY sinif, ders_kodu
            """, (self.current_bolum,))

            for c in cursor.fetchall():
                display = f"{c[1]} - {c[2]} ({c[3]}. Sınıf)"
                course_listbox.insert(tk.END, display)
                course_dict[display] = c[0]
            cursor.close()

        load_courses()

        
        def assign_courses():
            selection = student_listbox.curselection()
            if not selection:
                messagebox.showerror("Hata", "Bir öğrenci seçin!")
                return

            selected_text = student_listbox.get(selection[0])
            student_id = student_dict[selected_text]

            course_selections = course_listbox.curselection()
            if not course_selections:
                messagebox.showerror("Hata", "En az bir ders seçin!")
                return

            cursor = self.db.connection.cursor()
            success_count = 0

            for idx in course_selections:
                course_text = course_listbox.get(idx)
                course_id = course_dict[course_text]

                try:
                    cursor.execute("""
                        INSERT IGNORE INTO ogrenci_ders (ogrenci_id, ders_id)
                        VALUES (%s, %s)
                    """, (student_id, course_id))
                    success_count += 1
                except:
                    pass

            self.db.connection.commit()
            cursor.close()

            messagebox.showinfo("Başarılı", f"{success_count} ders öğrenciye atandı!")

        tk.Button(assign_window, text="✅ Dersleri Ata", font=("Arial", 12, "bold"),
                  bg="#27ae60", fg="white", height=2, command=assign_courses).pack(pady=10)

        
        search_students()

   

    def show_exam_scheduler(self):
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        scheduler_window = tk.Toplevel(self.root)
        scheduler_window.title("Sınav Programı Oluştur")
        scheduler_window.geometry("900x800")

        
        main_canvas = tk.Canvas(scheduler_window)
        scrollbar = tk.Scrollbar(scheduler_window, orient="vertical", command=main_canvas.yview)
        scrollable_frame = tk.Frame(main_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)

        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tk.Label(scrollable_frame, text="Sınav Programı Kısıtları",
                 font=("Arial", 16, "bold")).pack(pady=10)

       
        ders_frame = tk.LabelFrame(scrollable_frame, text="1. Ders Seçimi", font=("Arial", 12, "bold"), padx=20, pady=10)
        ders_frame.pack(fill=tk.BOTH, padx=20, pady=10)

        tk.Label(ders_frame, text="Sınav programına dahil edilecek dersleri seçin:",
                 font=("Arial", 10)).pack(anchor="w", pady=5)

        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT id, ders_kodu, ders_adi, sinif FROM dersler
            WHERE bolum_adi=%s ORDER BY sinif, ders_kodu
        """, (self.current_bolum,))
        dersler = cursor.fetchall()
        cursor.close()

        ders_checkboxes = {}
        ders_listbox_frame = tk.Frame(ders_frame)
        ders_listbox_frame.pack(fill=tk.BOTH, expand=True)

        ders_scroll = tk.Scrollbar(ders_listbox_frame)
        ders_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        ders_canvas = tk.Canvas(ders_listbox_frame, height=150, yscrollcommand=ders_scroll.set)
        ders_scroll.config(command=ders_canvas.yview)
        ders_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        ders_check_frame = tk.Frame(ders_canvas)
        ders_canvas.create_window((0, 0), window=ders_check_frame, anchor="nw")

        for ders in dersler:
            var = tk.BooleanVar(value=True)
            cb = tk.Checkbutton(ders_check_frame,
                                 text=f"{ders[1]} - {ders[2]} (Sınıf: {ders[3]})",
                                 variable=var, font=("Arial", 9))
            cb.pack(anchor="w", padx=5, pady=2)
            ders_checkboxes[ders[0]] = var

        ders_check_frame.update_idletasks()
        ders_canvas.config(scrollregion=ders_canvas.bbox("all"))

       
        tur_frame = tk.LabelFrame(scrollable_frame, text="2. Sınav Türü", font=("Arial", 12, "bold"), padx=20, pady=10)
        tur_frame.pack(fill=tk.X, padx=20, pady=10)

        sinav_turu_var = tk.StringVar(value="Vize")
        sinav_turu_row = tk.Frame(tur_frame)
        sinav_turu_row.pack(anchor="w")
        for tur in ["Vize", "Final", "Bütünleme"]:
            tk.Radiobutton(sinav_turu_row, text=tur, variable=sinav_turu_var,
                           value=tur, font=("Arial", 10)).pack(side=tk.LEFT, padx=10)

        
        tarih_frame = tk.LabelFrame(scrollable_frame, text="3. Tarih Aralığı", font=("Arial", 12, "bold"), padx=20, pady=10)
        tarih_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(tarih_frame, text="Başlangıç Tarihi (GG.AA.YYYY):",
                 font=("Arial", 10)).pack(anchor="w", pady=2)
        baslangic_entry = tk.Entry(tarih_frame, font=("Arial", 10), width=30)
        baslangic_entry.pack(anchor="w", pady=2)

        tk.Label(tarih_frame, text="Bitiş Tarihi (GG.AA.YYYY):",
                 font=("Arial", 10)).pack(anchor="w", pady=2)
        bitis_entry = tk.Entry(tarih_frame, font=("Arial", 10), width=30)
        bitis_entry.pack(anchor="w", pady=2)

       
        gun_frame = tk.LabelFrame(scrollable_frame, text="4. Sınav Yapılmayacak Günler", font=("Arial", 12, "bold"), padx=20, pady=10)
        gun_frame.pack(fill=tk.X, padx=20, pady=10)

        gun_row = tk.Frame(gun_frame)
        gun_row.pack(anchor="w")

        gun_vars = {}
        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        for gun in gunler:
            var = tk.BooleanVar(value=(gun in ["Cumartesi", "Pazar"]))
            tk.Checkbutton(gun_row, text=gun, variable=var,
                           font=("Arial", 9)).pack(side=tk.LEFT, padx=5)
            gun_vars[gun] = var

        
        sure_frame = tk.LabelFrame(scrollable_frame, text="5. Sınav Süreleri", font=("Arial", 12, "bold"), padx=20, pady=10)
        sure_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(sure_frame, text="Varsayılan Sınav Süresi (dakika):",
                 font=("Arial", 10)).pack(anchor="w", pady=2)
        sure_entry = tk.Entry(sure_frame, font=("Arial", 10), width=30)
        sure_entry.insert(0, "75")
        sure_entry.pack(anchor="w", pady=2)

        
        tk.Label(sure_frame, text="İstisnai Sınav Süreleri:",
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(10,2))

        istisnai_frame = tk.Frame(sure_frame)
        istisnai_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        istisnai_list = tk.Listbox(istisnai_frame, height=4, font=("Arial", 9))
        istisnai_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        istisnai_scroll = tk.Scrollbar(istisnai_frame, command=istisnai_list.yview)
        istisnai_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        istisnai_list.config(yscrollcommand=istisnai_scroll.set)

        istisnai_sureler = {}

        def add_istisnai_sure():
            istisna_window = tk.Toplevel(scheduler_window)
            istisna_window.title("İstisnai Süre Ekle")
            istisna_window.geometry("400x200")

            tk.Label(istisna_window, text="Ders:", font=("Arial", 10)).pack(pady=5)
            ders_var = tk.StringVar()
            ders_combo = ttk.Combobox(istisna_window, textvariable=ders_var, width=40)
            ders_combo['values'] = [f"{d[1]} - {d[2]}" for d in dersler]
            ders_combo.pack(pady=5)

            tk.Label(istisna_window, text="Sınav Süresi (dakika):", font=("Arial", 10)).pack(pady=5)
            sure_istisna_entry = tk.Entry(istisna_window, font=("Arial", 10), width=20)
            sure_istisna_entry.pack(pady=5)

            def kaydet_istisna():
                ders_sec = ders_var.get()
                sure_val = sure_istisna_entry.get()

                if not ders_sec or not sure_val:
                    messagebox.showerror("Hata", "Tüm alanları doldurun!")
                    return

                try:
                    sure_int = int(sure_val)
                    if sure_int <= 0:
                        messagebox.showerror("Hata", "Süre pozitif olmalı!")
                        return

                    ders_id = None
                    for d in dersler:
                        if f"{d[1]} - {d[2]}" == ders_sec:
                            ders_id = d[0]
                            break

                    if ders_id:
                        istisnai_sureler[ders_id] = sure_int
                        istisnai_list.insert(tk.END, f"{ders_sec} -> {sure_int} dk")
                        istisna_window.destroy()
                except ValueError:
                    messagebox.showerror("Hata", "Süre sayı olmalı!")

            tk.Button(istisna_window, text="Kaydet", bg="#27ae60", fg="white",
                      command=kaydet_istisna).pack(pady=10)

        def delete_istisnai_sure():
            selection = istisnai_list.curselection()
            if selection:
                istisnai_list.delete(selection[0])

        btn_frame = tk.Frame(sure_frame)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="İstisna Ekle", font=("Arial", 9),
                  bg="#3498db", fg="white", command=add_istisnai_sure).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Seçiliyi Sil", font=("Arial", 9),
                  bg="#e74c3c", fg="white", command=delete_istisnai_sure).pack(side=tk.LEFT, padx=5)

        
        bekleme_frame = tk.LabelFrame(scrollable_frame, text="6. Bekleme Süresi", font=("Arial", 12, "bold"), padx=20, pady=10)
        bekleme_frame.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(bekleme_frame, text="Sınavlar Arası Bekleme Süresi (dakika):",
                 font=("Arial", 10)).pack(anchor="w", pady=2)
        bekleme_entry = tk.Entry(bekleme_frame, font=("Arial", 10), width=30)
        bekleme_entry.insert(0, "15")
        bekleme_entry.pack(anchor="w", pady=2)

        
        ayni_zaman_frame = tk.LabelFrame(scrollable_frame, text="7. Çakışma Kuralı", font=("Arial", 12, "bold"), padx=20, pady=10)
        ayni_zaman_frame.pack(fill=tk.X, padx=20, pady=10)

        ayni_zaman_var = tk.BooleanVar(value=False)
        tk.Checkbutton(ayni_zaman_frame, text="Hiçbir sınav aynı zamana denk gelmesin (Bir sınav bitene kadar başka sınav başlamasın)",
                       variable=ayni_zaman_var, font=("Arial", 10)).pack(anchor="w", pady=5)

        
        def create_schedule():
            try:
                
                secili_dersler = [ders_id for ders_id, var in ders_checkboxes.items() if var.get()]

                if not secili_dersler:
                    messagebox.showerror("Hata", "En az bir ders seçmelisiniz!")
                    return

                baslangic_str = baslangic_entry.get()
                bitis_str = bitis_entry.get()
                baslangic = datetime.strptime(baslangic_str, "%d.%m.%Y")
                bitis = datetime.strptime(bitis_str, "%d.%m.%Y")

                if baslangic >= bitis:
                    messagebox.showerror("Hata", "Bitiş tarihi başlangıçtan sonra olmalı!")
                    return

                sinav_suresi_default = int(sure_entry.get())
                bekleme_suresi = int(bekleme_entry.get())
                sinav_turu = sinav_turu_var.get()
                ayni_zaman = ayni_zaman_var.get()

                
                calisilan_gunler = [i for i, gun in enumerate(gunler) if not gun_vars[gun].get()]

                
                tarihler = []
                current = baslangic
                while current <= bitis:
                    if current.weekday() in calisilan_gunler:
                        tarihler.append(current)
                    current += timedelta(days=1)

                if not tarihler:
                    messagebox.showerror("Hata", "Seçilen tarih aralığında uygun gün yok!")
                    return

                
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    SELECT id, derslik_adi, kapasite FROM derslikler
                    WHERE bolum_adi=%s ORDER BY kapasite DESC
                """, (self.current_bolum,))
                derslikler = cursor.fetchall()

                if not derslikler:
                    messagebox.showerror("Hata", "Sistemde derslik bulunamadı!")
                    cursor.close()
                    return

               
                cursor.execute("DELETE FROM istisnai_sinav_sureleri WHERE bolum_adi=%s", (self.current_bolum,))
                for ders_id, sure in istisnai_sureler.items():
                    cursor.execute("""
                        INSERT INTO istisnai_sinav_sureleri (bolum_adi, ders_id, sinav_suresi)
                        VALUES (%s, %s, %s)
                    """, (self.current_bolum, ders_id, sure))

                
                cursor.execute("DELETE FROM sinav_programi WHERE bolum_adi=%s", (self.current_bolum,))
                self.db.connection.commit()

                
                result = self.optimized_exam_scheduler(
                    secili_dersler, tarihler, derslikler,
                    sinav_suresi_default, istisnai_sureler,
                    bekleme_suresi, sinav_turu, ayni_zaman, cursor
                )

                cursor.close()

                if result['success']:
                    self.db.connection.commit()
                    messagebox.showinfo("Başarılı", result['message'])
                    self.export_schedule_to_excel()
                else:
                    self.db.connection.rollback()
                    messagebox.showerror("Hata", result['message'])

            except ValueError as e:
                messagebox.showerror("Hata", f"Tarih formatı hatalı! GG.AA.YYYY formatında girin.\n{e}")
            except Exception as e:
                messagebox.showerror("Hata", f"Program oluştururken hata: {e}")
                import traceback
                traceback.print_exc()

        tk.Button(scrollable_frame, text="Programı Oluştur", font=("Arial", 14, "bold"),
                  bg="#27ae60", fg="white", command=create_schedule, height=2).pack(pady=20)


    def optimized_exam_scheduler(self, secili_dersler, tarihler, derslikler,
                                 sinav_suresi_default, istisnai_sureler,
                                 bekleme_suresi, sinav_turu, ayni_zaman, cursor):

        
        cursor.execute(f"""
            SELECT id, ders_kodu, ders_adi, sinif
            FROM dersler
            WHERE id IN ({','.join(['%s']*len(secili_dersler))})
            ORDER BY sinif, ders_kodu
        """, secili_dersler)
        tum_dersler = cursor.fetchall()

        
        ders_ogrenci_sayilari = {}
        for ders in tum_dersler:
            cursor.execute("""
                SELECT COUNT(*) FROM ogrenci_ders WHERE ders_id=%s
            """, (ders[0],))
            ders_ogrenci_sayilari[ders[0]] = cursor.fetchone()[0]

        
        cursor.execute("""
            SELECT od.ogrenci_id, od.ders_id
            FROM ogrenci_ders od
            JOIN dersler d ON od.ders_id = d.id
            WHERE d.bolum_adi=%s AND d.id IN ({})
        """.format(','.join(['%s']*len(secili_dersler))),
        [self.current_bolum] + secili_dersler)

        ogrenci_dersler = defaultdict(set)
        for og_id, ders_id in cursor.fetchall():
            ogrenci_dersler[og_id].add(ders_id)

        
        sinif_dersleri = defaultdict(list)
        for ders in tum_dersler:
            sinif_dersleri[ders[3]].append(ders)  

     
        sinif_gun_planlari = {}

        for sinif, dersler in sinif_dersleri.items():
            ders_sayisi = len(dersler)
            gun_sayisi = len(tarihler)
            
            if gun_sayisi == 0:
                continue
            
           
            gun_basi_ders = ders_sayisi // gun_sayisi  
            kalan_ders = ders_sayisi % gun_sayisi      
            
           
            gun_ders_sayilari = []
            for gun_idx in range(gun_sayisi):
                if gun_idx < kalan_ders:
                   
                    gun_ders_sayilari.append(gun_basi_ders + 1)
                else:
                    gun_ders_sayilari.append(gun_basi_ders)
            
           
            gun_plani = []
            ders_index = 0
            
            for gun_idx in range(gun_sayisi):
                ders_adedi = gun_ders_sayilari[gun_idx]
                
                if ders_adedi > 0 and ders_index < ders_sayisi:
                    gun_dersleri = dersler[ders_index:ders_index + ders_adedi]
                    gun_plani.append((tarihler[gun_idx], gun_dersleri))
                    ders_index += ders_adedi
            
            sinif_gun_planlari[sinif] = gun_plani

     
        derslik_takvimi = defaultdict(lambda: defaultdict(list))
       
        global_sinav_takvimi = defaultdict(list)
        
        ogrenci_sinav_takvimi = defaultdict(list)

        sinav_programi = []
        hata_mesajlari = []

       
        for sinif, gun_plani in sinif_gun_planlari.items():
            for tarih, gun_dersleri in gun_plani:
                
                
                gun_dersleri_sorted = sorted(gun_dersleri,
                                             key=lambda d: ders_ogrenci_sayilari[d[0]],
                                             reverse=True)
                
                for ders in gun_dersleri_sorted:
                    ders_id = ders[0]
                    ders_kodu = ders[1]
                    ders_adi = ders[2]
                    ogrenci_sayisi = ders_ogrenci_sayilari[ders_id]
                    sinav_suresi = istisnai_sureler.get(ders_id, sinav_suresi_default)
                    
                    yerlestirildi = False
                    
                    
                    current_time = datetime.combine(tarih, datetime.min.time().replace(hour=9, minute=0))
                    gun_bitis = datetime.combine(tarih, datetime.min.time().replace(hour=18, minute=0))
                    
                    while current_time < gun_bitis and not yerlestirildi:
                        sinav_baslangic = current_time
                        sinav_bitis = sinav_baslangic + timedelta(minutes=sinav_suresi)
                        mola_bitis = sinav_bitis + timedelta(minutes=bekleme_suresi)

                        
                        cakisma_var = False
                        if ayni_zaman:
                            for (baslangic_global, global_mola_bitis) in global_sinav_takvimi[tarih]:
                                
                                if sinav_baslangic < global_mola_bitis:
                                    cakisma_var = True
                                    break
                            
                            if cakisma_var:
                                current_time += timedelta(minutes=15)
                                continue

                        
                        musait_derslikler = []
                        
                        for derslik in derslikler:
                            derslik_id = derslik[0]
                            derslik_musait = True
                            
                            
                            for (onceki_baslangic, onceki_bitis, onceki_mola_bitis, _) in derslik_takvimi[tarih][derslik_id]:
                                if sinav_baslangic < onceki_mola_bitis:
                                    derslik_musait = False
                                    break
                            
                            if derslik_musait:
                                musait_derslikler.append(derslik)
                        
                        
                        gerekli_derslikler = []
                        kalan_ogrenci = ogrenci_sayisi
                        
                        
                        musait_derslikler_sorted = sorted(musait_derslikler,
                                                         key=lambda d: len(derslik_takvimi[tarih][d[0]]),
                                                         reverse=True)
                        
                        for derslik in musait_derslikler_sorted:
                            if kalan_ogrenci <= 0:
                                break
                            gerekli_derslikler.append(derslik)
                            kalan_ogrenci -= derslik[2]
                        
                        if kalan_ogrenci > 0:
                            current_time += timedelta(minutes=15)
                            continue

                        

                        bekleme_ihlali = False
                        
                        
                        for og_id, ders_set in ogrenci_dersler.items():
                            if ders_id in ders_set:
                                
                                
                                for (onceki_sinav_bitis, onceki_ders_id) in ogrenci_sinav_takvimi[og_id]:
                                    if onceki_sinav_bitis.date() == tarih.date():
                                        
                                        
                                        sure_farki = (sinav_baslangic - onceki_sinav_bitis).total_seconds() / 60
                                        if sure_farki < bekleme_suresi:
                                            bekleme_ihlali = True
                                            break
                                        
                                if bekleme_ihlali:
                                    break

                       
                        if not bekleme_ihlali:
                         
                            cakisan_dersler = []
                            gerekli_derslik_ids = {d[0] for d in gerekli_derslikler}
                            for derslik in derslikler:
                                derslik_id = derslik[0]
                                if derslik_id in gerekli_derslik_ids: continue
                                for (baslangic_diger, bitis_diger, mola_bitis_diger, diger_ders_id) in derslik_takvimi[tarih][derslik_id]:
                                    
                                    if not (sinav_bitis <= baslangic_diger or sinav_baslangic >= bitis_diger):
                                        cakisan_dersler.append(diger_ders_id)
                            
                            if cakisan_dersler:
                                for og_id, ders_set in ogrenci_dersler.items():
                                    if ders_id in ders_set and ders_set.intersection(set(cakisan_dersler)):
                                        bekleme_ihlali = True
                                        break


                        if bekleme_ihlali:
                            current_time += timedelta(minutes=15)
                            continue
                        
                       
                        
                       
                        if ayni_zaman:
                            global_sinav_takvimi[tarih].append((sinav_baslangic, mola_bitis))
                        
                        
                        for og_id in ogrenci_dersler:
                            if ders_id in ogrenci_dersler[og_id]:
                                
                                ogrenci_sinav_takvimi[og_id].append((sinav_bitis, ders_id))

                       
                        for derslik in gerekli_derslikler:
                            derslik_id = derslik[0]
                            
                            derslik_takvimi[tarih][derslik_id].append(
                                (sinav_baslangic, sinav_bitis, mola_bitis, ders_id)
                            )
                            
                            sinav_programi.append({
                                'ders_id': ders_id,
                                'tarih': tarih,
                                'saat': sinav_baslangic.time().strftime('%H:%M:%S'),
                                'derslik_id': derslik_id
                            })
                            
                            cursor.execute("""
                                INSERT INTO sinav_programi
                                (bolum_adi, ders_id, sinav_tarihi, sinav_saati, sinav_turu, sinav_suresi, derslik_id, atanan_ogrenci)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (self.current_bolum, ders_id, tarih,
                                  sinav_baslangic.time().strftime('%H:%M:%S'),
                                  sinav_turu, sinav_suresi, derslik_id, derslik[2]))
                            
                        yerlestirildi = True
                        break 

                    if not yerlestirildi:
                        hata_mesajlari.append(
                            f"❌ {ders[1]} - {ders[2]} ({ders[3]}. sınıf) {tarih.strftime('%d.%m.%Y')} gününe yerleştirilemedi! (Kapasite/Zaman Dolu)"
                        )

        
        if hata_mesajlari:
            return {
                'success': len(sinav_programi) > 0,
                'message': f"{len(sinav_programi)} sınav oluşturuldu.\n\n⚠️ HATALAR:\n" + "\n".join(hata_mesajlari[:5])
            }
        else:
            return {
                'success': True,
                'message': f"✅ Başarılı!\n{len(sinav_programi)} sınav kaydı oluşturuldu."
            }

    def export_schedule_to_excel(self):
        if not self.current_bolum:
            return

        cursor = self.db.connection.cursor()

       
        cursor.execute("""
            SELECT
                sp.sinav_tarihi,
                sp.sinav_saati,
                d.ders_adi,
                d.hoca_adi,      -- Öğretim Elemanı
                dr.derslik_adi,  -- Derslik Adı
                sp.sinav_turu,
                sp.sinav_suresi,
                sp.ders_id
            FROM sinav_programi sp
            JOIN dersler d ON sp.ders_id = d.id
            JOIN derslikler dr ON sp.derslik_id = dr.id
            WHERE sp.bolum_adi=%s
            ORDER BY sp.sinav_tarihi, sp.sinav_saati, d.ders_adi
        """, (self.current_bolum,))

        results = cursor.fetchall()

        if not results:
            messagebox.showinfo("Bilgi", "Henüz sınav programı oluşturulmamış!")
            cursor.close()
            return

        
        ders_id_to_ogrenci_sayilari = {}
        ders_ids = list(set(r[7] for r in results))

        
        if ders_ids:
            cursor.execute(f"""
                SELECT ders_id, COUNT(*)
                FROM ogrenci_ders
                WHERE ders_id IN ({','.join(['%s']*len(ders_ids))})
                GROUP BY ders_id
            """, ders_ids)
            for ders_id, count in cursor.fetchall():
                ders_id_to_ogrenci_sayilari[ders_id] = count

        grouped_schedule = defaultdict(lambda: {
            'Derslikler': [],
            'Öğretim Elemanı': '',
            'Sınav Türü': '',
            'Sınav Süresi': 0,
            'Öğrenci Sayısı': 0
        })

        for tarih, saat, ders_adi, hoca_adi, derslik_adi, sinav_turu, sinav_suresi, ders_id in results:

            key = (tarih, saat, ders_adi)

          
            grouped_schedule[key]['Derslikler'].append(derslik_adi)

           
            grouped_schedule[key]['Öğretim Elemanı'] = hoca_adi
            grouped_schedule[key]['Sınav Türü'] = sinav_turu
            grouped_schedule[key]['Sınav Süresi'] = sinav_suresi

            
            grouped_schedule[key]['Öğrenci Sayısı'] = ders_id_to_ogrenci_sayilari.get(ders_id, 0)

        

        final_list = []

        for (tarih, saat, ders_adi), data in grouped_schedule.items():
            final_list.append({
                'Tarih': tarih.strftime('%d.%m.%Y'),
                'Sınav Saati': str(saat),
                'Ders Adı': ders_adi,
                'Öğretim Elemanı': data['Öğretim Elemanı'],
                'Derslik': '-'.join(sorted(set(data['Derslikler']))), 
                'Öğrenci Sayısı': data['Öğrenci Sayısı'],
                'Sınav Türü': data['Sınav Türü'],
                'Süre (dk)': data['Sınav Süresi']
            })

        df = pd.DataFrame(final_list)

        
        df_output = df[['Tarih', 'Sınav Saati', 'Ders Adı', 'Öğretim Elemanı', 'Derslik', 'Öğrenci Sayısı', 'Sınav Türü', 'Süre (dk)']]

        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile=f"sinav_programi_{self.current_bolum}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )

        if file_path:
            df_output.to_excel(file_path, index=False)
            messagebox.showinfo("Başarılı", "Sınav programı Excel'e aktarıldı!")

    def show_seating_plan(self):
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        seating_window = tk.Toplevel(self.root)
        seating_window.title("Oturma Planı")
        seating_window.geometry("900x600")

        tk.Label(seating_window, text="Sınavlar",
                 font=("Arial", 14, "bold")).pack(pady=10)

        list_frame = tk.Frame(seating_window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        exam_listbox = tk.Listbox(list_frame, font=("Arial", 11), yscrollcommand=scrollbar.set)
        scrollbar.config(command=exam_listbox.yview)
        exam_listbox.pack(fill=tk.BOTH, expand=True)

        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT
                sp.id,
                d.ders_kodu,
                d.ders_adi,
                sp.sinav_tarihi,
                sp.sinav_saati,
                dr.derslik_adi
            FROM sinav_programi sp
            JOIN dersler d ON sp.ders_id = d.id
            JOIN derslikler dr ON sp.derslik_id = dr.id
            WHERE sp.bolum_adi=%s
            ORDER BY sp.sinav_tarihi, sp.sinav_saati
        """, (self.current_bolum,))

        sinavlar = cursor.fetchall()
        cursor.close()

        if not sinavlar:
            messagebox.showinfo("Bilgi", "Henüz sınav programı oluşturulmamış!")
            seating_window.destroy()
            return

        sinav_dict = {}
        for sinav in sinavlar:
            display_text = f"{sinav[1]} - {sinav[2]} | {sinav[3]} {sinav[4]} | {sinav[5]}"
            exam_listbox.insert(tk.END, display_text)
            sinav_dict[display_text] = sinav[0]

        button_frame = tk.Frame(seating_window)
        button_frame.pack(pady=10)

        def create_seating():
            selection = exam_listbox.curselection()
            if not selection:
                messagebox.showerror("Hata", "Bir sınav seçin!")
                return

            selected_text = exam_listbox.get(selection[0])
            sinav_id = sinav_dict[selected_text]

            self.generate_seating_plan(sinav_id)

        def view_seating():
            selection = exam_listbox.curselection()
            if not selection:
                messagebox.showerror("Hata", "Bir sınav seçin!")
                return

            selected_text = exam_listbox.get(selection[0])
            sinav_id = sinav_dict[selected_text]

            self.view_seating_plan(sinav_id)

        tk.Button(button_frame, text="Oturma Planı Oluştur", font=("Arial", 11),
                  bg="#27ae60", fg="white", command=create_seating).pack(side=tk.LEFT, padx=10)

        tk.Button(button_frame, text="Oturma Planını Görüntüle", font=("Arial", 11),
                  bg="#3498db", fg="white", command=view_seating).pack(side=tk.LEFT, padx=10)

    def generate_seating_plan(self, sinav_id):
        """
        Oturma planı oluşturma (Sanal Koltuk Mantığı ile)
        3'lü yapıda: Her kutuya 2 kişi (1. ve 3. koltuklar dolu, 2. boş)
        """

        cursor = self.db.connection.cursor()

        
        cursor.execute("""
            SELECT sp.ders_id, sp.sinav_tarihi, sp.sinav_saati
            FROM sinav_programi sp
            WHERE sp.id=%s
        """, (sinav_id,))

        sinav_info = cursor.fetchone()
        if not sinav_info:
            messagebox.showerror("Hata", "Sınav bulunamadı!")
            cursor.close()
            return

        ders_id = sinav_info[0]
        sinav_tarihi = sinav_info[1]
        sinav_saati = sinav_info[2]

        
        cursor.execute("""
            SELECT sp.id, sp.derslik_id, dr.kapasite, dr.enine_sira, dr.boyuna_sira, dr.sira_yapisi, dr.derslik_adi
            FROM sinav_programi sp
            JOIN derslikler dr ON sp.derslik_id = dr.id
            WHERE sp.ders_id=%s AND sp.sinav_tarihi=%s AND sp.sinav_saati=%s
            ORDER BY dr.kapasite DESC
        """, (ders_id, sinav_tarihi, sinav_saati))

        tum_derslikler = cursor.fetchall()

        if not tum_derslikler:
            messagebox.showerror("Hata", "Derslik bilgisi bulunamadı!")
            cursor.close()
            return

        
        cursor.execute("""
            SELECT o.id, o.ogrenci_no, o.ad_soyad
            FROM ogrenciler o
            JOIN ogrenci_ders od ON o.id = od.ogrenci_id
            WHERE od.ders_id=%s
            ORDER BY RAND()
        """, (ders_id,))

        ogrenciler = cursor.fetchall()

        toplam_kapasite = sum(d[2] for d in tum_derslikler)

        if len(ogrenciler) > toplam_kapasite:
            messagebox.showerror(
                "Hata",
                f"❌ Öğrenci sayısı ({len(ogrenciler)}) toplam derslik kapasitesini ({toplam_kapasite}) aşıyor!"
            )
            cursor.close()
            return

        
        for derslik_data in tum_derslikler:
            cursor.execute("DELETE FROM oturma_plani WHERE sinav_id=%s", (derslik_data[0],))

       
        ogrenci_index = 0
        yerlestirildi = 0

        for derslik_data in tum_derslikler:
            sinav_programi_id = derslik_data[0]
            derslik_id = derslik_data[1]
            kapasite = derslik_data[2]
            enine = derslik_data[3]
            boyuna = derslik_data[4]
            sira_yapi = derslik_data[5] 

          
            students_to_seat_in_derslik = min(kapasite, len(ogrenciler) - ogrenci_index)

            seated_count_in_derslik = 0

            
            for sira in range(1, boyuna + 1):
                for kutu_sutun in range(1, enine + 1): 

                    
                    for koltuk_no in range(1, sira_yapi + 1):

                       
                        is_skipped = False
                        if sira_yapi == 3 and koltuk_no == 2: 
                            is_skipped = True
                        elif sira_yapi == 2 and koltuk_no == 2: 
                            is_skipped = True

                        if is_skipped:
                            continue

                        
                        if ogrenci_index >= len(ogrenciler) or seated_count_in_derslik >= students_to_seat_in_derslik:
                            break

                        ogrenci = ogrenciler[ogrenci_index]

                        sutun_kaydi = kutu_sutun * 10 + koltuk_no

                        
                        cursor.execute("""
                            INSERT INTO oturma_plani (sinav_id, ogrenci_id, derslik_id, sira_no, sutun_no)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (sinav_programi_id, ogrenci[0], derslik_id, sira, sutun_kaydi))

                        seated_count_in_derslik += 1
                        ogrenci_index += 1
                        yerlestirildi += 1

                    if ogrenci_index >= len(ogrenciler) or seated_count_in_derslik >= students_to_seat_in_derslik:
                        break

                if ogrenci_index >= len(ogrenciler):
                    break

        self.db.connection.commit()
        cursor.close()

        derslik_sayisi = len(tum_derslikler)
        derslik_isimleri = ', '.join(d[6] for d in tum_derslikler)

        messagebox.showinfo(
            "Başarılı",
            f"✅ Oturma planı oluşturuldu!\n\n"
            f"Toplam {yerlestirildi} öğrenci {derslik_sayisi} dersliğe yerleştirildi."
        )

    def view_seating_plan(self, sinav_id):
        cursor = self.db.connection.cursor()

        
        cursor.execute("""
            SELECT
                d.ders_kodu,
                d.ders_adi,
                sp.sinav_tarihi,
                sp.sinav_saati,
                sp.ders_id
            FROM sinav_programi sp
            JOIN dersler d ON sp.ders_id = d.id
            WHERE sp.id=%s
        """, (sinav_id,))

        sinav_info = cursor.fetchone()
        if not sinav_info:
            messagebox.showerror("Hata", "Sınav bulunamadı!")
            cursor.close()
            return

        ders_kodu = sinav_info[0]
        ders_adi = sinav_info[1]
        sinav_tarihi = sinav_info[2]
        sinav_saati = sinav_info[3]
        ders_id = sinav_info[4]

        
        cursor.execute("""
            SELECT
                dr.id,
                dr.derslik_adi,
                dr.enine_sira,
                dr.boyuna_sira,
                dr.sira_yapisi,
                sp.id as sinav_programi_id
            FROM sinav_programi sp
            JOIN derslikler dr ON sp.derslik_id = dr.id
            WHERE sp.ders_id=%s
            AND sp.sinav_tarihi=%s
            AND sp.sinav_saati=%s
            ORDER BY dr.kapasite DESC
        """, (ders_id, sinav_tarihi, sinav_saati))

        tum_derslikler = cursor.fetchall()

        if not tum_derslikler:
            messagebox.showwarning("Uyarı", "Bu sınav için derslik bulunamadı!")
            cursor.close()
            return

        #
        view_window = tk.Toplevel(self.root)
        view_window.title(f"Oturma Planı - {ders_adi}")
        view_window.geometry("1200x800")

        info_text = f"""
    Ders: {ders_kodu} - {ders_adi}
    Tarih: {sinav_tarihi} | Saat: {sinav_saati}
    Kullanılan Derslik Sayısı: {len(tum_derslikler)}
        """

        info_label = tk.Label(view_window, text=info_text, font=("Arial", 12, "bold"),
                              justify=tk.LEFT, bg="#3498db", fg="white", padx=10, pady=10)
        info_label.pack(fill=tk.X)

        
        notebook = ttk.Notebook(view_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tum_oturma_verileri = {}

        for derslik_data in tum_derslikler:
            derslik_id = derslik_data[0]
            derslik_adi = derslik_data[1]
            enine = derslik_data[2]
            boyuna = derslik_data[3]
            sira_yapi = derslik_data[4]
            sinav_programi_id = derslik_data[5]

           
            cursor.execute("""
                SELECT
                    op.sira_no,
                    op.sutun_no,
                    o.ogrenci_no,
                    o.ad_soyad
                FROM oturma_plani op
                JOIN ogrenciler o ON op.ogrenci_id = o.id
                WHERE op.sinav_id=%s
                ORDER BY op.sira_no, op.sutun_no
            """, (sinav_programi_id,))

            oturma_verileri = cursor.fetchall()

           
            oturma_dict = defaultdict(list)
            for sira, sanal_sutun, ogr_no, ad_soyad in oturma_verileri:
                kutu_sutun = sanal_sutun // 10
                koltuk_no = sanal_sutun % 10
                oturma_dict[(sira, kutu_sutun)].append((koltuk_no, ogr_no, ad_soyad))

           
            tab_frame = tk.Frame(notebook)
            notebook.add(tab_frame, text=f"{derslik_adi} ({len(oturma_verileri)} kayıt)")

           
            derslik_info = tk.Label(tab_frame,
                                     text=f"Derslik: {derslik_adi} | Düzen: {boyuna}x{enine} ({sira_yapi}'lü sıra)",
                                     font=("Arial", 10, "bold"), bg="#ecf0f1", pady=5)
            derslik_info.pack(fill=tk.X)

          
            canvas_container = tk.Frame(tab_frame)
            canvas_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

          
            v_scrollbar = tk.Scrollbar(canvas_container, orient=tk.VERTICAL)
            h_scrollbar = tk.Scrollbar(canvas_container, orient=tk.HORIZONTAL)

            canvas_widget = tk.Canvas(canvas_container, bg="white",
                                     yscrollcommand=v_scrollbar.set,
                                     xscrollcommand=h_scrollbar.set)

            v_scrollbar.config(command=canvas_widget.yview)
            h_scrollbar.config(command=canvas_widget.xview)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            canvas_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

           
            cell_width = 80  
            cell_height = 80  
            gap_between_cells = 8
            gap_between_boxes = 20
            start_x = 50
            start_y = 50

           
            total_box_width = sira_yapi * cell_width + (sira_yapi - 1) * gap_between_cells
            tahta_width = enine * (total_box_width + gap_between_boxes) - gap_between_boxes
            canvas_widget.create_rectangle(start_x, 10, start_x + tahta_width, 35,
                                           fill="#2c3e50", outline="black")
            canvas_widget.create_text(start_x + tahta_width/2, 22,
                                     text="TAHTA", font=("Arial", 14, "bold"), fill="white")

           
            for sira in range(boyuna):
                for kutu_sutun in range(enine):

                    anahtar_koordinat = (sira + 1, kutu_sutun + 1)

                   
                    for koltuk_idx in range(sira_yapi):

                        
                        x1 = start_x + kutu_sutun * (total_box_width + gap_between_boxes) + koltuk_idx * (cell_width + gap_between_cells)
                        y1 = start_y + sira * (cell_height + gap_between_boxes)
                        x2 = x1 + cell_width
                        y2 = y1 + cell_height

                        koltuk_no = koltuk_idx + 1

                       
                        is_empty_seat = False
                        if sira_yapi == 3 and koltuk_no == 2:
                            is_empty_seat = True
                        elif sira_yapi == 2 and koltuk_no == 2:
                            is_empty_seat = True

                       
                        student_data = None
                        if anahtar_koordinat in oturma_dict:
                            for k_no, ogr_no, ad_soyad in oturma_dict[anahtar_koordinat]:
                                if k_no == koltuk_no:
                                    student_data = (ogr_no, ad_soyad)
                                    break

                       
                        if is_empty_seat:
                            
                            color = "#ecf0f1"
                            canvas_widget.create_rectangle(x1, y1, x2, y2, fill=color, outline="#bdc3c7", width=1)
                            canvas_widget.create_text((x1+x2)/2, (y1+y2)/2,
                                                     text="BOŞ", font=("Arial", 9), fill="#95a5a6")
                        elif student_data:
                            
                            color = "#27ae60"
                            canvas_widget.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", width=2)

                            ogr_no, ad_soyad = student_data
                            
                           
                            isim_parcalari = ad_soyad.split()
                            if len(isim_parcalari) >= 2:
                                isim = isim_parcalari[0]
                                soyisim = ' '.join(isim_parcalari[1:])
                            else:
                                isim = ad_soyad
                                soyisim = ""
                            
                            
                            canvas_widget.create_text((x1+x2)/2, y1 + 20,
                                                     text=isim[:12],
                                                     font=("Arial", 9, "bold"), fill="white")
                            
                            
                            if soyisim:
                                canvas_widget.create_text((x1+x2)/2, y1 + 38,
                                                         text=soyisim[:12],
                                                         font=("Arial", 8), fill="white")
                            
                            
                            canvas_widget.create_text((x1+x2)/2, y1 + 60,
                                                     text=ogr_no,
                                                     font=("Arial", 7), fill="white")
                        else:
                            
                            color = "#95a5a6"
                            canvas_widget.create_rectangle(x1, y1, x2, y2, fill=color, outline="black", width=1)
                            canvas_widget.create_text((x1+x2)/2, (y1+y2)/2,
                                                     text="---", font=("Arial", 10), fill="white")

                       
                        canvas_widget.create_text(x1 + 8, y1 + 8,
                                                 text=f"S{sira+1}-{kutu_sutun+1}.{koltuk_no}",
                                                 font=("Arial", 7), fill="black", anchor="nw")

            canvas_widget.config(scrollregion=canvas_widget.bbox("all"))

           
            tum_oturma_verileri[derslik_adi] = {
                'oturma': oturma_dict,
                'enine': enine,
                'boyuna': boyuna,
                'sira_yapi': sira_yapi
            }

        cursor.close()

      
        btn_frame = tk.Frame(view_window)
        btn_frame.pack(pady=10)

        def export_to_pdf():
            self.export_seating_to_pdf_multi(
                sinav_id, ders_kodu, ders_adi, sinav_tarihi,
                sinav_saati, tum_oturma_verileri
            )

        tk.Button(btn_frame, text="📄 PDF Olarak İndir (Tüm Derslikler)",
                  font=("Arial", 11), bg="#e74c3c", fg="white",
                  command=export_to_pdf).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="📋 Liste Görünümü", font=("Arial", 11),
                  bg="#3498db", fg="white",
                  command=lambda: self.show_seating_list(sinav_id)).pack(side=tk.LEFT, padx=5)

    def show_seating_list(self, sinav_id):
        """Oturma planını liste halinde göster"""
        list_window = tk.Toplevel(self.root)
        list_window.title("Oturma Planı - Liste Görünümü")
        list_window.geometry("700x600")

        cursor = self.db.connection.cursor()

        
        cursor.execute("""
            SELECT d.ders_kodu, d.ders_adi, dr.derslik_adi
            FROM sinav_programi sp
            JOIN dersler d ON sp.ders_id = d.id
            JOIN derslikler dr ON sp.derslik_id = dr.id
            WHERE sp.id=%s
        """, (sinav_id,))

        sinav_info = cursor.fetchone()

        tk.Label(list_window,
                 text=f"{sinav_info[0]} - {sinav_info[1]}\nDerslik: {sinav_info[2]}",
                 font=("Arial", 12, "bold")).pack(pady=10)

       
        tree_frame = tk.Frame(list_window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("Sıra No", "Sütun No", "Öğrenci No", "Ad Soyad")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                            yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)

      
        cursor.execute("""
            SELECT op.sira_no, op.sutun_no, o.ogrenci_no, o.ad_soyad
            FROM oturma_plani op
            JOIN ogrenciler o ON op.ogrenci_id = o.id
            WHERE op.sinav_id=%s
            ORDER BY op.sira_no, op.sutun_no
        """, (sinav_id,))

        for row in cursor.fetchall():
            tree.insert("", tk.END, values=row)

        cursor.close()
        tree.pack(fill=tk.BOTH, expand=True)

        
        def export_to_excel():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialfile=f"oturma_plani_{sinav_info[0]}.xlsx"
            )

            if file_path:
                cursor = self.db.connection.cursor()
                cursor.execute("""
                    SELECT op.sira_no, op.sutun_no, o.ogrenci_no, o.ad_soyad
                    FROM oturma_plani op
                    JOIN ogrenciler o ON op.ogrenci_id = o.id
                    WHERE op.sinav_id=%s
                    ORDER BY op.sira_no, op.sutun_no
                """, (sinav_id,))

                df = pd.DataFrame(cursor.fetchall(),
                                  columns=["Sıra No", "Sütun No", "Öğrenci No", "Ad Soyad"])
                df.to_excel(file_path, index=False)
                cursor.close()
                messagebox.showinfo("Başarılı", "Excel dosyası oluşturuldu!")

        tk.Button(list_window, text="Excel Olarak İndir", font=("Arial", 11),
                  bg="#27ae60", fg="white", command=export_to_excel).pack(pady=10)

   

    def export_seating_to_pdf_multi(self, sinav_id, ders_kodu, ders_adi,
                                     sinav_tarihi, sinav_saati, tum_oturma_verileri):
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"oturma_plani_{ders_kodu}_{datetime.now().strftime('%Y%m%d')}.pdf"
        )

        if not file_path:
            return

        try:
            c = pdf_canvas.Canvas(file_path, pagesize=landscape(A4))
            width, height = landscape(A4)

           
            for derslik_adi, derslik_data in tum_oturma_verileri.items():
                oturma_dict = derslik_data['oturma']
                enine = derslik_data['enine']
                boyuna = derslik_data['boyuna']
                sira_yapi = derslik_data['sira_yapi']

              
                c.setFont("Helvetica-Bold", 16)
                c.drawString(2*cm, height - 2*cm, f"Oturma Plani: {ders_adi}")

                c.setFont("Helvetica", 12)
                c.drawString(2*cm, height - 2.7*cm, f"Ders Kodu: {ders_kodu}")
                c.drawString(2*cm, height - 3.2*cm, f"Derslik: {derslik_adi}")
                c.drawString(2*cm, height - 3.7*cm, f"Tarih: {sinav_tarihi} | Saat: {sinav_saati}")
                c.drawString(2*cm, height - 4.2*cm, f"Duzen: {boyuna}x{enine} ({sira_yapi}'lu sira)")

              
                start_x = 2*cm
                start_y = height - 6*cm
                
               
                koltuk_width = 1.6*cm   
                koltuk_height = 1.4*cm  
                koltuk_gap = 0.2*cm  
                kutu_gap = 0.25*cm      
                sira_gap = 0.25*cm      

                
                c.setFillColorRGB(0.17, 0.24, 0.31)
                
                total_kutu_width = sira_yapi * koltuk_width + (sira_yapi - 1) * koltuk_gap
                tahta_width = enine * total_kutu_width + (enine - 1) * kutu_gap
                c.rect(start_x, start_y, tahta_width, 0.8*cm, fill=1)
                c.setFillColorRGB(1, 1, 1)
                c.setFont("Arial-Bold", 10)
                c.drawString(start_x + tahta_width/2 - 1*cm, start_y + 0.3*cm, "TAHTA")

                
                current_y = start_y - sira_gap
                
                for sira in range(boyuna):
                    current_x = start_x
                    
                    for kutu_sutun in range(enine):
                       
                        kutu_key = (sira + 1, kutu_sutun + 1)
                        students_in_kutu = oturma_dict.get(kutu_key, [])
                        
                       
                        for koltuk_idx in range(sira_yapi):
                            koltuk_no = koltuk_idx + 1
                            
                            
                            x_pos = current_x + koltuk_idx * (koltuk_width + koltuk_gap)
                            y_pos = current_y - koltuk_height
                            
                            
                            is_empty_seat = False
                            if sira_yapi == 3 and koltuk_no == 2:
                                is_empty_seat = True
                            elif sira_yapi == 2 and koltuk_no == 2:
                                is_empty_seat = True
                            
                            
                            student_data = None
                            for k_no, ogr_no, ad_soyad in students_in_kutu:
                                if k_no == koltuk_no:
                                    student_data = (ogr_no, ad_soyad)
                                    break
                            
                            
                            if is_empty_seat:
                               
                                c.setFillColorRGB(0.93, 0.94, 0.95)
                                c.setStrokeColorRGB(0.74, 0.76, 0.78)
                                c.rect(x_pos, y_pos, koltuk_width, koltuk_height, fill=1, stroke=1)
                                
                                c.setFillColorRGB(0.5, 0.55, 0.6)
                                c.setFont("Arial", 6)
                                c.drawString(x_pos + koltuk_width/2 - 0.2*cm, 
                                           y_pos + koltuk_height/2 - 0.1*cm, "BOŞ")
                                
                            elif student_data:
                                
                                c.setFillColorRGB(0.15, 0.68, 0.38)
                                c.setStrokeColorRGB(0, 0, 0)
                                c.rect(x_pos, y_pos, koltuk_width, koltuk_height, fill=1, stroke=1)
                                
                                ogr_no, ad_soyad = student_data
                                
                                
                                isim_parcalari = ad_soyad.split()
                                if len(isim_parcalari) >= 2:
                                    isim = isim_parcalari[0]
                                    soyisim = ' '.join(isim_parcalari[1:])
                                else:
                                    isim = ad_soyad
                                    soyisim = ""
                                
                                c.setFillColorRGB(1, 1, 1)
                                
                                
                                c.setFillColorRGB(0.2, 0.29, 0.37)
                                c.setFont("Arial", 5)
                                c.drawString(x_pos + 0.05*cm, 
                                           y_pos + koltuk_height - 0.15*cm, 
                                           f"S{sira+1}-{kutu_sutun+1}.{koltuk_no}")
                                
                                c.setFillColorRGB(1, 1, 1)
                                
                                
                                c.setFont("Arial-Bold", 8)
                                c.drawString(x_pos + 0.1*cm, 
                                           y_pos + koltuk_height - 0.45*cm, 
                                           isim[:15])
                                
                                
                                if soyisim:
                                    c.setFont("Arial", 7)
                                    c.drawString(x_pos + 0.1*cm, 
                                               y_pos + koltuk_height - 0.75*cm, 
                                               soyisim[:15])
                                
                               
                                c.setFont("Arial", 6)
                                c.drawString(x_pos + 0.1*cm, 
                                           y_pos + 0.25*cm, 
                                           str(ogr_no)[:11])
                            else:
                                
                                c.setFillColorRGB(0.58, 0.64, 0.66)
                                c.setStrokeColorRGB(0, 0, 0)
                                c.rect(x_pos, y_pos, koltuk_width, koltuk_height, fill=1, stroke=1)
                                
                                c.setFillColorRGB(1, 1, 1)
                                c.setFont("Arial", 6)
                                c.drawString(x_pos + koltuk_width/2 - 0.15*cm, 
                                           y_pos + koltuk_height/2 - 0.05*cm, "---")
                                
                                
                                c.setFillColorRGB(0.2, 0.29, 0.37)
                                c.setFont("Arial", 5)
                                c.drawString(x_pos + 0.05*cm, 
                                           y_pos + koltuk_height - 0.15*cm, 
                                           f"S{sira+1}-{kutu_sutun+1}.{koltuk_no}")
                        
                        
                        current_x += total_kutu_width + kutu_gap
                    
                    
                    current_y -= (koltuk_height + sira_gap)

                
                table_start_y = current_y - 1.5*cm

                if table_start_y > 3*cm:
                    c.setFont("Arial-Bold", 10)
                    c.setFillColorRGB(0, 0, 0)
                    c.drawString(start_x, table_start_y + 0.5*cm, "Ogrenci Listesi:")

                    
                    col_widths = [2*cm, 2*cm, 3*cm, 5*cm]
                    headers = ["Sira", "Koltuk No", "Ogrenci No", "Ad Soyad"]

                    c.setFont("Arial-Bold", 9)
                    x_pos = start_x
                    for i, header in enumerate(headers):
                        c.drawString(x_pos, table_start_y, header)
                        x_pos += col_widths[i]

                    
                    c.line(start_x, table_start_y - 0.1*cm,
                           start_x + sum(col_widths), table_start_y - 0.1*cm)

                   
                    c.setFont("Arial", 8)
                    y_pos = table_start_y - 0.5*cm

                   
                    pdf_list_data = []
                    for (sira_anahtar, kutu_sutun), students in oturma_dict.items():
                        for koltuk_no, ogr_no, ad_soyad in students:
                            pdf_list_data.append((sira_anahtar, koltuk_no, ogr_no, ad_soyad))

                    pdf_list_data.sort(key=lambda x: (x[0], x[1]))

                    for sira_anahtar, koltuk_no, ogr_no, ad_soyad in pdf_list_data:
                        if y_pos < 2*cm:
                            c.showPage()
                            y_pos = height - 3*cm
                            c.setFont("Arial", 8)

                        x_pos = start_x
                        values = [str(sira_anahtar), str(koltuk_no), str(ogr_no), ad_soyad[:25]]

                        for i, val in enumerate(values):
                            c.drawString(x_pos, y_pos, val)
                            x_pos += col_widths[i]

                        y_pos -= 0.5*cm

                
                c.showPage()

            c.save()
            messagebox.showinfo("Başarılı", 
                f"PDF dosyası oluşturuldu!\n\n{len(tum_oturma_verileri)} derslik için oturma planı eklendi.")

        except Exception as e:
            messagebox.showerror("Hata", f"PDF oluşturulurken hata:\n{str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    root = tk.Tk()
    app = SinavTakvimiApp(root)
    root.mainloop()