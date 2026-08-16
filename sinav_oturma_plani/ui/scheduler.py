"""Sınav programı oluşturma (otomatik yerleştirme algoritması dahil),
Excel'e aktarım ve çakışma raporu."""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import pandas as pd


class SchedulerMixin:
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

        dersler = [(d['_id'], d['ders_kodu'], d['ders_adi'], d['sinif'])
                   for d in self.db.dersler.find({'bolum_adi': self.current_bolum})
                   .sort([('sinif', 1), ('ders_kodu', 1)])]

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


                derslikler = [(d['_id'], d['derslik_adi'], d['kapasite'])
                              for d in self.db.derslikler.find({'bolum_adi': self.current_bolum})
                              .sort('kapasite', -1)]

                if not derslikler:
                    messagebox.showerror("Hata", "Sistemde derslik bulunamadı!")
                    return


                self.db.istisnai_sinav_sureleri.delete_many({'bolum_adi': self.current_bolum})
                if istisnai_sureler:
                    self.db.istisnai_sinav_sureleri.insert_many([
                        {'bolum_adi': self.current_bolum, 'ders_id': ders_id, 'sinav_suresi': sure}
                        for ders_id, sure in istisnai_sureler.items()
                    ])


                result = self.optimized_exam_scheduler(
                    secili_dersler, tarihler, derslikler,
                    sinav_suresi_default, istisnai_sureler,
                    bekleme_suresi, sinav_turu, ayni_zaman
                )

                if result['success']:

                    self.db.sinav_programi.delete_many({'bolum_adi': self.current_bolum})
                    if result['records']:
                        self.db.sinav_programi.insert_many(result['records'])
                    self.log_activity("Sınav programı oluşturuldu",
                                       f"{sinav_turu}, {len(secili_dersler)} ders, "
                                       f"{baslangic_str}-{bitis_str}")
                    messagebox.showinfo("Başarılı", result['message'])
                    self.export_schedule_to_excel()
                else:
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
                                 bekleme_suresi, sinav_turu, ayni_zaman):


        ders_docs = list(self.db.dersler.find({'_id': {'$in': secili_dersler}})
                          .sort([('sinif', 1), ('ders_kodu', 1)]))
        tum_dersler = [(d['_id'], d['ders_kodu'], d['ders_adi'], d['sinif']) for d in ders_docs]


        enrollment_docs = list(self.db.ogrenci_ders.find(
            {'ders_id': {'$in': secili_dersler}}, {'ders_id': 1, 'ogrenci_id': 1}))
        ders_ogrenci_sayilari = Counter(e['ders_id'] for e in enrollment_docs)


        bolum_ders_ids = {d['_id'] for d in self.db.dersler.find(
            {'_id': {'$in': secili_dersler}, 'bolum_adi': self.current_bolum}, {'_id': 1})}

        ogrenci_dersler = defaultdict(set)
        for e in enrollment_docs:
            if e['ders_id'] in bolum_ders_ids:
                ogrenci_dersler[e['ogrenci_id']].add(e['ders_id'])


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
                                'bolum_adi': self.current_bolum,
                                'ders_id': ders_id,
                                'sinav_tarihi': tarih,
                                'sinav_saati': sinav_baslangic.time().strftime('%H:%M:%S'),
                                'sinav_turu': sinav_turu,
                                'sinav_suresi': sinav_suresi,
                                'derslik_id': derslik_id,
                            })

                        yerlestirildi = True
                        break

                    if not yerlestirildi:
                        hata_mesajlari.append(
                            f"❌ {ders[1]} - {ders[2]} ({ders[3]}. sınıf) {tarih.strftime('%d.%m.%Y')} gününe yerleştirilemedi! (Kapasite/Zaman Dolu)"
                        )


        if hata_mesajlari:
            return {
                'success': len(sinav_programi) > 0,
                'message': f"{len(sinav_programi)} sınav oluşturuldu.\n\n⚠️ HATALAR:\n" + "\n".join(hata_mesajlari[:5]),
                'records': sinav_programi,
            }
        else:
            return {
                'success': True,
                'message': f"✅ Başarılı!\n{len(sinav_programi)} sınav kaydı oluşturuldu.",
                'records': sinav_programi,
            }


    def export_schedule_to_excel(self):
        if not self.current_bolum:
            return

        sp_docs = list(self.db.sinav_programi.find({'bolum_adi': self.current_bolum}))

        if not sp_docs:
            messagebox.showinfo("Bilgi", "Henüz sınav programı oluşturulmamış!")
            return

        ders_ids = list({sp['ders_id'] for sp in sp_docs})
        derslik_ids = list({sp['derslik_id'] for sp in sp_docs if sp.get('derslik_id') is not None})

        ders_map = {d['_id']: d for d in self.db.dersler.find({'_id': {'$in': ders_ids}})}
        derslik_map = {d['_id']: d for d in self.db.derslikler.find({'_id': {'$in': derslik_ids}})}

        results = []
        for sp in sp_docs:
            ders = ders_map.get(sp['ders_id'])
            derslik = derslik_map.get(sp.get('derslik_id'))
            if not ders or not derslik:
                continue
            results.append((sp['sinav_tarihi'], sp['sinav_saati'], ders['ders_adi'],
                             ders.get('hoca_adi'), derslik['derslik_adi'], sp['sinav_turu'],
                             sp['sinav_suresi'], sp['ders_id']))

        results.sort(key=lambda r: (r[0], r[1], r[2]))

        if not results:
            messagebox.showinfo("Bilgi", "Henüz sınav programı oluşturulmamış!")
            return


        ders_id_to_ogrenci_sayilari = {}
        ders_ids2 = list({r[7] for r in results})


        if ders_ids2:
            enroll_docs = list(self.db.ogrenci_ders.find(
                {'ders_id': {'$in': ders_ids2}}, {'ders_id': 1}))
            ders_id_to_ogrenci_sayilari = dict(Counter(e['ders_id'] for e in enroll_docs))

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


    def show_exam_conflicts(self):
        """Kayıtlı programı öğrenci bazında denetleyen salt-okunur çakışma raporu."""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        sp_docs = list(self.db.sinav_programi.find({'bolum_adi': self.current_bolum}))

        if not sp_docs:
            messagebox.showinfo("Bilgi", "Henüz sınav programı oluşturulmamış!")
            return

        ders_ids = list({sp['ders_id'] for sp in sp_docs})
        ders_map = {d['_id']: d for d in self.db.dersler.find({'_id': {'$in': ders_ids}})}

        enrollment_docs = list(self.db.ogrenci_ders.find({'ders_id': {'$in': ders_ids}}))
        ders_to_ogrenciler = defaultdict(list)
        for e in enrollment_docs:
            ders_to_ogrenciler[e['ders_id']].append(e['ogrenci_id'])

        ogrenci_ids = list({e['ogrenci_id'] for e in enrollment_docs})
        ogrenci_map = {o['_id']: o for o in self.db.ogrenciler.find({'_id': {'$in': ogrenci_ids}})}

        ogrenci_sinavlari = defaultdict(list)
        for sp in sp_docs:
            ders = ders_map.get(sp['ders_id'])
            if not ders:
                continue
            # sinav_saati "HH:MM:SS" string olarak saklanıyor (bkz. optimized_exam_scheduler)
            saat_time = datetime.strptime(sp['sinav_saati'], '%H:%M:%S').time()
            baslangic = datetime.combine(sp['sinav_tarihi'].date(), saat_time)
            bitis = baslangic + timedelta(minutes=sp.get('sinav_suresi') or 0)
            for ogrenci_id in ders_to_ogrenciler.get(sp['ders_id'], []):
                ogrenci = ogrenci_map.get(ogrenci_id)
                if not ogrenci:
                    continue
                ogrenci_sinavlari[ogrenci_id].append({
                    'ad_soyad': ogrenci['ad_soyad'], 'ogrenci_no': ogrenci['ogrenci_no'],
                    'ders': f"{ders['ders_kodu']} - {ders['ders_adi']}",
                    'baslangic': baslangic, 'bitis': bitis
                })

        cakismalar = []
        for ogrenci_id in sorted(ogrenci_sinavlari, key=lambda oid: ogrenci_map[oid]['ogrenci_no']):
            sinavlar = ogrenci_sinavlari[ogrenci_id]
            sinavlar_sorted = sorted(sinavlar, key=lambda s: s['baslangic'])
            for i in range(len(sinavlar_sorted) - 1):
                a = sinavlar_sorted[i]
                b = sinavlar_sorted[i + 1]
                if a['baslangic'].date() == b['baslangic'].date() and b['baslangic'] < a['bitis']:
                    cakismalar.append((a, b))

        window = tk.Toplevel(self.root)
        window.title("Çakışma Raporu")
        window.geometry("800x550")

        tk.Label(window, text="Öğrenci Sınav Çakışma Raporu",
                 font=("Arial", 14, "bold")).pack(pady=10)

        if not cakismalar:
            tk.Label(window, text="✅ Herhangi bir öğrenci için çakışma tespit edilmedi.",
                     font=("Arial", 12), fg="#27ae60").pack(pady=30)
            return

        tk.Label(window,
                 text=f"⚠️ {len(cakismalar)} çakışma tespit edildi (aynı gün, üst üste binen sınavlar):",
                 font=("Arial", 11, "bold"), fg="#e74c3c").pack(pady=(0, 10))

        list_frame = tk.Frame(window)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        columns = ("Öğrenci No", "Ad Soyad", "Sınav 1", "Sınav 2", "Tarih")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=140)
        tree.pack(fill=tk.BOTH, expand=True)

        for a, b in cakismalar:
            tree.insert("", tk.END, values=(
                a['ogrenci_no'], a['ad_soyad'],
                f"{a['ders']} ({a['baslangic'].strftime('%H:%M')}-{a['bitis'].strftime('%H:%M')})",
                f"{b['ders']} ({b['baslangic'].strftime('%H:%M')}-{b['bitis'].strftime('%H:%M')})",
                a['baslangic'].strftime('%d.%m.%Y')
            ))

    def show_exam_calendar(self):
        """Tüm sınav programını derslik x zaman ızgarası olarak gösterir."""
        if not self.current_bolum:
            messagebox.showerror("Hata", "Önce bir bölüm seçin!")
            return

        sp_docs = list(self.db.sinav_programi.find({'bolum_adi': self.current_bolum}))

        if not sp_docs:
            messagebox.showinfo("Bilgi", "Henüz sınav programı oluşturulmamış!")
            return

        ders_ids = list({sp['ders_id'] for sp in sp_docs})
        derslik_ids = list({sp['derslik_id'] for sp in sp_docs if sp.get('derslik_id') is not None})
        ders_map = {d['_id']: d for d in self.db.dersler.find({'_id': {'$in': ders_ids}})}
        derslik_map = {d['_id']: d for d in self.db.derslikler.find({'_id': {'$in': derslik_ids}})}

        rows = []
        for sp in sp_docs:
            ders = ders_map.get(sp['ders_id'])
            derslik = derslik_map.get(sp.get('derslik_id'))
            if not ders or not derslik:
                continue
            rows.append((sp['sinav_tarihi'], sp['sinav_saati'], derslik['derslik_adi'], ders['ders_kodu']))

        rows.sort(key=lambda r: (r[0], r[1], r[2]))

        if not rows:
            messagebox.showinfo("Bilgi", "Henüz sınav programı oluşturulmamış!")
            return

        derslikler_sorted = sorted({r[2] for r in rows})
        zaman_dilimleri = sorted({(r[0], r[1]) for r in rows})
        hucre = {(tarih, saat, derslik_adi): ders_kodu for tarih, saat, derslik_adi, ders_kodu in rows}

        window = tk.Toplevel(self.root)
        window.title("Sınav Takvimi - Genel Görünüm")
        window.geometry("1100x650")

        tk.Label(window, text="Sınav Takvimi (Derslik x Zaman)",
                 font=("Segoe UI", 14, "bold")).pack(pady=10)

        tree_frame = tk.Frame(window)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        v_scroll = tk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scroll = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)

        columns = ["Tarih / Saat"] + derslikler_sorted
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                            yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        v_scroll.config(command=tree.yview)
        h_scroll.config(command=tree.xview)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        tree.pack(fill=tk.BOTH, expand=True)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=160 if col == "Tarih / Saat" else 130, anchor="center")

        for tarih, saat in zaman_dilimleri:
            row_values = [f"{tarih} {saat}"]
            for derslik_adi in derslikler_sorted:
                row_values.append(hucre.get((tarih, saat, derslik_adi), ""))
            tree.insert("", tk.END, values=row_values)
