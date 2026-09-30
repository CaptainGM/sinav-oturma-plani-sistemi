"""Derslik ekleme/düzenleme/listeleme ve görsel yerleşim önizlemesi."""
import tkinter as tk
from tkinter import ttk, messagebox
from pymongo.errors import DuplicateKeyError, PyMongoError

from .. import cascades


def compute_classroom_capacity(enine, boyuna, sira_yapi):
    """Dersliğe kaç öğrenci oturabileceğini hesaplar.

    Anti-kopya boşluğu bırakıldığı için her kutudaki koltukların yarısı dolar.
    Bu yüzden kapasite elle girilmez, buradan hesaplanır."""
    if enine <= 0 or boyuna <= 0 or sira_yapi <= 0:
        return 0
    doluluk_kutu_basi = (sira_yapi + 1) // 2
    return enine * boyuna * doluluk_kutu_basi


class ClassroomMixin:
    def show_add_classroom(self):
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        classroom_window = tk.Toplevel(self.root)
        classroom_window.title("Derslik Ekle")
        classroom_window.geometry("500x520")

        fields = [
            ("Derslik Kodu:", tk.Entry(classroom_window, font=("Arial", 11), width=30)),
            ("Derslik Adı:", tk.Entry(classroom_window, font=("Arial", 11), width=30)),
            ("Enine Sıra Sayısı:", tk.Entry(classroom_window, font=("Arial", 11), width=30)),
            ("Boyuna Sıra Sayısı:", tk.Entry(classroom_window, font=("Arial", 11), width=30)),
            ("Sıra Yapısı (kutu başına koltuk sayısı):", tk.Entry(classroom_window, font=("Arial", 11), width=30)),
        ]

        entries = []
        for i, (label, entry) in enumerate(fields):
            tk.Label(classroom_window, text=label, font=("Arial", 11)).grid(row=i, column=0, padx=20, pady=10, sticky="w")
            entry.grid(row=i, column=1, padx=20, pady=10)
            entries.append(entry)

        enine_entry, boyuna_entry, sira_yapi_entry = entries[2], entries[3], entries[4]

        kapasite_var = tk.StringVar(value="0")
        tk.Label(classroom_window, text="Hesaplanan Kapasite (anti-kopya boşluklu):",
                 font=("Arial", 11)).grid(row=5, column=0, padx=20, pady=10, sticky="w")
        tk.Label(classroom_window, textvariable=kapasite_var, font=("Arial", 12, "bold"),
                 fg="#2980b9").grid(row=5, column=1, padx=20, pady=10, sticky="w")

        def recompute_kapasite(event=None):
            try:
                enine = int(enine_entry.get())
                boyuna = int(boyuna_entry.get())
                sira_yapi = int(sira_yapi_entry.get())
                kapasite_var.set(str(compute_classroom_capacity(enine, boyuna, sira_yapi)))
            except ValueError:
                kapasite_var.set("0")

        for e in (enine_entry, boyuna_entry, sira_yapi_entry):
            e.bind("<KeyRelease>", recompute_kapasite)

        def save_classroom():
            kod, ad, enine_str, boyuna_str, sira_yapi_str = [e.get() for e in entries]
            if not all([kod, ad, enine_str, boyuna_str, sira_yapi_str]):
                messagebox.showerror("Hata", "Tüm alanları doldurun!")
                return

            try:
                enine = int(enine_str)
                boyuna = int(boyuna_str)
                sira_yapi = int(sira_yapi_str)

                if enine <= 0 or boyuna <= 0 or sira_yapi <= 0:
                    messagebox.showerror("Hata", "Enine sıra, boyuna sıra ve sıra yapısı pozitif olmalı!")
                    return

                kapasite = compute_classroom_capacity(enine, boyuna, sira_yapi)

                self.db.derslikler.insert_one({
                    'bolum_adi': self.current_bolum, 'derslik_kodu': kod, 'derslik_adi': ad,
                    'kapasite': kapasite, 'enine_sira': enine, 'boyuna_sira': boyuna,
                    'sira_yapisi': sira_yapi,
                })
                messagebox.showinfo("Başarılı", f"Derslik eklendi! Kapasite: {kapasite}")
                classroom_window.destroy()
                self.show_main_menu()
            except ValueError:
                messagebox.showerror("Hata", "Sayısal değerler geçerli olmalı!")
            except DuplicateKeyError:
                messagebox.showerror("Hata", "Bu derslik kodu zaten mevcut!")
            except PyMongoError as e:
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

        docs = list(self.db.derslikler.find({'bolum_adi': self.current_bolum}))
        derslikler = [(d['_id'], d['derslik_kodu'], d['derslik_adi'], d['kapasite'],
                       d['enine_sira'], d['boyuna_sira'], d['sira_yapisi']) for d in docs]

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

        labels = ["Derslik Kodu:", "Derslik Adı:", "Enine Sıra:", "Boyuna Sıra:", "Sıra Yapısı:"]
        entries = []

        for i, label in enumerate(labels):
            tk.Label(edit_frame, text=label, font=("Arial", 11)).grid(row=i, column=0, padx=10, pady=10, sticky="w")
            entry = tk.Entry(edit_frame, font=("Arial", 11), width=30)
            entry.grid(row=i, column=1, padx=10, pady=10)
            entries.append(entry)

        enine_entry, boyuna_entry, sira_yapi_entry = entries[2], entries[3], entries[4]

        kapasite_var = tk.StringVar(value="0")
        tk.Label(edit_frame, text="Hesaplanan Kapasite (anti-kopya boşluklu):",
                 font=("Arial", 11)).grid(row=5, column=0, padx=10, pady=10, sticky="w")
        tk.Label(edit_frame, textvariable=kapasite_var, font=("Arial", 12, "bold"),
                 fg="#2980b9").grid(row=5, column=1, padx=10, pady=10, sticky="w")

        def recompute_kapasite(event=None):
            try:
                enine = int(enine_entry.get())
                boyuna = int(boyuna_entry.get())
                sira_yapi = int(sira_yapi_entry.get())
                kapasite_var.set(str(compute_classroom_capacity(enine, boyuna, sira_yapi)))
            except ValueError:
                kapasite_var.set("0")

        for e in (enine_entry, boyuna_entry, sira_yapi_entry):
            e.bind("<KeyRelease>", recompute_kapasite)

        def load_classroom_data(event=None):
            selected = derslik_var.get()
            if selected and selected in derslik_dict:
                data = derslik_dict[selected]
                entries[0].delete(0, tk.END)
                entries[0].insert(0, data[1])
                entries[1].delete(0, tk.END)
                entries[1].insert(0, data[2])
                entries[2].delete(0, tk.END)
                entries[2].insert(0, data[4])
                entries[3].delete(0, tk.END)
                entries[3].insert(0, data[5])
                entries[4].delete(0, tk.END)
                entries[4].insert(0, data[6])
                recompute_kapasite()

        derslik_combo.bind('<<ComboboxSelected>>', load_classroom_data)

        def update_classroom():
            selected = derslik_var.get()
            if not selected:
                messagebox.showerror("Hata", "Derslik seçin!")
                return

            derslik_id = derslik_dict[selected][0]
            kod, ad, enine_str, boyuna_str, sira_yapi_str = [e.get() for e in entries]

            if not all([kod, ad, enine_str, boyuna_str, sira_yapi_str]):
                messagebox.showerror("Hata", "Tüm alanları doldurun!")
                return

            try:
                enine = int(enine_str)
                boyuna = int(boyuna_str)
                sira_yapi = int(sira_yapi_str)

                if enine <= 0 or boyuna <= 0 or sira_yapi <= 0:
                    messagebox.showerror("Hata", "Enine sıra, boyuna sıra ve sıra yapısı pozitif olmalı!")
                    return

                kapasite = compute_classroom_capacity(enine, boyuna, sira_yapi)

                self.db.derslikler.update_one(
                    {'_id': derslik_id, 'bolum_adi': self.current_bolum},
                    {'$set': {'derslik_kodu': kod, 'derslik_adi': ad, 'kapasite': kapasite,
                              'enine_sira': enine, 'boyuna_sira': boyuna, 'sira_yapisi': sira_yapi}})
                messagebox.showinfo("Başarılı", "Derslik güncellendi!")
                edit_window.destroy()
            except ValueError:
                messagebox.showerror("Hata", "Sayısal değerler geçerli olmalı!")
            except DuplicateKeyError:
                messagebox.showerror("Hata", "Bu derslik kodu zaten mevcut!")
            except PyMongoError as e:
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

            result = self.db.derslikler.find_one({'bolum_adi': self.current_bolum, 'derslik_kodu': kod})

            if result:
                classroom_tuple = (result['_id'], result['bolum_adi'], result['derslik_kodu'],
                                    result['derslik_adi'], result['kapasite'], result['enine_sira'],
                                    result['boyuna_sira'], result['sira_yapisi'])
                self.visualize_classroom(classroom_tuple)
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

        docs = self.db.derslikler.find({'bolum_adi': self.current_bolum})
        for d in docs:
            tree.insert("", tk.END, values=(
                d['derslik_kodu'], d['derslik_adi'], d['kapasite'],
                d['enine_sira'], d['boyuna_sira'], d['sira_yapisi']))

        tree.pack(fill=tk.BOTH, expand=True)

        def delete_classroom():
            selected = tree.selection()
            if not selected:
                messagebox.showerror("Hata", "Silinecek dersliği seçin!")
                return

            item = tree.item(selected[0])
            kod = item['values'][0]

            if messagebox.askyesno("Onay", f"{kod} kodlu derslik silinsin mi?"):
                derslik = self.db.derslikler.find_one({'bolum_adi': self.current_bolum, 'derslik_kodu': kod})
                if derslik:
                    cascades.delete_classroom(self.db, derslik['_id'])
                tree.delete(selected[0])
                self.log_activity("Derslik silindi", kod)
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
