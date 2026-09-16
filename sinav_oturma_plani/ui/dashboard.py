"""Ana menü (üst menü çubuğu) ve bölüm bazlı özet istatistik kartları."""
import tkinter as tk
from tkinter import ttk

from ..styles import COLORS


class DashboardMixin:
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
            admin_menu.add_command(label="Aktivite Kaydı", command=self.show_activity_log)

       
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
                sinav_menu.add_command(label="Gözetmen Ata", command=self.show_assign_proctor)
                sinav_menu.add_command(label="Çakışma Raporu", command=self.show_exam_conflicts)
                sinav_menu.add_command(label="Sınav Takvimi (Genel Görünüm)", command=self.show_exam_calendar)

        welcome_frame = tk.Frame(self.root, bg=COLORS['bg_light'])
        welcome_frame.pack(fill=tk.BOTH, expand=True)

        header_frame = tk.Frame(welcome_frame, bg=COLORS['bg_light'])
        header_frame.pack(fill=tk.X, padx=40, pady=(30, 10))

        tk.Label(header_frame, text=f"Hoş Geldiniz, {self.current_user}",
                 font=("Segoe UI", 20, "bold"), bg=COLORS['bg_light'],
                 fg=COLORS['text_dark']).pack(anchor="w")
        if self.current_bolum:
            tk.Label(header_frame, text=f"Bölüm: {self.current_bolum}",
                     font=("Segoe UI", 12), bg=COLORS['bg_light'],
                     fg=COLORS['text_muted']).pack(anchor="w", pady=(2, 0))

        if self.current_role in ["Bölüm Koordinatörü", "Admin"] and self.current_bolum and not self.check_derslik_requirement():
            tk.Label(welcome_frame,
                     text="⚠️ UYARI: Devam edebilmek için önce en az bir derslik girmelisiniz!",
                     font=("Segoe UI", 13, "bold"), bg=COLORS['bg_light'],
                     fg=COLORS['danger']).pack(pady=15)
        elif self.current_bolum:
            self._build_dashboard_cards(welcome_frame)


    def _build_dashboard_cards(self, parent):
        """Seçili bölüm için öğrenci/ders/derslik/öğretim görevlisi/sınav
        sayıları gibi özet istatistik kartlarını oluşturur."""
        cursor = self.db.connection.cursor()
        try:
            stats = []
            for title, query in [
                ("Öğrenci", "SELECT COUNT(*) FROM ogrenciler WHERE bolum_adi=%s"),
                ("Ders", "SELECT COUNT(*) FROM dersler WHERE bolum_adi=%s"),
                ("Derslik", "SELECT COUNT(*) FROM derslikler WHERE bolum_adi=%s"),
                ("Öğretim Görevlisi", "SELECT COUNT(*) FROM ogretim_gorevlileri WHERE bolum_adi=%s"),
                ("Planlanan Sınav", "SELECT COUNT(*) FROM sinav_programi WHERE bolum_adi=%s"),
            ]:
                cursor.execute(query, (self.current_bolum,))
                stats.append((title, cursor.fetchone()[0]))

            cursor.execute("""
                SELECT COUNT(DISTINCT op.sinav_id) FROM oturma_plani op
                JOIN sinav_programi sp ON op.sinav_id = sp.id
                WHERE sp.bolum_adi=%s
            """, (self.current_bolum,))
            stats.append(("Oluşturulan Oturma Planı", cursor.fetchone()[0]))
        finally:
            cursor.close()

        cards_frame = tk.Frame(parent, bg=COLORS['bg_light'])
        cards_frame.pack(fill=tk.X, padx=40, pady=20)

        for i, (title, value) in enumerate(stats):
            card = tk.Frame(cards_frame, bg=COLORS['bg_card'],
                             highlightbackground=COLORS['border'], highlightthickness=1,
                             padx=18, pady=14)
            card.grid(row=0, column=i, padx=8, sticky="nsew")
            cards_frame.grid_columnconfigure(i, weight=1)

            tk.Label(card, text=title, font=("Segoe UI", 9, "bold"), bg=COLORS['bg_card'],
                     fg=COLORS['text_muted'], wraplength=150).pack(anchor="w")
            tk.Label(card, text=str(value), font=("Segoe UI", 24, "bold"), bg=COLORS['bg_card'],
                     fg=COLORS['primary']).pack(anchor="w", pady=(6, 0))

    def show_activity_log(self):
        """Kim ne zaman ne yaptı kaydını (aktivite_log) listeler. Sadece Admin
        erişebilir; tüm bölümlerdeki kayıtları gösterir."""
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

        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT created_at, kullanici, bolum_adi, islem, detay
            FROM aktivite_log
            ORDER BY created_at DESC
            LIMIT 500
        """)
        rows = cursor.fetchall()
        cursor.close()

        for row in rows:
            tree.insert("", tk.END, values=row)

        if not rows:
            tk.Label(window, text="Henüz aktivite kaydı yok.",
                     font=("Segoe UI", 10), fg=COLORS['text_muted']).pack(pady=10)

