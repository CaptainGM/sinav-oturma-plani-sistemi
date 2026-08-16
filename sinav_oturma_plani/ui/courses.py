"""Ders ekleme/düzenleme/listeleme ve Excel'den toplu yükleme."""
import re
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pymongo.errors import DuplicateKeyError, PyMongoError
import pandas as pd

from .. import cascades


class CourseMixin:
    def download_course_template(self):
        """Ders yükleme ekranının beklediği formatta örnek bir Excel dosyası üretir."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="ders_sablonu.xlsx"
        )
        if not file_path:
            return

        rows = [
            ["SINIF: 1", "", ""],
            ["DERS KODU", "DERSİN ADI", "DERSİ VEREN ÖĞR. ELEMANI"],
            ["BLM101", "Programlama I", "Dr. Ahmet Yılmaz"],
            ["BLM103", "Matematik I", "Dr. Ayşe Kaya"],
            ["SINIF: 2", "", ""],
            ["BLM201", "Veri Yapıları", "Dr. Mehmet Demir"],
        ]
        try:
            pd.DataFrame(rows).to_excel(file_path, index=False, header=False)
            messagebox.showinfo(
                "Başarılı",
                "Şablon oluşturuldu.\n\n"
                "'SINIF: N' satırı kendisinden sonra gelen dersleri N. sınıfa atar; "
                "farklı sınıflar için ayrı 'SINIF: N' satırları ekleyebilirsiniz. "
                "'DERS KODU' başlık satırı dosyanın herhangi bir yerinde olabilir."
            )
        except Exception as e:
            messagebox.showerror("Hata", f"Şablon oluşturulamadı: {e}")

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
                self.db.dersler.insert_one({
                    'bolum_adi': self.current_bolum, 'ders_kodu': ders_kodu, 'ders_adi': ders_adı,
                    'hoca_adi': hoca_adı, 'ogretim_gorevlisi_id': None,
                    'sinif': sinif, 'ders_tipi': ders_tipi,
                })
                messagebox.showinfo("Başarılı", "Ders başarıyla eklendi!")
                course_window.destroy()
            except DuplicateKeyError:
                messagebox.showerror("Hata", "Bu ders kodu zaten mevcut!")
            except PyMongoError as e:
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

        docs = list(self.db.dersler.find({'bolum_adi': self.current_bolum}))
        dersler = [(d['_id'], d['ders_kodu'], d['ders_adi'], d.get('hoca_adi'),
                    d.get('sinif'), d.get('ders_tipi')) for d in docs]

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
                self.db.dersler.update_one(
                    {'_id': ders_id, 'bolum_adi': self.current_bolum},
                    {'$set': {'ders_kodu': ders_kodu, 'ders_adi': ders_adi, 'hoca_adi': hoca_adi,
                              'sinif': sinif, 'ders_tipi': ders_tipi}})
                messagebox.showinfo("Başarılı", "Ders güncellendi!")
                edit_window.destroy()
            except DuplicateKeyError:
                messagebox.showerror("Hata", "Bu ders kodu zaten mevcut!")
            except PyMongoError as e:
                messagebox.showerror("Hata", f"Ders güncellenemedi: {e}")

        def delete_course():
            selected = ders_var.get()
            if not selected:
                messagebox.showerror("Hata", "Ders seçin!")
                return

            if messagebox.askyesno("Onay", f"{selected} dersi silinsin mi?"):
                ders_id = ders_dict[selected][0]
                cascades.delete_course(self.db, ders_id)
                self.log_activity("Ders silindi", selected)
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
        except Exception as e:
            messagebox.showerror("Hata", f"Excel okuma hatası:\n{str(e)}")
            return

        col_mapping = {}
        required = {
            'ders_kodu': ['DERS KODU', 'DERSKODU', 'KOD'],
            'ders_adi': ['DERSİN ADI', 'DERS ADI', 'DERSADI', 'DERS'],
            'hoca_adi': ['DERSİ VEREN ÖĞR. ELEMANI', 'HOCA', 'ÖĞRETIM ELEMANI', 'ÖĞRETİM ÜYESİ', 'DERS VEREN ÖĞR. ELEMANI']
        }
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

        bolum_adi = self.current_bolum
        total_rows = len(df)

        def worker(progress_callback):
            success_count = 0
            error_list = []
            current_sinif = "1"

            for i, (index, row) in enumerate(df.iterrows()):
                try:
                    first_col = str(row[df.columns[0]]).strip()
                    if 'SINIF' in first_col.upper() or 'Sınıf' in first_col:
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

                    self.db.dersler.update_one(
                        {'bolum_adi': bolum_adi, 'ders_kodu': ders_kodu},
                        {'$set': {'ders_adi': ders_adi, 'hoca_adi': hoca_adi,
                                  'sinif': current_sinif, 'ders_tipi': ders_tipi}},
                        upsert=True)

                    success_count += 1

                except PyMongoError as e:
                    error_msg = f"Satır {index+2}: DB Hatası - {str(e)}"
                    error_list.append(error_msg)
                except Exception as e:
                    error_msg = f"Satır {index+2}: {str(e)}"
                    error_list.append(error_msg)

                progress_callback(i + 1, total_rows, f"{i + 1}/{total_rows} satır işleniyor...")

            message = f"✅ {success_count} ders başarıyla yüklendi!"
            if error_list:
                message += f"\n\n⚠️ {len(error_list)} satırda hata:\n" + "\n".join(error_list[:3])
                if len(error_list) > 3:
                    message += f"\n... ve {len(error_list)-3} hata daha"
            return message

        self.run_background_task("Ders Listesi Yükleniyor", worker)


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

        courses = list(self.db.dersler.find({'bolum_adi': self.current_bolum}).sort(
            [('sinif', 1), ('ders_kodu', 1)]))

        course_dict = {}
        for course in courses:
            ders_id = course['_id']
            ders_kodu = course['ders_kodu']
            ders_adi = course['ders_adi']
            hoca_adi = course.get('hoca_adi') or "Belirtilmemiş"
            sinif = course.get('sinif')

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

            ogrenci_ids = [od['ogrenci_id'] for od in self.db.ogrenci_ders.find(
                {'ders_id': ders_id}, {'ogrenci_id': 1})]
            ogrenciler = self.db.ogrenciler.find(
                {'_id': {'$in': ogrenci_ids}}).sort('ogrenci_no', 1)

            for o in ogrenciler:
                student_tree.insert("", tk.END, values=(o['ogrenci_no'], o['ad_soyad'], o.get('sinif')))

        course_tree.bind('<<TreeviewSelect>>', on_course_select)
