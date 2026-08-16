"""Kaskad silme yardımcıları.

MongoDB'de foreign key olmadığı için, bir kayıt silinirken ona referans veren
belgeler burada açıkça temizlenir ya da ilgili alanları None'lanır. Silme
işlemi yapan her ekran tek çağrı noktası olarak bu fonksiyonları kullanır.

`bolumler` hiçbir koleksiyondan referans almaz (bolum_adi her yerde düz metin
olarak tutulur), bu yüzden ayrı bir kaskad fonksiyonu yoktur."""


def delete_student(db, ogrenci_id):
    db.ogrenci_ders.delete_many({'ogrenci_id': ogrenci_id})
    db.oturma_plani.delete_many({'ogrenci_id': ogrenci_id})
    db.ogrenciler.delete_one({'_id': ogrenci_id})


def delete_course(db, ders_id):
    db.ogrenci_ders.delete_many({'ders_id': ders_id})
    db.istisnai_sinav_sureleri.delete_many({'ders_id': ders_id})

    sinav_ids = [s['_id'] for s in db.sinav_programi.find({'ders_id': ders_id}, {'_id': 1})]
    if sinav_ids:
        db.oturma_plani.delete_many({'sinav_id': {'$in': sinav_ids}})
    db.sinav_programi.delete_many({'ders_id': ders_id})

    db.dersler.delete_one({'_id': ders_id})


def delete_classroom(db, derslik_id):
    db.sinav_programi.update_many({'derslik_id': derslik_id}, {'$set': {'derslik_id': None}})
    db.oturma_plani.delete_many({'derslik_id': derslik_id})
    db.derslikler.delete_one({'_id': derslik_id})


def delete_instructor(db, ogretim_gorevlisi_id):
    db.dersler.update_many({'ogretim_gorevlisi_id': ogretim_gorevlisi_id},
                            {'$set': {'ogretim_gorevlisi_id': None}})
    db.sinav_programi.update_many({'gozetmen_id': ogretim_gorevlisi_id},
                                   {'$set': {'gozetmen_id': None}})
    db.ogretim_gorevlileri.delete_one({'_id': ogretim_gorevlisi_id})


def delete_exam_row(db, sinav_id):
    db.oturma_plani.delete_many({'sinav_id': sinav_id})
    db.sinav_programi.delete_one({'_id': sinav_id})


def delete_exam_rows(db, sinav_ids):
    if not sinav_ids:
        return
    db.oturma_plani.delete_many({'sinav_id': {'$in': list(sinav_ids)}})
    db.sinav_programi.delete_many({'_id': {'$in': list(sinav_ids)}})
