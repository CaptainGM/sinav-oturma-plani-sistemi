"""Öğretim görevlisi ekleme/düzenleme/listeleme."""
import tkinter as tk
from tkinter import ttk, messagebox
from pymongo.errors import DuplicateKeyError, PyMongoError

from .. import cascades


class InstructorMixin:
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
                self.db.ogretim_gorevlileri.insert_one({
                    'bolum_adi': self.current_bolum, 'sicil_no': sicil, 'ad_soyad': ad_soyad,
                    'unvan': unvan, 'email': email, 'telefon': telefon,
                })
                messagebox.showinfo("Başarılı", "Öğretim görevlisi eklendi!")
                inst_window.destroy()
            except DuplicateKeyError:
                messagebox.showerror("Hata", "Bu sicil no zaten mevcut!")
            except PyMongoError as e:
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

        docs = list(self.db.ogretim_gorevlileri.find({'bolum_adi': self.current_bolum}))
        gorevliler = [(d['_id'], d['sicil_no'], d['ad_soyad'], d.get('unvan'),
                       d.get('email'), d.get('telefon')) for d in docs]

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
                self.db.ogretim_gorevlileri.update_one(
                    {'_id': gorevli_id, 'bolum_adi': self.current_bolum},
                    {'$set': {'sicil_no': sicil, 'ad_soyad': ad_soyad, 'unvan': unvan,
                              'email': email, 'telefon': telefon}})
                messagebox.showinfo("Başarılı", "Öğretim görevlisi güncellendi!")
                edit_window.destroy()
            except PyMongoError as e:
                messagebox.showerror("Hata", f"Güncellenemedi: {e}")

        def delete_instructor():
            selected = gorevli_var.get()
            if not selected:
                messagebox.showerror("Hata", "Öğretim görevlisi seçin!")
                return

            if messagebox.askyesno("Onay", f"{selected} silinsin mi?"):
                gorevli_id = gorevli_dict[selected][0]
                cascades.delete_instructor(self.db, gorevli_id)
                self.log_activity("Öğretim görevlisi silindi", selected)
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

        docs = self.db.ogretim_gorevlileri.find({'bolum_adi': self.current_bolum}).sort('ad_soyad', 1)
        for d in docs:
            tree.insert("", tk.END, values=(
                d['sicil_no'], d['ad_soyad'], d.get('unvan'), d.get('email'), d.get('telefon')))

        tree.pack(fill=tk.BOTH, expand=True)
