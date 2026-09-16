"""MySQL bağlantısı, şema oluşturma/migrasyon ve varsayılan admin hesabı."""
import os
import hashlib

import mysql.connector
from mysql.connector import Error
from tkinter import messagebox


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
        self.create_tables()
        self.migrate_add_gozetmen_column()
        self.migrate_add_student_email_column()
        self.create_default_admin()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=os.environ.get('DB_HOST', 'localhost'),
                user=os.environ.get('DB_USER', 'root'),
                password=os.environ.get('DB_PASSWORD', ''),
                database=os.environ.get('DB_NAME', 'sinav_takvimi_db')
            )
            if self.connection.is_connected():
                print("Veritabanına başarıyla bağlanıldı")
        except Error as e:
            print(f"Hata: {e}")
            messagebox.showerror("Hata", f"Veritabanı bağlantı hatası: {e}")

    def create_tables(self):
        cursor = self.connection.cursor()

        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS kullanicilar (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            sifre VARCHAR(255) NOT NULL,
            rol VARCHAR(50) NOT NULL,
            bolum VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bolumler (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bolum_adi VARCHAR(100) UNIQUE NOT NULL
        )
        """)

       
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ogretim_gorevlileri (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bolum_adi VARCHAR(100) NOT NULL,
            sicil_no VARCHAR(50) NOT NULL,
            ad_soyad VARCHAR(200) NOT NULL,
            unvan VARCHAR(100),
            email VARCHAR(255),
            telefon VARCHAR(20),
            UNIQUE KEY unique_ogretim (bolum_adi, sicil_no)
        )
        """)

        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS derslikler (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bolum_adi VARCHAR(100) NOT NULL,
            derslik_kodu VARCHAR(50) NOT NULL,
            derslik_adi VARCHAR(100) NOT NULL,
            kapasite INT NOT NULL,
            enine_sira INT NOT NULL,
            boyuna_sira INT NOT NULL,
            sira_yapisi INT NOT NULL,
            UNIQUE KEY unique_derslik (bolum_adi, derslik_kodu)
        )
        """)

        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS dersler (
            id INT AUTO_INCREMENT PRIMARY KEY,
            bolum_adi VARCHAR(100) NOT NULL,
            ders_kodu VARCHAR(50) NOT NULL,
            ders_adi VARCHAR(200) NOT NULL,
            hoca_adi VARCHAR(200),
            ogretim_gorevlisi_id INT,
            sinif VARCHAR(50),
            ders_tipi VARCHAR(50),
            FOREIGN KEY (ogretim_gorevlisi_id) REFERENCES ogretim_gorevlileri(id) ON DELETE SET NULL,
            UNIQUE KEY unique_ders (bolum_adi, ders_kodu)
        )
        """)

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ogrenciler (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bolum_adi VARCHAR(100) NOT NULL,
                ogrenci_no VARCHAR(50) NOT NULL,
                ad_soyad VARCHAR(200) NOT NULL,
                sinif VARCHAR(50),
                UNIQUE KEY unique_ogrenci (bolum_adi, ogrenci_no)
            )
        """)

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ogrenci_ders (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ogrenci_id INT NOT NULL,
                ders_id INT NOT NULL,
                FOREIGN KEY (ogrenci_id) REFERENCES ogrenciler(id) ON DELETE CASCADE,
                FOREIGN KEY (ders_id) REFERENCES dersler(id) ON DELETE CASCADE,
                UNIQUE KEY unique_relation (ogrenci_id, ders_id)
            )
        """)

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sinav_programi (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bolum_adi VARCHAR(100) NOT NULL,
                ders_id INT NOT NULL,
                sinav_tarihi DATE NOT NULL,
                sinav_saati TIME NOT NULL,
                sinav_turu VARCHAR(50),
                sinav_suresi INT,
                derslik_id INT,
                atanan_ogrenci INT, -- Bu sütun eklenmeli
                FOREIGN KEY (ders_id) REFERENCES dersler(id) ON DELETE CASCADE,
                FOREIGN KEY (derslik_id) REFERENCES derslikler(id) ON DELETE SET NULL
            )
        """)

       
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS oturma_plani (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sinav_id INT NOT NULL,
                ogrenci_id INT NOT NULL,
                derslik_id INT NOT NULL,
                sira_no INT NOT NULL,
                sutun_no INT NOT NULL, -- Sanal sütun numarası (örn: 11, 13)
                FOREIGN KEY (sinav_id) REFERENCES sinav_programi(id) ON DELETE CASCADE,
                FOREIGN KEY (ogrenci_id) REFERENCES ogrenciler(id) ON DELETE CASCADE,
                FOREIGN KEY (derslik_id) REFERENCES derslikler(id) ON DELETE CASCADE
            )
        """)

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS istisnai_sinav_sureleri (
                id INT AUTO_INCREMENT PRIMARY KEY,
                bolum_adi VARCHAR(100) NOT NULL,
                ders_id INT NOT NULL,
                sinav_suresi INT NOT NULL,
                FOREIGN KEY (ders_id) REFERENCES dersler(id) ON DELETE CASCADE,
                UNIQUE KEY unique_ders_sure (bolum_adi, ders_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aktivite_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                kullanici VARCHAR(255),
                bolum_adi VARCHAR(100),
                islem VARCHAR(100) NOT NULL,
                detay VARCHAR(500),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


        bolumler = [
            'Bilgisayar Müh.',
            'Yazılım Müh.',
            'Elektrik Müh.',
            'Elektronik Müh.',
            'İnşaat Müh.'
        ]

        for bolum in bolumler:
            try:
                cursor.execute("INSERT INTO bolumler (bolum_adi) VALUES (%s)", (bolum,))
            except:
                pass

        self.connection.commit()
        cursor.close()

    def migrate_add_gozetmen_column(self):
        """sinav_programi tablosuna gözetmen (öğretim görevlisi) ataması için
        nullable bir FK kolonu ekler. Her ikisi de bağımsız olarak idempotenttir:
        kolon/kısıt zaten varsa MySQL hatası bastırılır, uygulama normal çalışmaya devam eder."""
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                ALTER TABLE sinav_programi ADD COLUMN gozetmen_id INT NULL
            """)
            self.connection.commit()
        except Error as e:
            self.connection.rollback()
            if e.errno != 1060:  # 1060: Duplicate column name (beklenen/normal durum)
                print(f"Uyarı: gozetmen_id kolonu eklenemedi: {e}")

        try:
            cursor.execute("""
                ALTER TABLE sinav_programi
                ADD CONSTRAINT fk_sinav_gozetmen
                FOREIGN KEY (gozetmen_id) REFERENCES ogretim_gorevlileri(id) ON DELETE SET NULL
            """)
            self.connection.commit()
        except Error as e:
            self.connection.rollback()
            if e.errno != 1061:  # 1061: Duplicate key name (beklenen/normal durum)
                print(f"Uyarı: fk_sinav_gozetmen kısıtı eklenemedi: {e}")

        cursor.close()

    def migrate_add_student_email_column(self):
        """ogrenciler tablosuna, sınav bildirimi e-postaları gönderebilmek için
        nullable bir email kolonu ekler (idempotent)."""
        cursor = self.connection.cursor()
        try:
            cursor.execute("""
                ALTER TABLE ogrenciler ADD COLUMN email VARCHAR(255) NULL
            """)
            self.connection.commit()
        except Error as e:
            self.connection.rollback()
            if e.errno != 1060:  # 1060: Duplicate column name (beklenen/normal durum)
                print(f"Uyarı: ogrenciler.email kolonu eklenemedi: {e}")
        cursor.close()

    def create_default_admin(self):
        if 'ADMIN_EMAIL' not in os.environ or 'ADMIN_PASSWORD' not in os.environ:
            print("Uyarı: ADMIN_EMAIL / ADMIN_PASSWORD ortam değişkenleri ayarlanmamış, "
                  "varsayılan admin bilgileri kullanılacak (admin@kocaeli.edu.tr / admin123). "
                  "Giriş yaptıktan sonra şifrenizi değiştirmeniz önerilir.")

        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@kocaeli.edu.tr')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')

        cursor = self.connection.cursor()
        # Not: burada bilinçli olarak eski (salt'sız SHA256) formatta hashleniyor,
        # böylece verify_password()'daki geriye dönük uyumluluk yolu her kurulumun
        # ilk admin girişinde otomatik olarak çalışıp test edilmiş olur.
        hashed_pass = hashlib.sha256(admin_password.encode()).hexdigest()
        try:
            cursor.execute("""
                INSERT INTO kullanicilar (email, sifre, rol, bolum)
                VALUES (%s, %s, %s, %s)
            """, (admin_email, hashed_pass, "Admin", None))
            self.connection.commit()
        except:
            pass
        cursor.close()
