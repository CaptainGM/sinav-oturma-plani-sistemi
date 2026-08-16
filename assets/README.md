# Görsel Değiştirme

Bu klasöre aşağıdaki dosyalardan birini/ikisini koyarsanız, uygulama kod
değişikliği gerektirmeden otomatik olarak bunları kullanır. Dosya yoksa
programatik üretilen varsayılan görsel kullanılır.

| Dosya adı                | Boyut (önerilen) | Açıklama |
|--------------------------|-------------------|----------|
| `login_background.png`   | 1200 x 700 px     | Giriş ekranının arka planı. Farklı bir en-boy oranında bir görsel koyarsanız, oranı bozulmadan ortadan kırpılarak (CSS `background-size: cover` gibi) yerleştirilir. `.jpg`/`.jpeg` da desteklenir. |
| `app_icon.png`            | 512 x 512 px, kare | Uygulama/pencere ikonu ve giriş ekranındaki logo. Şeffaf arka plan (PNG alpha kanalı) önerilir. |

Not: Şu an yalnızca **giriş ekranı** özel arka plan görseli destekliyor; ana
menü/dashboard gibi diğer ekranlar düz renk kullanıyor. Onlar için de görsel
arka plan istiyorsanız ayrıca belirtin, aynı mekanizma oraya da eklenebilir.
