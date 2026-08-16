"""MongoDB bağlantısı, koleksiyon/index kurulumu ve varsayılan admin hesabı."""
import hashlib
import os
from tkinter import messagebox

from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError


class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()
        self.create_collections_and_indexes()
        self.create_default_admin()

    def connect(self):
        try:
            uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017')
            db_name = os.environ.get('MONGO_DB_NAME', 'sinav_takvimi_db')
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[db_name]

            self.kullanicilar = self.db['kullanicilar']
            self.bolumler = self.db['bolumler']
            self.ogretim_gorevlileri = self.db['ogretim_gorevlileri']
            self.derslikler = self.db['derslikler']
            self.dersler = self.db['dersler']
            self.ogrenciler = self.db['ogrenciler']
            self.ogrenci_ders = self.db['ogrenci_ders']
            self.sinav_programi = self.db['sinav_programi']
            self.oturma_plani = self.db['oturma_plani']
            self.istisnai_sinav_sureleri = self.db['istisnai_sinav_sureleri']
            self.aktivite_log = self.db['aktivite_log']

            print("Veritabanına başarıyla bağlanıldı")
        except PyMongoError as e:
            print(f"Hata: {e}")
            messagebox.showerror("Hata", f"Veritabanı bağlantı hatası: {e}")

    def create_collections_and_indexes(self):
        """Unique index'leri ve varsayılan bölümleri kurar. Tekrar çağrılması zararsızdır."""
        self.kullanicilar.create_index([('email', ASCENDING)], unique=True)
        self.bolumler.create_index([('bolum_adi', ASCENDING)], unique=True)
        self.ogretim_gorevlileri.create_index(
            [('bolum_adi', ASCENDING), ('sicil_no', ASCENDING)], unique=True)
        self.derslikler.create_index(
            [('bolum_adi', ASCENDING), ('derslik_kodu', ASCENDING)], unique=True)
        self.dersler.create_index(
            [('bolum_adi', ASCENDING), ('ders_kodu', ASCENDING)], unique=True)
        self.ogrenciler.create_index(
            [('bolum_adi', ASCENDING), ('ogrenci_no', ASCENDING)], unique=True)
        self.ogrenci_ders.create_index(
            [('ogrenci_id', ASCENDING), ('ders_id', ASCENDING)], unique=True)
        self.istisnai_sinav_sureleri.create_index(
            [('bolum_adi', ASCENDING), ('ders_id', ASCENDING)], unique=True)

        varsayilan_bolumler = [
            'Bilgisayar Müh.',
            'Yazılım Müh.',
            'Elektrik Müh.',
            'Elektronik Müh.',
            'İnşaat Müh.',
        ]
        for bolum in varsayilan_bolumler:
            try:
                self.bolumler.insert_one({'bolum_adi': bolum})
            except DuplicateKeyError:
                pass

    def create_default_admin(self):
        if 'ADMIN_EMAIL' not in os.environ or 'ADMIN_PASSWORD' not in os.environ:
            print("Uyarı: ADMIN_EMAIL / ADMIN_PASSWORD ortam değişkenleri ayarlanmamış, "
                  "varsayılan admin bilgileri kullanılacak (admin@kocaeli.edu.tr / admin123). "
                  "Giriş yaptıktan sonra şifrenizi değiştirmeniz önerilir.")

        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@kocaeli.edu.tr')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')

        # Eski SHA256 formatında yazılır; ilk girişte bcrypt'e yükseltilir.
        hashed_pass = hashlib.sha256(admin_password.encode()).hexdigest()
        try:
            self.kullanicilar.insert_one({
                'email': admin_email,
                'sifre': hashed_pass,
                'rol': 'Admin',
                'bolum': None,
            })
        except DuplicateKeyError:
            pass
