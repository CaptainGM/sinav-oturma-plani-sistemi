# Görseller

## Pakete dahil olanlar

| Dosya | Kaynak |
|-------|--------|
| `login_background.jpg` | [Unsplash](https://unsplash.com/photos/empty-lecture-hall-with-rows-of-seats-I8PUo5Xk8DU) — boş amfi. Uygulamanın paletine göre koyulaştırılıp renklendirildi. |
| `panel_background.jpg` | [Unsplash](https://unsplash.com/photos/students-attentively-taking-notes-in-a-lecture-hall-NKr9f2t8Lgk) — derste not alan öğrenciler. Panelde içeriğin altında kalması için açıklaştırıldı. |

Her iki görsel de [Unsplash Lisansı](https://unsplash.com/license) ile
dağıtılıyor: ticari kullanım dahil ücretsiz, atıf zorunlu değil.

## Kendi görselinizi koymak

Aşağıdaki dosyalardan birini bu klasöre koyarsanız, uygulama kod değişikliği
gerektirmeden onu kullanır. Dosya yoksa programatik üretilen desen devreye girer.

| Dosya adı                | Boyut (önerilen) | Açıklama |
|--------------------------|-------------------|----------|
| `login_background.png`   | 1200 x 700 px     | Giriş ve kayıt ekranlarının arka planı. Farklı bir en-boy oranında bir görsel koyarsanız, oranı bozulmadan ortadan kırpılarak (CSS `background-size: cover` gibi) yerleştirilir. `.jpg`/`.jpeg` da desteklenir. |
| `panel_background.png`    | 1600 x 1000 px    | Ana panelde içeriğin altında kalan dekoratif alan. Üst kenarı panel zemin rengiyle (`#ecf0f1`) uyumlu bir görsel seçmek, içerikle arasında görünür bir sınır oluşmasını engeller. |
| `app_icon.png`            | 512 x 512 px, kare | Uygulama/pencere ikonu ve giriş ekranındaki logo. Şeffaf arka plan (PNG alpha kanalı) önerilir. |
