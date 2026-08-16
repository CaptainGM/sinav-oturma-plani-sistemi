# Görsel Değiştirme

Bu klasöre aşağıdaki dosyalardan birini/ikisini koyarsanız, uygulama kod
değişikliği gerektirmeden otomatik olarak bunları kullanır. Dosya yoksa
programatik üretilen varsayılan görsel kullanılır.

| Dosya adı                | Boyut (önerilen) | Açıklama |
|--------------------------|-------------------|----------|
| `login_background.png`   | 1200 x 700 px     | Giriş ve kayıt ekranlarının arka planı. Farklı bir en-boy oranında bir görsel koyarsanız, oranı bozulmadan ortadan kırpılarak (CSS `background-size: cover` gibi) yerleştirilir. `.jpg`/`.jpeg` da desteklenir. |
| `panel_background.png`    | 1600 x 1000 px    | Ana panelde içeriğin altında kalan dekoratif alan. Üst kenarı panel zemin rengiyle (`#ecf0f1`) uyumlu bir görsel seçmek, içerikle arasında görünür bir sınır oluşmasını engeller. |
| `app_icon.png`            | 512 x 512 px, kare | Uygulama/pencere ikonu ve giriş ekranındaki logo. Şeffaf arka plan (PNG alpha kanalı) önerilir. |
