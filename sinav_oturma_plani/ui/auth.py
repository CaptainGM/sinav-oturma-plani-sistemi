"""Giriş, kayıt ve bölüm seçimi ekranları."""
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from PIL import ImageTk
from pymongo.errors import DuplicateKeyError, PyMongoError

from ..styles import (CARD_PADDING, COLORS, hash_password, hex_to_rgb, is_bcrypt_hash,
                       rounded_card, verify_password)
from .background import ResponsiveBackground

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthMixin:
    def _build_auth_screen(self, subtitle):
        """Giriş/kayıt ekranlarının ortak iskeleti: pencereyle birlikte
        ölçeklenen arka plan ve ortalanmış form kutusu. Form alanlarının
        eklendiği Frame'i döndürür."""
        self.clear_screen()

        canvas = tk.Canvas(self.root, highlightthickness=0, bd=0, bg=COLORS['bg_dark'])
        canvas.pack(fill=tk.BOTH, expand=True)

        ResponsiveBackground(canvas, self.login_bg_source)

        icon_item = canvas.create_image(0, 0, image=self.login_icon_img, anchor="n")
        title_item = canvas.create_text(0, 0, text="Sınav Takvimi Yönetim Sistemi",
                                         font=("Segoe UI", 22, "bold"),
                                         fill=COLORS['text_light'], anchor="n")
        subtitle_item = canvas.create_text(0, 0, text=subtitle, font=("Segoe UI", 10),
                                            fill=COLORS['text_muted'], anchor="n")

        # Kart görseli formdan önce oluşturuluyor ki formun altında kalsın.
        card_item = canvas.create_image(0, 0, anchor="n")
        form_frame = tk.Frame(canvas, bg=COLORS['bg_dark'], padx=45, pady=35)
        form_item = canvas.create_window(0, 0, window=form_frame, anchor="n")

        card_size = {'value': None}

        def layout(_event=None):
            # Ekran değişiminde canvas, gecikmeli çağrı gelmeden yok edilebilir.
            if not canvas.winfo_exists():
                return

            w, h = canvas.winfo_width(), canvas.winfo_height()
            if w < 2 or h < 2:
                return

            cx = w // 2
            block_height = 245 + form_frame.winfo_reqheight()
            top = max(20, (h - block_height) // 2)

            form_w, form_h = form_frame.winfo_reqwidth(), form_frame.winfo_reqheight()
            if card_size['value'] != (form_w, form_h):
                card_size['value'] = (form_w, form_h)
                self._auth_card_img = ImageTk.PhotoImage(
                    rounded_card(form_w, form_h, hex_to_rgb(COLORS['bg_dark']) + (255,)))
                canvas.itemconfig(card_item, image=self._auth_card_img)

            canvas.coords(icon_item, cx, top)
            canvas.coords(title_item, cx, top + 165)
            canvas.coords(subtitle_item, cx, top + 200)
            canvas.coords(card_item, cx, top + 235 - CARD_PADDING)
            canvas.coords(form_item, cx, top + 235)

        canvas.bind("<Configure>", layout, add="+")
        # Form alanları bu fonksiyon döndükten sonra ekleniyor; yüksekliği
        # kesinleştiğinde yeniden ortalayabilmek için formu da dinliyoruz.
        form_frame.bind("<Configure>", layout, add="+")
        self.root.after(0, layout)
        return form_frame

    def _form_label(self, parent, text, row):
        tk.Label(parent, text=text, font=("Segoe UI", 10), bg=COLORS['bg_dark'],
                 fg=COLORS['text_light']).grid(row=row, column=0, sticky="w", pady=(0, 4))

    def _link_row(self, parent, row, question, action_text, command):
        container = tk.Frame(parent, bg=COLORS['bg_dark'])
        container.grid(row=row, column=0, pady=(14, 0))
        tk.Label(container, text=question, font=("Segoe UI", 9), bg=COLORS['bg_dark'],
                 fg=COLORS['text_muted']).pack(side=tk.LEFT)
        tk.Button(container, text=action_text, font=("Segoe UI", 9, "bold"), relief="flat",
                  bd=0, bg=COLORS['bg_dark'], fg=COLORS['primary'],
                  activebackground=COLORS['bg_dark'], activeforeground=COLORS['primary'],
                  cursor="hand2", command=command).pack(side=tk.LEFT, padx=(4, 0))

    def show_login_screen(self):
        form = self._build_auth_screen("Devam etmek için giriş yapın")

        self._form_label(form, "E-posta", 0)
        email_entry = ttk.Entry(form, font=("Segoe UI", 12), width=28)
        email_entry.grid(row=1, column=0, pady=(0, 16))
        email_entry.focus_set()

        self._form_label(form, "Şifre", 2)
        password_frame = tk.Frame(form, bg=COLORS['bg_dark'])
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
                               activebackground=COLORS['bg_panel'],
                               activeforeground=COLORS['text_light'],
                               command=toggle_password_visibility)
        toggle_btn.pack(side=tk.LEFT, padx=(4, 0))

        def login(event=None):
            email = email_entry.get().strip()
            password = password_entry.get()

            if not email or not password:
                messagebox.showerror("Hata", "Tüm alanları doldurun!")
                return

            user = self.db.kullanicilar.find_one({'email': email})

            if user and verify_password(password, user['sifre']):
                if not is_bcrypt_hash(user['sifre']):
                    self.db.kullanicilar.update_one(
                        {'_id': user['_id']}, {'$set': {'sifre': hash_password(password)}})

                self.current_user = user['email']
                self.current_role = user['rol']
                self.current_bolum = user['bolum']
                self.log_activity("Giriş yapıldı")
                self.show_main_menu()
            else:
                messagebox.showerror("Hata", "Geçersiz kullanıcı adı veya şifre!")

        email_entry.bind("<Return>", login)
        password_entry.bind("<Return>", login)

        ttk.Button(form, text="Giriş Yap", style="Accent.TButton", command=login).grid(
            row=4, column=0, pady=(22, 0), sticky="ew")

        self._link_row(form, 5, "Hesabınız yok mu?", "Kayıt Ol", self.show_register_screen)

    def show_register_screen(self):
        form = self._build_auth_screen("Yeni bir koordinatör hesabı oluşturun")

        self._form_label(form, "E-posta", 0)
        email_entry = ttk.Entry(form, font=("Segoe UI", 12), width=28)
        email_entry.grid(row=1, column=0, pady=(0, 12))
        email_entry.focus_set()

        self._form_label(form, "Şifre (en az 6 karakter)", 2)
        password_entry = ttk.Entry(form, font=("Segoe UI", 12), width=28, show="*")
        password_entry.grid(row=3, column=0, pady=(0, 12))

        self._form_label(form, "Şifre (Tekrar)", 4)
        password2_entry = ttk.Entry(form, font=("Segoe UI", 12), width=28, show="*")
        password2_entry.grid(row=5, column=0, pady=(0, 12))

        self._form_label(form, "Bölüm", 6)
        bolum_row = tk.Frame(form, bg=COLORS['bg_dark'])
        bolum_row.grid(row=7, column=0, pady=(0, 10), sticky="w")

        bolumler = [b['bolum_adi'] for b in self.db.bolumler.find().sort('bolum_adi', 1)]
        bolum_var = tk.StringVar(value=bolumler[0] if bolumler else "")
        bolum_combo = ttk.Combobox(bolum_row, textvariable=bolum_var, values=bolumler,
                                    state="readonly", width=22)
        bolum_combo.pack(side=tk.LEFT)

        def add_bolum():
            ad = simpledialog.askstring("Bölüm Ekle", "Yeni bölüm adı:", parent=self.root)
            if not ad or not ad.strip():
                return
            ad = ad.strip()
            try:
                self.db.bolumler.insert_one({'bolum_adi': ad})
            except DuplicateKeyError:
                pass
            except PyMongoError as e:
                messagebox.showerror("Hata", f"Bölüm eklenemedi: {e}")
                return
            bolum_combo['values'] = [b['bolum_adi'] for b in
                                      self.db.bolumler.find().sort('bolum_adi', 1)]
            bolum_var.set(ad)

        tk.Button(bolum_row, text="+", font=("Segoe UI", 11, "bold"), width=3, relief="flat",
                  bd=0, bg=COLORS['primary'], fg="white", activebackground=COLORS['primary'],
                  activeforeground="white", cursor="hand2",
                  command=add_bolum).pack(side=tk.LEFT, padx=(6, 0))

        tk.Label(form, text="Listede bölümünüz yoksa + ile ekleyebilirsiniz.\n"
                            "Yeni hesaplar 'Bölüm Koordinatörü' olarak açılır.",
                 font=("Segoe UI", 8), bg=COLORS['bg_dark'], fg=COLORS['text_muted'],
                 justify=tk.LEFT).grid(row=8, column=0, sticky="w")

        def register(event=None):
            email = email_entry.get().strip()
            password = password_entry.get()
            password_repeat = password2_entry.get()
            bolum = bolum_var.get()

            if not email or not password:
                messagebox.showerror("Hata", "E-posta ve şifre gerekli!")
                return
            if not EMAIL_PATTERN.match(email):
                messagebox.showerror("Hata", "Geçerli bir e-posta adresi girin!")
                return
            if len(password) < 6:
                messagebox.showerror("Hata", "Şifre en az 6 karakter olmalı!")
                return
            if password != password_repeat:
                messagebox.showerror("Hata", "Şifreler eşleşmiyor!")
                return
            if not bolum:
                messagebox.showerror("Hata", "Bir bölüm seçin veya + ile yeni bir tane ekleyin!")
                return

            try:
                self.db.kullanicilar.insert_one({
                    'email': email,
                    'sifre': hash_password(password),
                    'rol': "Bölüm Koordinatörü",
                    'bolum': bolum,
                })
            except DuplicateKeyError:
                messagebox.showerror("Hata", "Bu e-posta adresi zaten kayıtlı!")
                return
            except PyMongoError as e:
                messagebox.showerror("Hata", f"Kayıt oluşturulamadı: {e}")
                return

            messagebox.showinfo("Başarılı", "Hesabınız oluşturuldu, giriş yapabilirsiniz.")
            self.show_login_screen()

        password2_entry.bind("<Return>", register)

        ttk.Button(form, text="Hesap Oluştur", style="Accent.TButton", command=register).grid(
            row=9, column=0, pady=(18, 0), sticky="ew")

        self._link_row(form, 10, "Zaten hesabınız var mı?", "Giriş Yap", self.show_login_screen)

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

        bolumler = [b['bolum_adi'] for b in self.db.bolumler.find()]

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
            try:
                self.db.kullanicilar.insert_one({
                    'email': email, 'sifre': hashed_pass, 'rol': rol, 'bolum': bolum,
                })
                messagebox.showinfo("Başarılı", "Kullanıcı eklendi!")
                add_user_window.destroy()
            except DuplicateKeyError:
                messagebox.showerror("Hata", "Bu e-posta adresi zaten kullanılıyor!")
            except PyMongoError as e:
                messagebox.showerror("Hata", f"Kullanıcı eklenemedi: {e}")

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
            bolumler = [b['bolum_adi'] for b in self.db.bolumler.find().sort('bolum_adi', 1)]
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
                self.db.bolumler.insert_one({'bolum_adi': ad})
                yeni_bolum_entry.delete(0, tk.END)
                reload_bolumler(select=ad)
                self.log_activity("Bölüm eklendi", ad)
            except DuplicateKeyError:
                messagebox.showerror("Hata", "Bu isimde bir bölüm zaten var!")
            except PyMongoError as e:
                messagebox.showerror("Hata", f"Bölüm eklenemedi: {e}")

        tk.Button(add_frame, text="Bölüm Ekle", font=("Arial", 10),
                  bg="#27ae60", fg="white", command=add_bolum).pack(side=tk.LEFT, padx=5)

        def delete_bolum():
            ad = bolum_var.get()
            if not ad:
                messagebox.showerror("Hata", "Silinecek bölümü seçin!")
                return

            derslik_sayisi = self.db.derslikler.count_documents({'bolum_adi': ad})

            uyari = f"'{ad}' bölümü silinsin mi?"
            if derslik_sayisi > 0:
                uyari += (f"\n\n⚠️ Bu bölüme ait {derslik_sayisi} derslik kaydı var. "
                          f"Bölüm silinse bile bu kayıtlar veritabanında kalır, "
                          f"sadece bölüm listesinden kaybolur.")

            if messagebox.askyesno("Onay", uyari):
                self.db.bolumler.delete_one({'bolum_adi': ad})
                bolum_var.set("")
                reload_bolumler()
                self.log_activity("Bölüm silindi", ad)

        tk.Button(dept_window, text="Seçili Bölümü Sil", font=("Arial", 10),
                  bg="#e74c3c", fg="white", command=delete_bolum).pack(pady=5)
