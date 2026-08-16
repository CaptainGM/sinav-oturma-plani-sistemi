"""Ana menü, üst başlık çubuğu ve bölüm bazlı özet istatistik kartları."""
import tkinter as tk
from datetime import datetime
from tkinter import ttk

from ..styles import COLORS
from .background import ResponsiveBackground


class DashboardMixin:
    def show_main_menu(self):
        self.clear_screen()
        self._build_menubar()
        self._build_header()

        body, refresh_layout = self._build_scrollable_body()

        if self.current_role == "Admin" and not self.current_bolum:
            self._build_department_prompt(body)
        elif self.current_bolum and not self.check_derslik_requirement():
            self._build_classroom_prompt(body)
        elif self.current_bolum:
            self._build_dashboard_cards(body)
            self._build_quick_actions(body)
            self._build_upcoming_exams(body)

        self._build_decoration(body)
        self.root.after(0, refresh_layout)

    def _build_menubar(self):
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
            admin_menu.add_command(label="Aktivite Kaydı", command=self.show_activity_log)

        if self.current_role == "Bölüm Koordinatörü" or (self.current_role == "Admin" and self.current_bolum):
            koordinator_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Derslik İşlemleri", menu=koordinator_menu)
            koordinator_menu.add_command(label="Derslik Ekle", command=self.show_add_classroom)
            koordinator_menu.add_command(label="Derslik Düzenle", command=self.show_edit_classroom)
            koordinator_menu.add_command(label="Derslik Listele/Ara", command=self.show_classroom_list)

            # Ders/öğrenci/sınav işlemleri en az bir derslik girilmeden anlamsız.
            if self.check_derslik_requirement():
                ders_menu = tk.Menu(menubar, tearoff=0)
                menubar.add_cascade(label="Ders İşlemleri", menu=ders_menu)
                ders_menu.add_command(label="Ders Ekle", command=self.show_add_course)
                ders_menu.add_command(label="Ders Düzenle", command=self.show_edit_course)
                ders_menu.add_command(label="Ders Listesi Yükle (Excel)", command=self.upload_course_excel)
                ders_menu.add_command(label="Excel Şablonu İndir", command=self.download_course_template)
                ders_menu.add_command(label="Ders Listesi Görüntüle", command=self.show_course_list)

                ogrenci_menu = tk.Menu(menubar, tearoff=0)
                menubar.add_cascade(label="Öğrenci İşlemleri", menu=ogrenci_menu)
                ogrenci_menu.add_command(label="Öğrenci Ekle", command=self.show_add_student)
                ogrenci_menu.add_command(label="Öğrenci Düzenle", command=self.show_edit_student)
                ogrenci_menu.add_command(label="Öğrenci Listesi Yükle (Excel)", command=self.upload_student_excel)
                ogrenci_menu.add_command(label="Excel Şablonu İndir", command=self.download_student_template)
                ogrenci_menu.add_command(label="Öğrenci Listesi Görüntüle", command=self.show_student_list)
                ogrenci_menu.add_separator()
                ogrenci_menu.add_command(label="Öğrenciye Ders Ata", command=self.show_assign_courses_to_student)

                ogretim_menu = tk.Menu(menubar, tearoff=0)
                menubar.add_cascade(label="Öğretim Görevlisi İşlemleri", menu=ogretim_menu)
                ogretim_menu.add_command(label="Öğretim Görevlisi Ekle", command=self.show_add_instructor)
                ogretim_menu.add_command(label="Öğretim Görevlisi Düzenle", command=self.show_edit_instructor)
                ogretim_menu.add_command(label="Öğretim Görevlisi Listele", command=self.show_instructor_list)

                sinav_menu = tk.Menu(menubar, tearoff=0)
                menubar.add_cascade(label="Sınav Programı", menu=sinav_menu)
                sinav_menu.add_command(label="Sınav Programı Oluştur", command=self.show_exam_scheduler)
                sinav_menu.add_command(label="Oturma Planı", command=self.show_seating_plan)
                sinav_menu.add_command(label="Gözetmen Ata", command=self.show_assign_proctor)
                sinav_menu.add_command(label="Çakışma Raporu", command=self.show_exam_conflicts)
                sinav_menu.add_command(label="Sınav Takvimi (Genel Görünüm)", command=self.show_exam_calendar)

    def _build_scrollable_body(self):
        """Panel gövdesi. İçerik pencereye sığmadığında kaydırma çubuğu belirir;
        sığdığında dekor katmanı kalan boşluğu doldurur.

        `(icerik_cercevesi, yerlesimi_tazeleyen_fonksiyon)` döndürür."""
        outer = tk.Frame(self.root, bg=COLORS['bg_light'])
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0, bd=0, bg=COLORS['bg_light'])
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        inner = tk.Frame(canvas, bg=COLORS['bg_light'])
        inner_item = canvas.create_window(0, 0, window=inner, anchor="nw")

        def refresh(_event=None):
            if not canvas.winfo_exists():
                return

            width, height = canvas.winfo_width(), canvas.winfo_height()
            if width < 2:
                return
            canvas.itemconfig(inner_item, width=width)

            deco = getattr(self, '_panel_decoration', None)
            if deco is not None and deco.winfo_exists():
                # Dekor dışındaki içeriğin kapladığı yer kadarını çıkarıp
                # kalan boşluğu dekora veriyoruz.
                kullanilan = inner.winfo_reqheight() - int(deco.cget('height'))
                deco.configure(height=max(90, height - kullanilan))

            gereken = inner.winfo_reqheight()
            if gereken > height:
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                canvas.configure(scrollregion=(0, 0, width, gereken))
            else:
                scrollbar.pack_forget()
                canvas.yview_moveto(0)
                canvas.configure(scrollregion=(0, 0, width, height))

        canvas.bind("<Configure>", refresh, add="+")
        inner.bind("<Configure>", refresh, add="+")

        def on_wheel(event):
            if inner.winfo_reqheight() > canvas.winfo_height():
                canvas.yview_scroll(-int(event.delta / 120), "units")

        # bind_all yalnızca imleç panelin üzerindeyken bağlanır; aksi halde
        # açık olan diğer pencerelerin tekerlek olaylarını da yakalardı.
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", on_wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        return inner, refresh

    def _build_decoration(self, parent):
        """İçeriğin altında kalan boşluğu dekoratif arka planla doldurur.

        Ayrı bir katman olarak en sona yerleştirilir; böylece içerik ne kadar
        yer kaplarsa kaplasın dekor tam onun bittiği yerden başlar ve araya
        görünür bir sınır girmez."""
        canvas = tk.Canvas(parent, highlightthickness=0, bd=0, bg=COLORS['bg_light'],
                            height=90)
        canvas.pack(fill=tk.X)
        ResponsiveBackground(canvas, self.panel_bg_source)
        self._panel_decoration = canvas
        return canvas

    def _build_header(self):
        header = tk.Frame(self.root, bg=COLORS['bg_panel'])
        header.pack(fill=tk.X)

        inner = tk.Frame(header, bg=COLORS['bg_panel'])
        inner.pack(fill=tk.X, padx=30, pady=16)

        tk.Label(inner, image=self.header_icon_img, bg=COLORS['bg_panel']).pack(side=tk.LEFT)

        titles = tk.Frame(inner, bg=COLORS['bg_panel'])
        titles.pack(side=tk.LEFT, padx=14)
        tk.Label(titles, text="Sınav Takvimi Yönetim Sistemi", font=("Segoe UI", 15, "bold"),
                 bg=COLORS['bg_panel'], fg=COLORS['text_light']).pack(anchor="w")
        tk.Label(titles, text=self.current_bolum or "Bölüm seçilmedi", font=("Segoe UI", 10),
                 bg=COLORS['bg_panel'], fg=COLORS['text_muted']).pack(anchor="w")

        tk.Button(inner, text="Çıkış Yap", font=("Segoe UI", 9, "bold"), relief="flat",
                  bg=COLORS['danger'], fg="white", padx=16, pady=7, bd=0,
                  activebackground=COLORS['danger'], activeforeground="white",
                  command=self.show_login_screen).pack(side=tk.RIGHT)

        user_box = tk.Frame(inner, bg=COLORS['bg_panel'])
        user_box.pack(side=tk.RIGHT, padx=16)
        tk.Label(user_box, text=self.current_user, font=("Segoe UI", 10, "bold"),
                 bg=COLORS['bg_panel'], fg=COLORS['text_light']).pack(anchor="e")
        tk.Label(user_box, text=self.current_role, font=("Segoe UI", 9),
                 bg=COLORS['bg_panel'], fg=COLORS['text_muted']).pack(anchor="e")

    def _build_department_prompt(self, parent):
        card = tk.Frame(parent, bg=COLORS['bg_card'], highlightbackground=COLORS['border'],
                         highlightthickness=1, padx=30, pady=25)
        card.pack(padx=40, pady=40, anchor="w")

        tk.Label(card, text="Devam etmek için bir bölüm seçmelisiniz",
                 font=("Segoe UI", 13, "bold"), bg=COLORS['bg_card'],
                 fg=COLORS['text_dark']).pack(anchor="w")
        tk.Label(card, text="Derslik/ders/öğrenci/sınav işlemleri, seçtiğiniz bölüme özeldir.\n"
                            "Henüz uygun bir bölüm yoksa önce yeni bir tane ekleyebilirsiniz.",
                 font=("Segoe UI", 10), bg=COLORS['bg_card'], fg=COLORS['text_muted'],
                 justify=tk.LEFT).pack(anchor="w", pady=(6, 14))
        tk.Button(card, text="Bölüm Seç / Ekle", font=("Segoe UI", 11, "bold"), relief="flat",
                  bg=COLORS['primary'], fg="white", padx=16, pady=7, bd=0,
                  command=self.show_select_department).pack(anchor="w")

    def _build_classroom_prompt(self, parent):
        card = tk.Frame(parent, bg=COLORS['bg_card'], highlightbackground=COLORS['border'],
                         highlightthickness=1, padx=30, pady=25)
        card.pack(padx=40, pady=40, anchor="w")

        tk.Label(card, text="Önce en az bir derslik eklemelisiniz",
                 font=("Segoe UI", 13, "bold"), bg=COLORS['bg_card'],
                 fg=COLORS['danger']).pack(anchor="w")
        tk.Label(card, text="Ders, öğrenci ve sınav programı menüleri, bu bölüme ait\n"
                            "en az bir derslik tanımlandıktan sonra açılır.",
                 font=("Segoe UI", 10), bg=COLORS['bg_card'], fg=COLORS['text_muted'],
                 justify=tk.LEFT).pack(anchor="w", pady=(6, 14))
        tk.Button(card, text="Derslik Ekle", font=("Segoe UI", 11, "bold"), relief="flat",
                  bg=COLORS['primary'], fg="white", padx=16, pady=7, bd=0,
                  command=self.show_add_classroom).pack(anchor="w")

    def _build_dashboard_cards(self, parent):
        stats = []
        for title, collection in [
            ("Öğrenci", self.db.ogrenciler),
            ("Ders", self.db.dersler),
            ("Derslik", self.db.derslikler),
            ("Öğretim Görevlisi", self.db.ogretim_gorevlileri),
            ("Planlanan Sınav", self.db.sinav_programi),
        ]:
            stats.append((title, collection.count_documents({'bolum_adi': self.current_bolum})))

        sinav_ids = [s['_id'] for s in self.db.sinav_programi.find(
            {'bolum_adi': self.current_bolum}, {'_id': 1})]
        oturma_plani_sayisi = 0
        if sinav_ids:
            oturma_plani_sayisi = len(
                self.db.oturma_plani.distinct('sinav_id', {'sinav_id': {'$in': sinav_ids}}))
        stats.append(("Oturma Planı", oturma_plani_sayisi))

        tk.Label(parent, text="Özet", font=("Segoe UI", 13, "bold"), bg=COLORS['bg_light'],
                 fg=COLORS['text_dark']).pack(anchor="w", padx=40, pady=(28, 0))

        cards_frame = tk.Frame(parent, bg=COLORS['bg_light'])
        cards_frame.pack(fill=tk.X, padx=32, pady=(12, 0))

        for i, (title, value) in enumerate(stats):
            card = tk.Frame(cards_frame, bg=COLORS['bg_card'],
                             highlightbackground=COLORS['border'], highlightthickness=1,
                             padx=18, pady=16)
            card.grid(row=0, column=i, padx=8, sticky="nsew")
            cards_frame.grid_columnconfigure(i, weight=1, uniform="card")

            tk.Label(card, text=str(value), font=("Segoe UI", 26, "bold"), bg=COLORS['bg_card'],
                     fg=COLORS['primary']).pack(anchor="w")
            tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), bg=COLORS['bg_card'],
                     fg=COLORS['text_muted'], wraplength=150).pack(anchor="w", pady=(4, 0))

    def _build_quick_actions(self, parent):
        actions = [
            ("Sınav Programı Oluştur", COLORS['primary'], self.show_exam_scheduler),
            ("Oturma Planı", COLORS['success'], self.show_seating_plan),
            ("Çakışma Raporu", COLORS['warning'], self.show_exam_conflicts),
            ("Sınav Takvimi", COLORS['primary_dark'], self.show_exam_calendar),
        ]

        tk.Label(parent, text="Hızlı İşlemler", font=("Segoe UI", 13, "bold"),
                 bg=COLORS['bg_light'], fg=COLORS['text_dark']).pack(anchor="w", padx=40, pady=(30, 0))

        row = tk.Frame(parent, bg=COLORS['bg_light'])
        row.pack(fill=tk.X, padx=32, pady=(12, 0))

        for i, (label, color, command) in enumerate(actions):
            tk.Button(row, text=label, font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                      bg=color, fg="white", activebackground=color, activeforeground="white",
                      padx=10, pady=16, command=command).grid(row=0, column=i, padx=8, sticky="ew")
            row.grid_columnconfigure(i, weight=1, uniform="action")

    def _build_upcoming_exams(self, parent, limit=6):
        bugun = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        sp_docs = list(self.db.sinav_programi
                       .find({'bolum_adi': self.current_bolum, 'sinav_tarihi': {'$gte': bugun}})
                       .sort([('sinav_tarihi', 1), ('sinav_saati', 1)])
                       .limit(limit))

        tk.Label(parent, text="Yaklaşan Sınavlar", font=("Segoe UI", 13, "bold"),
                 bg=COLORS['bg_light'], fg=COLORS['text_dark']).pack(anchor="w", padx=40, pady=(30, 0))

        if not sp_docs:
            tk.Label(parent, text="Planlanmış yaklaşan sınav yok.", font=("Segoe UI", 10),
                     bg=COLORS['bg_light'], fg=COLORS['text_muted']).pack(anchor="w", padx=40, pady=(8, 0))
            return

        ders_map = {d['_id']: d for d in self.db.dersler.find(
            {'_id': {'$in': [s['ders_id'] for s in sp_docs]}})}
        derslik_map = {d['_id']: d for d in self.db.derslikler.find(
            {'_id': {'$in': [s['derslik_id'] for s in sp_docs if s.get('derslik_id')]}})}
        gozetmen_map = {g['_id']: g for g in self.db.ogretim_gorevlileri.find(
            {'_id': {'$in': [s['gozetmen_id'] for s in sp_docs if s.get('gozetmen_id')]}})}

        table_frame = tk.Frame(parent, bg=COLORS['bg_light'])
        table_frame.pack(fill=tk.X, padx=40, pady=(12, 24))

        columns = ("Tarih", "Saat", "Ders", "Derslik", "Gözetmen")
        tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=len(sp_docs))
        for col, width in zip(columns, (110, 80, 280, 150, 190)):
            tree.heading(col, text=col)
            tree.column(col, width=width, anchor="w")
        tree.pack(fill=tk.X)

        for sp in sp_docs:
            ders = ders_map.get(sp['ders_id'])
            derslik = derslik_map.get(sp.get('derslik_id'))
            gozetmen = gozetmen_map.get(sp.get('gozetmen_id'))
            tree.insert("", tk.END, values=(
                sp['sinav_tarihi'].strftime('%d.%m.%Y'),
                str(sp['sinav_saati'])[:5],
                f"{ders['ders_kodu']} - {ders['ders_adi']}" if ders else "—",
                derslik['derslik_adi'] if derslik else "—",
                gozetmen['ad_soyad'] if gozetmen else "— Atanmadı —",
            ))

    def show_activity_log(self):
        window = tk.Toplevel(self.root)
        window.title("Aktivite Kaydı")
        window.geometry("900x600")

        tk.Label(window, text="Aktivite Kaydı", font=("Segoe UI", 14, "bold")).pack(pady=10)

        tree_frame = tk.Frame(window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("Zaman", "Kullanıcı", "Bölüm", "İşlem", "Detay")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                            yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)
        widths = (150, 200, 130, 160, 250)
        for col, width in zip(columns, widths):
            tree.heading(col, text=col)
            tree.column(col, width=width)
        tree.pack(fill=tk.BOTH, expand=True)

        rows = list(self.db.aktivite_log.find().sort('created_at', -1).limit(500))

        for row in rows:
            tree.insert("", tk.END, values=(
                row.get('created_at'), row.get('kullanici'),
                row.get('bolum_adi'), row.get('islem'), row.get('detay'),
            ))

        if not rows:
            tk.Label(window, text="Henüz aktivite kaydı yok.",
                     font=("Segoe UI", 10), fg=COLORS['text_muted']).pack(pady=10)
