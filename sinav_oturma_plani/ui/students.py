"""Öğrenci ekleme/düzenleme/listeleme, Excel'den toplu yükleme ve ders atama."""
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError
import pandas as pd

from .. import cascades


def _like_filter(*fields, query):
    """Verilen alanlarda büyük/küçük harf duyarsız alt dize araması.

    Kullanıcı girdisi regex metakarakteri içerebileceği için escape edilir."""
    pattern = re.escape(query)
    return {'$or': [{f: {'$regex': pattern, '$options': 'i'}} for f in fields]}


class StudentMixin:
    def download_student_template(self):
        """upload_student_excel'in beklediği sütunlarla örnek bir Excel şablonu üretir."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="ogrenci_sablonu.xlsx"
        )
        if not file_path:
            return

        df = pd.DataFrame({
            "Öğrenci No": ["2201001", "2201001", "2201002"],
            "Ad Soyad": ["Ayşe Kaya", "Ayşe Kaya", "Mehmet Demir"],
            "Sınıf": ["1", "1", "1"],
            "Ders": ["BLM101", "BLM103", "BLM101"],
            "E-posta": ["ayse.kaya@example.edu.tr", "ayse.kaya@example.edu.tr", ""],
        })
        try:
            df.to_excel(file_path, index=False)
            messagebox.showinfo(
                "Başarılı",
                "Şablon oluşturuldu.\n\n"
                "Her satır bir öğrenci-ders eşleşmesidir; aynı öğrenci birden fazla "
                "ders alıyorsa o öğrenci için birden fazla satır ekleyin "
                "(yukarıdaki örnekte olduğu gibi). 'E-posta' sütunu isteğe bağlıdır."
            )
        except Exception as e:
            messagebox.showerror("Hata", f"Şablon oluşturulamadı: {e}")

    def show_add_student(self):
        """Manuel öğrenci ekleme ekranı"""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        student_window = tk.Toplevel(self.root)
        student_window.title("Öğrenci Ekle")
        student_window.geometry("500x440")

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

        tk.Label(student_window, text="E-posta (opsiyonel):", font=("Arial", 11)).grid(
            row=3, column=0, padx=20, pady=10, sticky="w")
        email_entry = tk.Entry(student_window, font=("Arial", 11), width=30)
        email_entry.grid(row=3, column=1, padx=20, pady=10)

        def save_student():
            ogrenci_no = ogrenci_no_entry.get().strip()
            ad_soyad = ad_soyad_entry.get().strip()
            sinif = sinif_var.get()
            email = email_entry.get().strip() or None

            if not all([ogrenci_no, ad_soyad]):
                messagebox.showerror("Hata", "Öğrenci no ve ad soyad zorunludur!")
                return

            try:
                self.db.ogrenciler.insert_one({
                    'bolum_adi': self.current_bolum, 'ogrenci_no': ogrenci_no,
                    'ad_soyad': ad_soyad, 'sinif': sinif, 'email': email,
                })
                messagebox.showinfo("Başarılı", "Öğrenci başarıyla eklendi!")
                student_window.destroy()
            except DuplicateKeyError:
                messagebox.showerror("Hata", "Bu öğrenci numarası zaten mevcut!")
            except PyMongoError as e:
                messagebox.showerror("Hata", f"Öğrenci eklenemedi: {e}")

        tk.Button(student_window, text="Kaydet", font=("Arial", 12),
                  bg="#27ae60", fg="white", command=save_student).grid(
                        row=4, column=0, columnspan=2, pady=20)


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

            students = list(self.db.ogrenciler.find({
                'bolum_adi': self.current_bolum,
                **_like_filter('ogrenci_no', 'ad_soyad', query=query),
            }))

            for s in students:
                display_text = f"{s['ogrenci_no']} - {s['ad_soyad']} (Sınıf: {s.get('sinif')})"
                result_listbox.insert(tk.END, display_text)
                student_dict[display_text] = (s['_id'], s['ogrenci_no'], s['ad_soyad'],
                                               s.get('sinif'), s.get('email'))

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

        tk.Label(edit_frame, text="E-posta:", font=("Arial", 10)).grid(
            row=3, column=0, padx=10, pady=5, sticky="w")
        email_entry = tk.Entry(edit_frame, font=("Arial", 10), width=25)
        email_entry.grid(row=3, column=1, padx=10, pady=5)

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
                email_entry.delete(0, tk.END)
                email_entry.insert(0, data[4] or "")

        result_listbox.bind('<<ListboxSelect>>', load_student_data)

        def update_student():
            if not selected_id[0]:
                messagebox.showerror("Hata", "Öğrenci seçin!")
                return

            ogrenci_no = no_entry.get().strip()
            ad_soyad = ad_entry.get().strip()
            sinif = sinif_var.get()
            email = email_entry.get().strip() or None

            if not all([ogrenci_no, ad_soyad]):
                messagebox.showerror("Hata", "Tüm alanları doldurun!")
                return

            try:
                self.db.ogrenciler.update_one(
                    {'_id': selected_id[0], 'bolum_adi': self.current_bolum},
                    {'$set': {'ogrenci_no': ogrenci_no, 'ad_soyad': ad_soyad,
                              'sinif': sinif, 'email': email}})
                messagebox.showinfo("Başarılı", "Öğrenci güncellendi!")
                search_students()
            except PyMongoError as e:
                messagebox.showerror("Hata", f"Öğrenci güncellenemedi: {e}")

        def delete_student():
            if not selected_id[0]:
                messagebox.showerror("Hata", "Öğrenci seçin!")
                return

            if messagebox.askyesno("Onay", "Öğrenci silinsin mi?"):
                silinen_bilgi = f"{no_entry.get().strip()} - {ad_entry.get().strip()}"
                cascades.delete_student(self.db, selected_id[0])
                self.log_activity("Öğrenci silindi", silinen_bilgi)
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
        except Exception as e:
            messagebox.showerror("Hata", f"Excel okuma hatası: {e}")
            return

        required_cols = ['Öğrenci No', 'Ad Soyad', 'Sınıf', 'Ders']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            messagebox.showerror(
                "Hata",
                f"Eksik sütunlar: {', '.join(missing_cols)}\n\n"
                f"Dosyada mevcut sütunlar: {', '.join(df.columns)}\n\n"
                f"Gerekli sütunlar: Öğrenci No, Ad Soyad, Sınıf, Ders"
            )
            return

        bolum_adi = self.current_bolum
        total_rows = len(df)

        def worker(progress_callback):
            success_count = 0
            error_list = []

            for i, (index, row) in enumerate(df.iterrows()):
                try:
                    ogrenci_no = str(row['Öğrenci No']).strip()
                    ad_soyad = str(row['Ad Soyad']).strip()
                    sinif = str(row['Sınıf']).strip()
                    ders_kodu = str(row['Ders']).strip()
                    email = None
                    if 'E-posta' in df.columns:
                        email_val = str(row['E-posta']).strip()
                        if email_val and email_val.lower() != 'nan':
                            email = email_val

                    if not ogrenci_no or ogrenci_no == 'nan' or ogrenci_no == '':
                        continue

                    # ON DUPLICATE KEY UPDATE ... email=COALESCE(VALUES(email), email)
                    # karşılığı: bulunamazsa oluştur, bulunursa ad/sınıfı her zaman,
                    # e-postayı SADECE yeni değer varsa güncelle (var olanı boşla silme).
                    set_fields = {'ad_soyad': ad_soyad, 'sinif': sinif}
                    if email is not None:
                        set_fields['email'] = email

                    ogrenci_doc = self.db.ogrenciler.find_one_and_update(
                        {'bolum_adi': bolum_adi, 'ogrenci_no': ogrenci_no},
                        {'$set': set_fields},
                        upsert=True,
                        return_document=ReturnDocument.AFTER)
                    ogrenci_id = ogrenci_doc['_id']

                    ders_doc = self.db.dersler.find_one({'bolum_adi': bolum_adi, 'ders_kodu': ders_kodu})

                    if ders_doc:
                        try:
                            self.db.ogrenci_ders.insert_one(
                                {'ogrenci_id': ogrenci_id, 'ders_id': ders_doc['_id']})
                        except DuplicateKeyError:
                            pass  # zaten atanmış — INSERT IGNORE ile aynı davranış
                        success_count += 1
                    else:
                        error_list.append(
                            f"Satır {index+2} ({ogrenci_no}): '{ders_kodu}' dersi veritabanında bulunamadı"
                        )

                except PyMongoError as e:
                    error_msg = f"Satır {index+2}: {str(e)}"
                    error_list.append(error_msg)
                    print(error_msg)
                except Exception as e:
                    error_msg = f"Satır {index+2}: {str(e)}"
                    error_list.append(error_msg)
                    print(error_msg)

                progress_callback(i + 1, total_rows, f"{i + 1}/{total_rows} satır işleniyor...")

            message = f"✅ {success_count} öğrenci-ders kaydı yapıldı!"
            if error_list:
                message += f"\n\n⚠️ {len(error_list)} satırda hata oluştu:\n" + "\n".join(error_list[:5])
                if len(error_list) > 5:
                    message += f"\n... ve {len(error_list)-5} hata daha"
            return message

        self.run_background_task("Öğrenci Listesi Yükleniyor", worker)


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

            if search_query.strip():
                filtre = {'bolum_adi': self.current_bolum,
                          **_like_filter('ogrenci_no', 'ad_soyad', query=search_query)}
            else:
                filtre = {'bolum_adi': self.current_bolum}

            students = list(self.db.ogrenciler.find(filtre).sort('ogrenci_no', 1))

            # Tkinter tag'leri string olmak zorunda; ObjectId'yi buradan itibaren
            # str() ile saklayıp okurken tekrar ObjectId()'ye çeviriyoruz —
            # aksi halde Mongo sorgularında tip uyuşmazlığından sessizce eşleşmez.
            for student in students:
                student_tree.insert("", tk.END,
                                     values=(student['ogrenci_no'], student['ad_soyad'], student.get('sinif')),
                                     tags=(str(student['_id']),))

            info_label.config(text=f"Toplam {len(students)} öğrenci bulundu")

        def on_student_select(event):
            selection = student_tree.selection()
            if not selection:
                return

            item = student_tree.item(selection[0])
            student_id = ObjectId(item['tags'][0])
            student_no = item['values'][0]
            student_name = item['values'][1]
            student_class = item['values'][2]

            info_label.config(
                text=f"📚 {student_name} ({student_no}) - {student_class}. Sınıf",
                font=("Arial", 11, "bold"), fg="#2c3e50"
            )

            for item in course_tree.get_children():
                course_tree.delete(item)

            ders_ids = [od['ders_id'] for od in self.db.ogrenci_ders.find(
                {'ogrenci_id': student_id}, {'ders_id': 1})]
            courses = list(self.db.dersler.find({'_id': {'$in': ders_ids}}).sort('ders_kodu', 1))

            if courses:
                for course in courses:
                    course_tree.insert("", tk.END, values=(course['ders_kodu'], course['ders_adi']))
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

        total = self.db.ogrenciler.count_documents({'bolum_adi': self.current_bolum})

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

        # exportselection=False olmadan, aynı penceredeki iki liste kutusundan
        # birini seçmek diğerinin seçimini temizler (Tk'nin PRIMARY seçim sahipliği).
        student_listbox = tk.Listbox(left_frame, font=("Arial", 10), height=15,
                                      exportselection=False)
        student_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        student_dict = {}

        def search_students():
            query = search_entry.get().strip()
            student_listbox.delete(0, tk.END)
            student_dict.clear()

            if query:
                filtre = {'bolum_adi': self.current_bolum,
                          **_like_filter('ogrenci_no', 'ad_soyad', query=query)}
            else:
                filtre = {'bolum_adi': self.current_bolum}

            students = self.db.ogrenciler.find(filtre)

            for s in students:
                display = f"{s['ogrenci_no']} - {s['ad_soyad']} ({s.get('sinif')}. Sınıf)"
                student_listbox.insert(tk.END, display)
                student_dict[display] = s['_id']

        tk.Button(left_frame, text="Ara / Tümünü Listele", font=("Arial", 10),
                  bg="#3498db", fg="white", command=search_students).pack(pady=5)


        right_frame = tk.LabelFrame(assign_window, text="2. Dersleri Seç (Multiple Selection)",
                                    font=("Arial", 12, "bold"), padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        course_listbox = tk.Listbox(right_frame, font=("Arial", 10), height=15,
                                    selectmode=tk.MULTIPLE, exportselection=False)
        course_listbox.pack(fill=tk.BOTH, expand=True, pady=5)

        course_dict = {}

        def load_courses():
            course_listbox.delete(0, tk.END)
            course_dict.clear()

            courses = self.db.dersler.find({'bolum_adi': self.current_bolum}).sort(
                [('sinif', 1), ('ders_kodu', 1)])

            for c in courses:
                display = f"{c['ders_kodu']} - {c['ders_adi']} ({c.get('sinif')}. Sınıf)"
                course_listbox.insert(tk.END, display)
                course_dict[display] = c['_id']

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

            success_count = 0

            for idx in course_selections:
                course_text = course_listbox.get(idx)
                course_id = course_dict[course_text]

                try:
                    self.db.ogrenci_ders.insert_one({'ogrenci_id': student_id, 'ders_id': course_id})
                    success_count += 1
                except DuplicateKeyError:
                    success_count += 1  # zaten atanmış — INSERT IGNORE ile aynı davranış
                except PyMongoError:
                    pass

            messagebox.showinfo("Başarılı", f"{success_count} ders öğrenciye atandı!")

        tk.Button(assign_window, text="✅ Dersleri Ata", font=("Arial", 12, "bold"),
                  bg="#27ae60", fg="white", height=2, command=assign_courses).pack(pady=10)


        search_students()
