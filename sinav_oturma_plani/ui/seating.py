"""Oturma planı oluşturma/görüntüleme, gözetmen atama, PDF/Excel dışa aktarım."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from collections import defaultdict
import random
import pandas as pd
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from ..notifications import smtp_configured, send_email
from ..styles import COLORS

try:

    pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
except Exception as e:

    print(f"Uyarı: Arial font dosyaları bulunamadı! Varsayılan font kullanılacak. Hata: {e}")


def is_seat_empty(koltuk_no, sira_yapi):
    """Anti-kopya düzeni: çift numaralı koltuklar boş bırakılır.

    Sıra yapısı 1 ise hiçbir koltuk boşaltılmaz."""
    if sira_yapi <= 1:
        return False
    return koltuk_no % 2 == 0


class SeatingMixin:
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

        sp_docs = list(self.db.sinav_programi.find({'bolum_adi': self.current_bolum})
                       .sort([('sinav_tarihi', 1), ('sinav_saati', 1)]))

        ders_ids = list({sp['ders_id'] for sp in sp_docs})
        derslik_ids = list({sp['derslik_id'] for sp in sp_docs if sp.get('derslik_id') is not None})
        ders_map = {d['_id']: d for d in self.db.dersler.find({'_id': {'$in': ders_ids}})}
        derslik_map = {d['_id']: d for d in self.db.derslikler.find({'_id': {'$in': derslik_ids}})}

        sinavlar = []
        for sp in sp_docs:
            ders = ders_map.get(sp['ders_id'])
            derslik = derslik_map.get(sp.get('derslik_id'))
            if not ders or not derslik:
                continue
            sinavlar.append((sp['_id'], ders['ders_kodu'], ders['ders_adi'],
                              sp['sinav_tarihi'], sp['sinav_saati'], derslik['derslik_adi']))

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


    def show_assign_proctor(self):
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        gorevliler = [(g['_id'], g['sicil_no'], g['ad_soyad'])
                      for g in self.db.ogretim_gorevlileri.find({'bolum_adi': self.current_bolum})
                      .sort('ad_soyad', 1)]

        if not gorevliler:
            messagebox.showinfo("Bilgi", "Önce en az bir öğretim görevlisi eklemelisiniz!")
            return

        sp_docs = list(self.db.sinav_programi.find({'bolum_adi': self.current_bolum})
                       .sort([('sinav_tarihi', 1), ('sinav_saati', 1)]))

        ders_ids = list({sp['ders_id'] for sp in sp_docs})
        derslik_ids = list({sp['derslik_id'] for sp in sp_docs if sp.get('derslik_id') is not None})
        gozetmen_ids = list({sp['gozetmen_id'] for sp in sp_docs if sp.get('gozetmen_id') is not None})

        ders_map = {d['_id']: d for d in self.db.dersler.find({'_id': {'$in': ders_ids}})}
        derslik_map = {d['_id']: d for d in self.db.derslikler.find({'_id': {'$in': derslik_ids}})}
        gorevli_map = {g['_id']: g for g in self.db.ogretim_gorevlileri.find({'_id': {'$in': gozetmen_ids}})}

        sinavlar = []
        for sp in sp_docs:
            ders = ders_map.get(sp['ders_id'])
            derslik = derslik_map.get(sp.get('derslik_id'))
            if not ders or not derslik:
                continue
            gozetmen = gorevli_map.get(sp.get('gozetmen_id'))
            sinavlar.append((sp['_id'], ders['ders_kodu'], ders['ders_adi'], sp['sinav_tarihi'],
                              sp['sinav_saati'], derslik['derslik_adi'], sp.get('gozetmen_id'),
                              gozetmen['ad_soyad'] if gozetmen else None))

        if not sinavlar:
            messagebox.showinfo("Bilgi", "Henüz sınav programı oluşturulmamış!")
            return

        window = tk.Toplevel(self.root)
        window.title("Gözetmen Ata")
        window.geometry("950x600")

        tk.Label(window, text="Sınavlara Gözetmen Ata", font=("Arial", 14, "bold")).pack(pady=10)
        tk.Label(window, text="Bir sınav satırı seçin, gözetmeni seçip 'Ata' butonuna basın.",
                 font=("Arial", 9), fg="#555555").pack(pady=(0, 10))

        list_frame = tk.Frame(window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("Ders", "Tarih", "Saat", "Derslik", "Gözetmen")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        tree.pack(fill=tk.BOTH, expand=True)

        gorevli_isimleri = [f"{g[1]} - {g[2]}" for g in gorevliler]
        gorevli_id_by_isim = {f"{g[1]} - {g[2]}": g[0] for g in gorevliler}

        sinav_id_by_item = {}
        for sinav in sinavlar:
            sinav_id, ders_kodu, ders_adi, tarih, saat, derslik_adi, gozetmen_id, gozetmen_adi = sinav
            gozetmen_text = gozetmen_adi if gozetmen_adi else "— Atanmadı —"
            item_id = tree.insert("", tk.END, values=(
                f"{ders_kodu} - {ders_adi}", tarih, saat, derslik_adi, gozetmen_text
            ))
            sinav_id_by_item[item_id] = sinav_id

        assign_frame = tk.Frame(window)
        assign_frame.pack(pady=10)

        tk.Label(assign_frame, text="Gözetmen:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        gozetmen_var = tk.StringVar()
        gozetmen_combo = ttk.Combobox(assign_frame, textvariable=gozetmen_var,
                                       values=gorevli_isimleri, width=35, state="readonly")
        gozetmen_combo.pack(side=tk.LEFT, padx=5)

        def kaydet():
            selection = tree.selection()
            if not selection:
                messagebox.showerror("Hata", "Bir sınav seçin!")
                return
            secilen_isim = gozetmen_var.get()
            if not secilen_isim:
                messagebox.showerror("Hata", "Bir gözetmen seçin!")
                return

            item_id = selection[0]
            sinav_id = sinav_id_by_item[item_id]
            gozetmen_id = gorevli_id_by_isim[secilen_isim]

            self.db.sinav_programi.update_one({'_id': sinav_id}, {'$set': {'gozetmen_id': gozetmen_id}})

            values = list(tree.item(item_id, "values"))
            values[4] = secilen_isim
            tree.item(item_id, values=values)
            self.log_activity("Gözetmen atandı", f"{values[0]} -> {secilen_isim}")
            messagebox.showinfo("Başarılı", "Gözetmen atandı!")

        tk.Button(assign_frame, text="Ata", font=("Arial", 10, "bold"),
                  bg="#27ae60", fg="white", command=kaydet).pack(side=tk.LEFT, padx=10)


    def generate_seating_plan(self, sinav_id):
        """Öğrencileri karışık sırayla dersliklere yerleştirir.

        Koltuk numarası sutun_no = kutu_sutun * 10 + koltuk_no olarak saklanır."""
        sinav_info = self.db.sinav_programi.find_one({'_id': sinav_id})
        if not sinav_info:
            messagebox.showerror("Hata", "Sınav bulunamadı!")
            return

        ders_id = sinav_info['ders_id']
        sinav_tarihi = sinav_info['sinav_tarihi']
        sinav_saati = sinav_info['sinav_saati']


        sp_docs = list(self.db.sinav_programi.find({
            'ders_id': ders_id, 'sinav_tarihi': sinav_tarihi, 'sinav_saati': sinav_saati,
        }))
        derslik_ids = [sp['derslik_id'] for sp in sp_docs if sp.get('derslik_id') is not None]
        derslik_map = {d['_id']: d for d in self.db.derslikler.find({'_id': {'$in': derslik_ids}})}

        sp_with_derslik = [(sp, derslik_map[sp['derslik_id']]) for sp in sp_docs
                            if sp.get('derslik_id') in derslik_map]
        sp_with_derslik.sort(key=lambda pair: pair[1]['kapasite'], reverse=True)

        tum_derslikler = [(sp['_id'], derslik['_id'], derslik['kapasite'], derslik['enine_sira'],
                            derslik['boyuna_sira'], derslik['sira_yapisi'], derslik['derslik_adi'])
                           for sp, derslik in sp_with_derslik]

        if not tum_derslikler:
            messagebox.showerror("Hata", "Derslik bilgisi bulunamadı!")
            return


        enrollment_docs = list(self.db.ogrenci_ders.find({'ders_id': ders_id}, {'ogrenci_id': 1}))
        ogrenci_ids = [e['ogrenci_id'] for e in enrollment_docs]
        ogrenci_map = {o['_id']: o for o in self.db.ogrenciler.find({'_id': {'$in': ogrenci_ids}})}
        ogrenciler = [(oid, ogrenci_map[oid]['ogrenci_no'], ogrenci_map[oid]['ad_soyad'])
                      for oid in ogrenci_ids if oid in ogrenci_map]
        random.shuffle(ogrenciler)

        toplam_kapasite = sum(d[2] for d in tum_derslikler)

        if len(ogrenciler) > toplam_kapasite:
            messagebox.showerror(
                "Hata",
                f"❌ Öğrenci sayısı ({len(ogrenciler)}) toplam derslik kapasitesini ({toplam_kapasite}) aşıyor!"
            )
            return


        self.db.oturma_plani.delete_many({'sinav_id': {'$in': [d[0] for d in tum_derslikler]}})


        ogrenci_index = 0
        yerlestirildi = 0
        oturma_docs = []

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


                        if is_seat_empty(koltuk_no, sira_yapi):
                            continue


                        if ogrenci_index >= len(ogrenciler) or seated_count_in_derslik >= students_to_seat_in_derslik:
                            break

                        ogrenci = ogrenciler[ogrenci_index]

                        sutun_kaydi = kutu_sutun * 10 + koltuk_no


                        oturma_docs.append({
                            'sinav_id': sinav_programi_id, 'ogrenci_id': ogrenci[0],
                            'derslik_id': derslik_id, 'sira_no': sira, 'sutun_no': sutun_kaydi,
                        })

                        seated_count_in_derslik += 1
                        ogrenci_index += 1
                        yerlestirildi += 1

                    if ogrenci_index >= len(ogrenciler) or seated_count_in_derslik >= students_to_seat_in_derslik:
                        break

                if ogrenci_index >= len(ogrenciler):
                    break

        if oturma_docs:
            self.db.oturma_plani.insert_many(oturma_docs)

        derslik_sayisi = len(tum_derslikler)
        derslik_isimleri = ', '.join(d[6] for d in tum_derslikler)

        self.log_activity("Oturma planı oluşturuldu",
                           f"sinav_id={sinav_id}, {yerlestirildi} öğrenci, {derslik_isimleri}")

        messagebox.showinfo(
            "Başarılı",
            f"✅ Oturma planı oluşturuldu!\n\n"
            f"Toplam {yerlestirildi} öğrenci {derslik_sayisi} dersliğe yerleştirildi."
        )


    def view_seating_plan(self, sinav_id):
        sinav_info = self.db.sinav_programi.find_one({'_id': sinav_id})
        if not sinav_info:
            messagebox.showerror("Hata", "Sınav bulunamadı!")
            return

        ders = self.db.dersler.find_one({'_id': sinav_info['ders_id']})
        if not ders:
            messagebox.showerror("Hata", "Sınav bulunamadı!")
            return

        ders_kodu = ders['ders_kodu']
        ders_adi = ders['ders_adi']
        sinav_tarihi = sinav_info['sinav_tarihi']
        sinav_saati = sinav_info['sinav_saati']
        ders_id = sinav_info['ders_id']


        sp_docs = list(self.db.sinav_programi.find({
            'ders_id': ders_id, 'sinav_tarihi': sinav_tarihi, 'sinav_saati': sinav_saati,
        }))
        derslik_ids = [sp['derslik_id'] for sp in sp_docs if sp.get('derslik_id') is not None]
        derslik_map = {d['_id']: d for d in self.db.derslikler.find({'_id': {'$in': derslik_ids}})}

        sp_with_derslik = [(sp, derslik_map[sp['derslik_id']]) for sp in sp_docs
                            if sp.get('derslik_id') in derslik_map]
        sp_with_derslik.sort(key=lambda pair: pair[1]['kapasite'], reverse=True)

        tum_derslikler = [(derslik['_id'], derslik['derslik_adi'], derslik['enine_sira'],
                            derslik['boyuna_sira'], derslik['sira_yapisi'], sp['_id'])
                           for sp, derslik in sp_with_derslik]

        if not tum_derslikler:
            messagebox.showwarning("Uyarı", "Bu sınav için derslik bulunamadı!")
            return

        view_window = tk.Toplevel(self.root)
        view_window.title(f"Oturma Planı - {ders_adi}")
        view_window.geometry("1200x800")

        info_text = f"""
    Ders: {ders_kodu} - {ders_adi}
    Tarih: {sinav_tarihi} | Saat: {sinav_saati}
    Kullanılan Derslik Sayısı: {len(tum_derslikler)}
        """

        info_label = tk.Label(view_window, text=info_text, font=("Arial", 12, "bold"),
                              justify=tk.LEFT, bg=COLORS['primary'], fg="white", padx=10, pady=10)
        info_label.pack(fill=tk.X)

        legend_frame = tk.Frame(view_window, bg=COLORS['bg_light'])
        legend_frame.pack(fill=tk.X)
        for renk, aciklama in [
            ("#27ae60", "Öğrenci oturuyor (tıklayıp başka koltukla yer değiştirebilirsiniz)"),
            ("#ecf0f1", "Anti-kopya boşluğu (bilerek boş bırakılır)"),
            ("#95a5a6", "Bu sınavda kullanılmıyor"),
        ]:
            item = tk.Frame(legend_frame, bg=COLORS['bg_light'])
            item.pack(side=tk.LEFT, padx=10, pady=6)
            tk.Frame(item, bg=renk, width=14, height=14, highlightbackground="black",
                     highlightthickness=1).pack(side=tk.LEFT, padx=(0, 5))
            tk.Label(item, text=aciklama, font=("Segoe UI", 8), bg=COLORS['bg_light'],
                     fg=COLORS['text_muted']).pack(side=tk.LEFT)

        swap_status_var = tk.StringVar(
            value="💡 Yer değiştirmek için bir öğrenciye, ardından değiştirmek istediğiniz koltuğa tıklayın.")
        tk.Label(view_window, textvariable=swap_status_var, font=("Segoe UI", 9, "italic"),
                 bg=COLORS['bg_light'], fg=COLORS['primary']).pack(fill=tk.X, pady=(0, 4))

        notebook = ttk.Notebook(view_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tum_oturma_verileri = {}
        selection = {}

        def swap_seats(op_id_a, sira_a, sutun_a, op_id_b, sira_b, sutun_b):
            self.db.oturma_plani.update_one({'_id': op_id_a}, {'$set': {'sira_no': sira_b, 'sutun_no': sutun_b}})
            self.db.oturma_plani.update_one({'_id': op_id_b}, {'$set': {'sira_no': sira_a, 'sutun_no': sutun_a}})

        def on_seat_click(op_id, ad_soyad, sira, sutun_no, sinav_programi_id,
                           canvas_widget, derslik_data):
            if not selection:
                selection.update(op_id=op_id, ad_soyad=ad_soyad, sira=sira, sutun_no=sutun_no,
                                  sinav_programi_id=sinav_programi_id,
                                  canvas_widget=canvas_widget, derslik_data=derslik_data)
                swap_status_var.set(
                    f"Seçili: {ad_soyad}. Şimdi yer değiştirmek istediğiniz koltuğa tıklayın "
                    f"(iptal için aynı öğrenciye tekrar tıklayın).")
                return

            if selection['op_id'] == op_id:
                selection.clear()
                swap_status_var.set("Seçim iptal edildi.")
                return

            if selection['sinav_programi_id'] != sinav_programi_id:
                messagebox.showerror("Hata", "Yer değiştirme yalnızca aynı derslik içinde yapılabilir!")
                selection.clear()
                swap_status_var.set(
                    "💡 Yer değiştirmek için bir öğrenciye, ardından değiştirmek istediğiniz koltuğa tıklayın.")
                return

            onceki_ad_soyad = selection['ad_soyad']
            swap_seats(selection['op_id'], selection['sira'], selection['sutun_no'],
                       op_id, sira, sutun_no)
            self.log_activity("Oturma planında yer değiştirildi",
                               f"{derslik_data[1]}: {onceki_ad_soyad} <-> {ad_soyad}")
            selection.clear()
            swap_status_var.set(f"✅ {onceki_ad_soyad} ile {ad_soyad} yer değiştirdi.")
            draw_seats(canvas_widget, derslik_data)

        def draw_seats(canvas_widget, derslik_data):
            """Koltuk ızgarasını güncel verilerle yeniden çizer."""
            derslik_adi = derslik_data[1]
            enine = derslik_data[2]
            boyuna = derslik_data[3]
            sira_yapi = derslik_data[4]
            sinav_programi_id = derslik_data[5]

            oturma_docs = list(self.db.oturma_plani.find({'sinav_id': sinav_programi_id}))
            ogrenci_ids = list({o['ogrenci_id'] for o in oturma_docs})
            ogrenci_map = {o['_id']: o for o in self.db.ogrenciler.find({'_id': {'$in': ogrenci_ids}})}

            oturma_verileri = []
            for op in oturma_docs:
                ogrenci = ogrenci_map.get(op['ogrenci_id'])
                if not ogrenci:
                    continue
                oturma_verileri.append((op['_id'], op['sira_no'], op['sutun_no'],
                                         ogrenci['ogrenci_no'], ogrenci['ad_soyad']))
            oturma_verileri.sort(key=lambda r: (r[1], r[2]))

            oturma_dict = defaultdict(list)
            for op_id, sira, sanal_sutun, ogr_no, ad_soyad in oturma_verileri:
                kutu_sutun = sanal_sutun // 10
                koltuk_no = sanal_sutun % 10
                oturma_dict[(sira, kutu_sutun)].append((koltuk_no, op_id, ogr_no, ad_soyad))

            canvas_widget.delete("all")

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
                        is_empty_seat = is_seat_empty(koltuk_no, sira_yapi)

                        student_data = None
                        if anahtar_koordinat in oturma_dict:
                            for k_no, op_id, ogr_no, ad_soyad in oturma_dict[anahtar_koordinat]:
                                if k_no == koltuk_no:
                                    student_data = (op_id, ogr_no, ad_soyad)
                                    break

                        if is_empty_seat:
                            color = "#ecf0f1"
                            canvas_widget.create_rectangle(x1, y1, x2, y2, fill=color, outline="#bdc3c7", width=1)
                            canvas_widget.create_text((x1+x2)/2, (y1+y2)/2,
                                                     text="BOŞ", font=("Arial", 9), fill="#95a5a6")
                        elif student_data:
                            op_id, ogr_no, ad_soyad = student_data
                            cell_tag = f"seat_op_{op_id}"
                            color = "#27ae60"
                            canvas_widget.create_rectangle(x1, y1, x2, y2, fill=color, outline="black",
                                                           width=2, tags=(cell_tag,))

                            isim_parcalari = ad_soyad.split()
                            if len(isim_parcalari) >= 2:
                                isim = isim_parcalari[0]
                                soyisim = ' '.join(isim_parcalari[1:])
                            else:
                                isim = ad_soyad
                                soyisim = ""

                            canvas_widget.create_text((x1+x2)/2, y1 + 20,
                                                     text=isim[:12], tags=(cell_tag,),
                                                     font=("Arial", 9, "bold"), fill="white")

                            if soyisim:
                                canvas_widget.create_text((x1+x2)/2, y1 + 38,
                                                         text=soyisim[:12], tags=(cell_tag,),
                                                         font=("Arial", 8), fill="white")

                            canvas_widget.create_text((x1+x2)/2, y1 + 60,
                                                     text=ogr_no, tags=(cell_tag,),
                                                     font=("Arial", 7), fill="white")

                            # Numaralandırma 1'den başlıyor.
                            sutun_no = (kutu_sutun + 1) * 10 + koltuk_no
                            canvas_widget.tag_bind(
                                cell_tag, "<Button-1>",
                                lambda e, oid=op_id, ad=ad_soyad, s=sira + 1, sut=sutun_no,
                                       spid=sinav_programi_id, cw=canvas_widget, dd=derslik_data:
                                    on_seat_click(oid, ad, s, sut, spid, cw, dd))
                            canvas_widget.tag_bind(cell_tag, "<Enter>",
                                                   lambda e, cw=canvas_widget: cw.config(cursor="hand2"))
                            canvas_widget.tag_bind(cell_tag, "<Leave>",
                                                   lambda e, cw=canvas_widget: cw.config(cursor=""))
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

        for derslik_data in tum_derslikler:
            derslik_adi = derslik_data[1]
            enine = derslik_data[2]
            boyuna = derslik_data[3]
            sira_yapi = derslik_data[4]

            tab_frame = tk.Frame(notebook)
            notebook.add(tab_frame, text=derslik_adi)

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

            draw_seats(canvas_widget, derslik_data)


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

        sinav_programi_ids = [d[5] for d in tum_derslikler]

        def send_notifications():
            self.send_seating_notifications(sinav_programi_ids, ders_kodu, ders_adi,
                                             sinav_tarihi, sinav_saati)

        tk.Button(btn_frame, text="📧 Bildirim Gönder", font=("Arial", 11),
                  bg="#27ae60", fg="white",
                  command=send_notifications).pack(side=tk.LEFT, padx=5)

    def send_seating_notifications(self, sinav_programi_ids, ders_kodu, ders_adi,
                                    sinav_tarihi, sinav_saati):
        """E-postası kayıtlı öğrencilere sınav yeri/saati bilgisini gönderir."""
        if not smtp_configured():
            messagebox.showerror(
                "SMTP Yapılandırılmamış",
                "E-posta göndermek için SMTP_HOST, SMTP_USER ve SMTP_PASSWORD "
                "ortam değişkenlerini ayarlamanız gerekiyor.\n\n"
                "Ayrıntılar için README'ye bakın."
            )
            return

        oturma_docs = list(self.db.oturma_plani.find({'sinav_id': {'$in': sinav_programi_ids}}))
        ogrenci_ids = list({o['ogrenci_id'] for o in oturma_docs})
        derslik_ids = list({o['derslik_id'] for o in oturma_docs if o.get('derslik_id') is not None})
        ogrenci_map = {o['_id']: o for o in self.db.ogrenciler.find({'_id': {'$in': ogrenci_ids}})}
        derslik_map = {d['_id']: d for d in self.db.derslikler.find({'_id': {'$in': derslik_ids}})}

        alicilar_set = set()
        for op in oturma_docs:
            ogrenci = ogrenci_map.get(op['ogrenci_id'])
            derslik = derslik_map.get(op.get('derslik_id'))
            if not ogrenci or not derslik:
                continue
            email = ogrenci.get('email')
            if not email:
                continue
            alicilar_set.add((email, ogrenci['ad_soyad'], derslik['derslik_adi'], op['sira_no'], op['sutun_no']))

        alicilar = list(alicilar_set)

        if not alicilar:
            messagebox.showinfo(
                "Bilgi",
                "Bu sınava yerleştirilmiş, e-posta adresi kayıtlı öğrenci bulunamadı."
            )
            return

        if not messagebox.askyesno(
                "Onay",
                f"{len(alicilar)} öğrenciye sınav bilgilendirme e-postası gönderilecek. Devam edilsin mi?"):
            return

        total = len(alicilar)

        def worker(progress_callback):
            basarili = 0
            hatali = []
            for i, (email, ad_soyad, derslik_adi, sira_no, sutun_no) in enumerate(alicilar):
                subject = f"Sınav Bilgilendirmesi: {ders_kodu} - {ders_adi}"
                body = (
                    f"Sayın {ad_soyad},\n\n"
                    f"{ders_kodu} - {ders_adi} dersi sınavınıza ait yer bilgisi:\n\n"
                    f"Tarih: {sinav_tarihi}\n"
                    f"Saat: {sinav_saati}\n"
                    f"Derslik: {derslik_adi}\n"
                    f"Sıra: {sira_no}\n\n"
                    f"Bu e-posta Sınav Takvimi Yönetim Sistemi tarafından otomatik gönderilmiştir."
                )
                try:
                    send_email(email, subject, body)
                    basarili += 1
                except Exception as e:
                    hatali.append(f"{email}: {e}")
                progress_callback(i + 1, total, f"{i + 1}/{total} e-posta gönderiliyor...")

            message = f"✅ {basarili}/{total} e-posta başarıyla gönderildi."
            if hatali:
                message += f"\n\n⚠️ {len(hatali)} e-posta gönderilemedi:\n" + "\n".join(hatali[:5])
                if len(hatali) > 5:
                    message += f"\n... ve {len(hatali)-5} hata daha"
            self.log_activity("Sınav bildirimi e-postası gönderildi",
                               f"{ders_kodu}: {basarili}/{total} başarılı")
            return message

        self.run_background_task("Bildirimler Gönderiliyor", worker)

    def show_seating_list(self, sinav_id):
        """Oturma planını liste halinde göster"""
        list_window = tk.Toplevel(self.root)
        list_window.title("Oturma Planı - Liste Görünümü")
        list_window.geometry("700x600")

        sp = self.db.sinav_programi.find_one({'_id': sinav_id})
        ders = self.db.dersler.find_one({'_id': sp['ders_id']})
        derslik = self.db.derslikler.find_one({'_id': sp['derslik_id']})

        tk.Label(list_window,
                 text=f"{ders['ders_kodu']} - {ders['ders_adi']}\nDerslik: {derslik['derslik_adi']}",
                 font=("Arial", 12, "bold")).pack(pady=10)

        search_frame = tk.Frame(list_window)
        search_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        tk.Label(search_frame, text="Ara (Öğrenci No / Ad Soyad):",
                 font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 8))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=35)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        search_entry.focus_set()

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

        oturma_docs = list(self.db.oturma_plani.find({'sinav_id': sinav_id}))
        ogrenci_ids = list({o['ogrenci_id'] for o in oturma_docs})
        ogrenci_map = {o['_id']: o for o in self.db.ogrenciler.find({'_id': {'$in': ogrenci_ids}})}
        all_rows = []
        for op in oturma_docs:
            ogrenci = ogrenci_map.get(op['ogrenci_id'])
            if not ogrenci:
                continue
            all_rows.append((op['sira_no'], op['sutun_no'], ogrenci['ogrenci_no'], ogrenci['ad_soyad']))
        all_rows.sort(key=lambda r: (r[0], r[1]))

        def populate(filter_text=""):
            tree.delete(*tree.get_children())
            needle = filter_text.strip().lower()
            for row in all_rows:
                if not needle or needle in str(row[2]).lower() or needle in str(row[3]).lower():
                    tree.insert("", tk.END, values=row)

        populate()
        tree.pack(fill=tk.BOTH, expand=True)

        # Arama, veritabanına gitmeden yerel listeden yapılıyor.
        search_var.trace_add("write", lambda *_: populate(search_var.get()))


        def export_to_excel():
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialfile=f"oturma_plani_{ders['ders_kodu']}.xlsx"
            )

            if file_path:
                df = pd.DataFrame(all_rows,
                                  columns=["Sıra No", "Sütun No", "Öğrenci No", "Ad Soyad"])
                df.to_excel(file_path, index=False)
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


                            is_empty_seat = is_seat_empty(koltuk_no, sira_yapi)


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
