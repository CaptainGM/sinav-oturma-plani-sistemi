"""Giriş ekranı, kullanıcı ekleme ve bölüm seçimi."""
import tkinter as tk
from tkinter import ttk, messagebox
from mysql.connector import Error

from ..styles import COLORS, hash_password, verify_password, _is_bcrypt_hash


class AuthMixin:
    def show_login_screen(self):
        self.clear_screen()

        login_frame = tk.Frame(self.root, bg=COLORS['bg_panel'])
        login_frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(login_frame, image=self.login_icon_img, bg=COLORS['bg_panel']).pack(pady=(45, 15))

        tk.Label(login_frame, text="Sınav Takvimi Yönetim Sistemi",
                 font=("Segoe UI", 22, "bold"), bg=COLORS['bg_panel'], fg=COLORS['text_light']).pack(pady=(0, 5))
        tk.Label(login_frame, text="Devam etmek için giriş yapın",
                 font=("Segoe UI", 10), bg=COLORS['bg_panel'], fg=COLORS['text_muted']).pack(pady=(0, 25))

        form_frame = tk.Frame(login_frame, bg=COLORS['bg_dark'], padx=45, pady=35)
        form_frame.pack(pady=10)

        tk.Label(form_frame, text="E-posta", font=("Segoe UI", 10), bg=COLORS['bg_dark'],
                 fg=COLORS['text_light']).grid(row=0, column=0, sticky="w", pady=(0, 4))
        email_entry = ttk.Entry(form_frame, font=("Segoe UI", 12), width=28)
        email_entry.grid(row=1, column=0, pady=(0, 16))
        email_entry.focus_set()

        tk.Label(form_frame, text="Şifre", font=("Segoe UI", 10), bg=COLORS['bg_dark'],
                 fg=COLORS['text_light']).grid(row=2, column=0, sticky="w", pady=(0, 4))

        password_frame = tk.Frame(form_frame, bg=COLORS['bg_dark'])
        password_frame.grid(row=3, column=0, pady=(0, 8))

        password_entry = ttk.Entry(password_frame, font=("Segoe UI", 12), width=23, show="*")
        password_entry.pack(side=tk.LEFT)

        def toggle_password_visibility():
            if password_entry.cget("show") == "*":
                password_entry.config(show="")
                toggle_btn.config(text="🙈")
            else:
                password_entry.config(show="*")
                toggle_btn.config(text="👁")

        toggle_btn = tk.Button(password_frame, text="👁", font=("Segoe UI", 10), width=3,
                               relief="flat", bg=COLORS['bg_dark'], fg=COLORS['text_light'],
                               activebackground=COLORS['bg_panel'], activeforeground=COLORS['text_light'],
                               command=toggle_password_visibility)
        toggle_btn.pack(side=tk.LEFT, padx=(4, 0))

        def login(event=None):
            email = email_entry.get()
            password = password_entry.get()

            if not email or not password:
                messagebox.showerror("Hata", "Tüm alanları doldurun!")
                return

            cursor = self.db.connection.cursor()
            cursor.execute("""
                SELECT id, email, rol, bolum, sifre FROM kullanicilar
                WHERE email=%s
            """, (email,))
            user = cursor.fetchone()

            if user and verify_password(password, user[4]):
                if not _is_bcrypt_hash(user[4]):
                    # Eski (salt'sız SHA256) hash ile başarılı giriş yapıldı,
                    # şifreyi sessizce bcrypt'e yükselt.
                    cursor.execute("UPDATE kullanicilar SET sifre=%s WHERE id=%s",
                                    (hash_password(password), user[0]))
                    self.db.connection.commit()
                cursor.close()

                self.current_user = user[1]
                self.current_role = user[2]
                self.current_bolum = user[3]
                self.log_activity("Giriş yapıldı")
                self.show_main_menu()
            else:
                cursor.close()
                messagebox.showerror("Hata", "Geçersiz kullanıcı adı veya şifre!")

        password_entry.bind("<Return>", login)
        email_entry.bind("<Return>", login)

        login_btn = ttk.Button(form_frame, text="Giriş Yap", style="Accent.TButton", command=login)
        login_btn.grid(row=4, column=0, pady=(22, 0), sticky="ew")


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

            hashed_pass = hash_password(password)
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
        dept_window.geometry("420x320")

        tk.Label(dept_window, text="Yönetmek istediğiniz bölümü seçin:",
                 font=("Arial", 12)).pack(pady=(20, 10))

        bolum_var = tk.StringVar()
        bolum_combo = ttk.Combobox(dept_window, textvariable=bolum_var,
                                   state="readonly", width=30)
        bolum_combo.pack(pady=10)

        def reload_bolumler(select=None):
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT bolum_adi FROM bolumler ORDER BY bolum_adi")
            bolumler = [row[0] for row in cursor.fetchall()]
            cursor.close()
            bolum_combo['values'] = bolumler
            if select and select in bolumler:
                bolum_var.set(select)
            elif bolumler and not bolum_var.get():
                bolum_var.set(bolumler[0])

        reload_bolumler()

        def select_dept():
            if bolum_var.get():
                self.current_bolum = bolum_var.get()
                dept_window.destroy()
                self.show_main_menu()

        tk.Button(dept_window, text="Seç", font=("Arial", 11),
                  bg="#3498db", fg="white", command=select_dept).pack(pady=10)

        ttk.Separator(dept_window, orient="horizontal").pack(fill=tk.X, padx=20, pady=15)

        tk.Label(dept_window, text="Not: 'Bölüm' bir mühendislik bölümü, bir okul sınıfı ya "
                 "da istediğiniz herhangi bir grup olabilir — sadece bir isimdir.",
                 font=("Arial", 8), fg="#7f8c8d", wraplength=380, justify=tk.LEFT).pack(padx=20)

        add_frame = tk.Frame(dept_window)
        add_frame.pack(pady=10, fill=tk.X, padx=20)

        yeni_bolum_entry = tk.Entry(add_frame, font=("Arial", 10), width=22)
        yeni_bolum_entry.pack(side=tk.LEFT, padx=(0, 5))

        def add_bolum():
            ad = yeni_bolum_entry.get().strip()
            if not ad:
                messagebox.showerror("Hata", "Bölüm adı girin!")
                return
            try:
                cursor = self.db.connection.cursor()
                cursor.execute("INSERT INTO bolumler (bolum_adi) VALUES (%s)", (ad,))
                self.db.connection.commit()
                cursor.close()
                yeni_bolum_entry.delete(0, tk.END)
                reload_bolumler(select=ad)
                self.log_activity("Bölüm eklendi", ad)
            except Error as e:
                if "Duplicate entry" in str(e):
                    messagebox.showerror("Hata", "Bu isimde bir bölüm zaten var!")
                else:
                    messagebox.showerror("Hata", f"Bölüm eklenemedi: {e}")

        tk.Button(add_frame, text="Bölüm Ekle", font=("Arial", 10),
                  bg="#27ae60", fg="white", command=add_bolum).pack(side=tk.LEFT, padx=5)

        def delete_bolum():
            ad = bolum_var.get()
            if not ad:
                messagebox.showerror("Hata", "Silinecek bölümü seçin!")
                return

            cursor = self.db.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM derslikler WHERE bolum_adi=%s", (ad,))
            derslik_sayisi = cursor.fetchone()[0]
            cursor.close()

            uyari = f"'{ad}' bölümü silinsin mi?"
            if derslik_sayisi > 0:
                uyari += (f"\n\n⚠️ Bu bölüme ait {derslik_sayisi} derslik kaydı var. "
                          f"Bölüm silinse bile bu kayıtlar veritabanında kalır, "
                          f"sadece bölüm listesinden kaybolur.")

            if messagebox.askyesno("Onay", uyari):
                cursor = self.db.connection.cursor()
                cursor.execute("DELETE FROM bolumler WHERE bolum_adi=%s", (ad,))
                self.db.connection.commit()
                cursor.close()
                bolum_var.set("")
                reload_bolumler()
                self.log_activity("Bölüm silindi", ad)

        tk.Button(dept_window, text="Seçili Bölümü Sil", font=("Arial", 10),
                  bg="#e74c3c", fg="white", command=delete_bolum).pack(pady=5)

