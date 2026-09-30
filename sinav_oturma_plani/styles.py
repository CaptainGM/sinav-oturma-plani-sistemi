"""Renkler, ortak görünüm ayarları, buton/pencere tasarımı ve şifre işlemleri."""
import hashlib
import os
import tkinter as tk

import tkinter.font as tkfont

import bcrypt
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageTk

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS_DIR = os.path.join(_PROJECT_ROOT, 'assets')


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')


def is_bcrypt_hash(stored_hash):
    return (isinstance(stored_hash, str)
            and stored_hash.startswith(('$2a$', '$2b$', '$2y$'))
            and len(stored_hash) == 60)


def verify_password(password, stored_hash):
    """Girilen şifreyi kayıtlı şifreyle karşılaştırır. Eski hesaplarla da çalışır."""
    if is_bcrypt_hash(stored_hash):
        try:
            return bcrypt.checkpw(password.encode(), stored_hash.encode())
        except ValueError:
            return False
    return hashlib.sha256(password.encode()).hexdigest() == stored_hash


COLORS = {
    'bg_dark': '#1f2d3d',
    'bg_panel': '#2c3e50',
    'bg_light': '#ecf0f1',
    'bg_card': '#ffffff',
    'primary': '#3498db',
    'primary_dark': '#2980b9',
    'success': '#27ae60',
    'success_dark': '#219150',
    'danger': '#e74c3c',
    'warning': '#f39c12',
    'text_light': '#ffffff',
    'text_dark': '#2c3e50',
    'text_muted': '#7f8c8d',
    'border': '#d0d7de',
    'accent': '#3884f6',
    'accent_dark': '#2f6fd0',
}


def configure_styles(style):
    # Windows'un kendi temaları renk ayarlarını yok sayıyor, bu yüzden 'clam'.
    style.theme_use('clam')

    style.configure('TFrame', background=COLORS['bg_light'])
    style.configure('Card.TFrame', background=COLORS['bg_card'], relief='flat')
    style.configure('Dark.TFrame', background=COLORS['bg_panel'])

    style.configure('TLabel', background=COLORS['bg_light'], foreground=COLORS['text_dark'],
                     font=('Segoe UI', 10))
    style.configure('Card.TLabel', background=COLORS['bg_card'], foreground=COLORS['text_dark'],
                     font=('Segoe UI', 10))
    style.configure('Dark.TLabel', background=COLORS['bg_panel'], foreground=COLORS['text_light'],
                     font=('Segoe UI', 10))
    style.configure('Title.TLabel', background=COLORS['bg_panel'], foreground=COLORS['text_light'],
                     font=('Segoe UI', 22, 'bold'))
    style.configure('CardTitle.TLabel', background=COLORS['bg_card'], foreground=COLORS['text_muted'],
                     font=('Segoe UI', 10, 'bold'))
    style.configure('CardValue.TLabel', background=COLORS['bg_card'], foreground=COLORS['primary'],
                     font=('Segoe UI', 24, 'bold'))

    style.configure('TButton', font=('Segoe UI', 10), padding=6)
    style.configure('Accent.TButton', background=COLORS['accent'], foreground=COLORS['text_light'],
                     font=('Segoe UI', 11, 'bold'), padding=8)
    style.map('Accent.TButton', background=[('active', COLORS['accent_dark'])])
    style.configure('Primary.TButton', background=COLORS['primary'], foreground=COLORS['text_light'],
                     font=('Segoe UI', 10, 'bold'), padding=8)
    style.map('Primary.TButton', background=[('active', COLORS['primary_dark'])])

    style.configure('TEntry', padding=5)

    style.configure('Treeview', rowheight=26, font=('Segoe UI', 10))
    style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))


def apply_widget_defaults(root):
    """Bütün pencerelerin aynı zemin rengini kullanması için varsayılanları ayarlar."""
    for widget in ('Toplevel', 'Frame', 'Label', 'Labelframe',
                    'Checkbutton', 'Radiobutton'):
        root.option_add(f'*{widget}.background', COLORS['bg_light'])

    for widget in ('Label', 'Labelframe', 'Checkbutton', 'Radiobutton'):
        root.option_add(f'*{widget}.foreground', COLORS['text_dark'])

    for widget in ('Checkbutton', 'Radiobutton'):
        root.option_add(f'*{widget}.activeBackground', COLORS['bg_light'])
        root.option_add(f'*{widget}.activeForeground', COLORS['text_dark'])
        root.option_add(f'*{widget}.selectColor', COLORS['bg_card'])

    root.option_add('*Entry.background', COLORS['bg_card'])
    root.option_add('*Listbox.background', COLORS['bg_card'])


def _shade(rgb, amount):
    """Rengi açar (amount > 0) ya da koyulaştırır (amount < 0)."""
    if amount >= 0:
        return tuple(int(c + (255 - c) * amount) for c in rgb)
    return tuple(max(0, int(c * (1 + amount))) for c in rgb)


def _pill(width, height, rgb, radius, supersample=3):
    """Üstten alta hafif gradyanlı, yuvarlak köşeli buton gövdesi."""
    big = (width * supersample, height * supersample)
    gradient = _diagonal_gradient(big[0], big[1], _shade(rgb, 0.12), _shade(rgb, -0.08),
                                   angle_deg=90)

    mask = Image.new('L', big, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, big[0] - 1, big[1] - 1],
                                            radius=radius * supersample, fill=255)

    img = Image.new('RGBA', big, (0, 0, 0, 0))
    img.paste(gradient, (0, 0), mask)
    return img.resize((width, height), Image.LANCZOS)


class _RoundedButton(tk.Canvas):
    """Yuvarlak köşeli buton. tk.Button ile aynı şekilde kullanılır.

    Tkinter'ın kendi butonu yuvarlak köşe desteklemediği için zemin resim
    olarak çizilir."""

    RADIUS = 8
    _SWALLOWED = ('relief', 'bd', 'borderwidth', 'activebackground', 'activeforeground',
                   'highlightthickness', 'highlightbackground', 'anchor', 'justify',
                   'overrelief', 'default', 'takefocus')

    def __init__(self, master=None, text='', command=None, bg=None, fg=None,
                 font=None, padx=None, pady=None, width=None, height=None,
                 state='normal', cursor='hand2', **_legacy):
        self._text = text
        self._command = command
        self._fill = bg or COLORS['accent']
        self._fg = fg or COLORS['text_light']
        self._font = font or ('Segoe UI', 10, 'bold')
        self._padx = 24 if padx is None else max(int(padx), 14)
        self._pady = 11 if pady is None else max(int(pady), 8)
        self._min_chars = width
        self._min_lines = height
        self._state = state
        self._photo = None

        try:
            parent_bg = master.cget('background')
        except Exception:
            parent_bg = COLORS['bg_light']

        box = self._measure()
        super().__init__(master, width=box[0], height=box[1], highlightthickness=0,
                          bd=0, bg=parent_bg, cursor='' if state == 'disabled' else cursor)

        self._body = self.create_image(0, 0, anchor='nw')
        self._label = self.create_text(box[0] // 2, box[1] // 2, text=self._text,
                                        fill=self._fg, font=self._font)
        self._paint()

        self.bind('<Enter>', lambda _e: self._paint(hover=True))
        self.bind('<Leave>', lambda _e: self._paint())
        self.bind('<Button-1>', lambda _e: self._paint(press=True))
        self.bind('<ButtonRelease-1>', self._on_release)

    def _measure(self):
        font = tkfont.Font(font=self._font)
        line = font.metrics('linespace')
        width = font.measure(self._text) + self._padx * 2
        height = line + self._pady * 2
        if self._min_chars:
            width = max(width, int(self._min_chars) * font.measure('0') + self._padx * 2)
        if self._min_lines:
            height = max(height, int(self._min_lines) * line + self._pady)
        return int(width), int(height)

    def _rgb(self, color):
        if isinstance(color, str) and color.startswith('#') and len(color) == 7:
            return hex_to_rgb(color)
        try:
            return tuple(c >> 8 for c in self.winfo_rgb(color))
        except tk.TclError:
            return hex_to_rgb(COLORS['accent'])

    def _paint(self, hover=False, press=False):
        width, height = int(self['width']), int(self['height'])
        rgb = self._rgb(self._fill)

        if self._state == 'disabled':
            rgb = tuple((c + b) // 2 for c, b in zip(rgb, hex_to_rgb(COLORS['bg_light'])))
        elif press:
            rgb = _shade(rgb, -0.16)
        elif hover:
            rgb = _shade(rgb, 0.14)

        self._photo = ImageTk.PhotoImage(_pill(width, height, rgb, self.RADIUS))
        self.itemconfig(self._body, image=self._photo)
        self.tag_raise(self._label)

    def _on_release(self, event):
        self._paint(hover=True)
        if 0 <= event.x < int(self['width']) and 0 <= event.y < int(self['height']):
            self.invoke()

    def invoke(self):
        if self._state != 'disabled' and self._command:
            return self._command()

    def cget(self, key):
        return {'text': self._text, 'state': self._state, 'command': self._command,
                 'bg': self._fill, 'background': self._fill,
                 'fg': self._fg, 'foreground': self._fg}.get(key) \
            if key in ('text', 'state', 'command', 'bg', 'background', 'fg', 'foreground') \
            else super().cget(key)

    __getitem__ = cget

    def configure(self, cnf=None, **kw):
        resize = redraw = False

        if 'text' in kw:
            self._text = kw.pop('text')
            resize = True
        if 'state' in kw:
            self._state = kw.pop('state')
            redraw = True
        if 'command' in kw:
            self._command = kw.pop('command')
        for key in ('bg', 'background'):
            if key in kw:
                self._fill = kw.pop(key)
                redraw = True
        for key in ('fg', 'foreground'):
            if key in kw:
                self._fg = kw.pop(key)
                redraw = True
        for key in self._SWALLOWED + ('padx', 'pady', 'font', 'image'):
            kw.pop(key, None)

        if resize:
            width, height = self._measure()
            super().configure(width=width, height=height)
            self.coords(self._label, width // 2, height // 2)
            self.itemconfig(self._label, text=self._text)
        if resize or redraw:
            self.itemconfig(self._label, fill=self._fg)
            self._paint()
        if cnf is not None or kw:
            return super().configure(cnf, **kw)

    config = configure


tk.Button = _RoundedButton

_WINDOW_BACKGROUND = None


def set_window_background(source):
    """Alt pencerelerde kullanılacak arka planı belirler."""
    global _WINDOW_BACKGROUND
    _WINDOW_BACKGROUND = source


class _ThemedToplevel(tk.Toplevel):
    """Arka planı boş gri kalmayan pencere."""

    def __init__(self, master=None, **kwargs):
        kwargs.setdefault('background', COLORS['bg_light'])
        super().__init__(master, **kwargs)

        if _WINDOW_BACKGROUND is None:
            return

        from .ui.background import ResponsiveBackground

        decoration = tk.Canvas(self, highlightthickness=0, bd=0, bg=COLORS['bg_light'])
        decoration.place(x=0, y=0, relwidth=1, relheight=1)
        # Dekor katmanı en altta kalsın (Canvas.lower başka iş yapıyor).
        tk.Misc.lower(decoration)
        ResponsiveBackground(decoration, _WINDOW_BACKGROUND)
        self._decoration = decoration


tk.Toplevel = _ThemedToplevel


GRADIENT_START = (56, 132, 246)
GRADIENT_END = (139, 92, 246)

CARD_PADDING = 22


def hex_to_rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def rounded_card(width, height, fill, glow=GRADIENT_START, radius=20):
    """Giriş formunun arkasına konan, yuvarlak köşeli ve hafif parlayan kart."""
    pad = CARD_PADDING
    canvas_size = (width + pad * 2, height + pad * 2)

    glow_layer = Image.new('RGBA', canvas_size, (0, 0, 0, 0))
    ImageDraw.Draw(glow_layer).rounded_rectangle(
        [pad - 4, pad - 4, pad + width + 4, pad + height + 4],
        radius=radius + 4, fill=glow + (70,))
    img = glow_layer.filter(ImageFilter.GaussianBlur(pad * 0.55))

    ImageDraw.Draw(img).rounded_rectangle(
        [pad, pad, pad + width, pad + height], radius=radius,
        fill=fill, outline=(255, 255, 255, 42), width=2)
    return img


def generate_app_icon(size=512):
    """Uygulama ikonu: mavi-mor zemin üzerine koltuk ızgarası."""
    scale = 4
    s = size * scale
    radius = int(s * 0.235)

    canvas = _diagonal_gradient(s, s, GRADIENT_START, GRADIENT_END, angle_deg=115).convert('RGBA')

    # Üstteki parlaklık ikona derinlik hissi veriyor.
    highlight = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(highlight).ellipse(
        [-s * 0.35, -s * 0.80, s * 1.35, s * 0.44], fill=(255, 255, 255, 54))
    canvas = Image.alpha_composite(canvas, highlight.filter(ImageFilter.GaussianBlur(s * 0.05)))

    cols = rows = 3
    grid_pad = int(s * 0.185)
    gap = int(s * 0.055)
    cell = (s - 2 * grid_pad - (cols - 1) * gap) / cols
    seat_radius = cell * 0.30
    # Bir sütun dolu, bir sütun boş: anti-kopya düzeni.
    dolu = {(r, c) for r in range(rows) for c in (0, 2)}

    glow = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    seats = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    seat_draw = ImageDraw.Draw(seats)

    for r in range(rows):
        for c in range(cols):
            x0 = grid_pad + c * (cell + gap)
            y0 = grid_pad + r * (cell + gap)
            box = [x0, y0, x0 + cell, y0 + cell]
            if (r, c) in dolu:
                glow_draw.rounded_rectangle(box, radius=seat_radius, fill=(255, 255, 255, 140))
                seat_draw.rounded_rectangle(box, radius=seat_radius, fill=(255, 255, 255, 250))
            else:
                seat_draw.rounded_rectangle(box, radius=seat_radius,
                                             outline=(255, 255, 255, 120), width=int(s * 0.012))

    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(s * 0.03)))
    canvas = Image.alpha_composite(canvas, seats)

    mask = Image.new('L', (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=radius, fill=255)
    canvas.putalpha(mask)

    return canvas.resize((size, size), Image.LANCZOS)


def _diagonal_gradient(w, h, c1, c2, angle_deg=120):
    theta = np.deg2rad(angle_deg)
    x = np.linspace(0, 1, w)
    y = np.linspace(0, 1, h)
    xx, yy = np.meshgrid(x, y)
    proj = xx * np.cos(theta) + yy * np.sin(theta)
    proj = (proj - proj.min()) / (proj.max() - proj.min())
    arr = np.empty((h, w, 3), dtype=np.uint8)
    for i in range(3):
        arr[:, :, i] = (c1[i] + (c2[i] - c1[i]) * proj).astype(np.uint8)
    return Image.fromarray(arr, mode='RGB')


def _add_glow(img, center, radius, color, alpha=90, blur=160):
    glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)
    x, y = center
    draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=color + (alpha,))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(img.convert('RGBA'), glow_layer).convert('RGB')


def generate_login_background(width=1600, height=1000):
    """Giriş ekranı için katmanlı gradyan + glow efektli arka plan."""
    primary = tuple(int(COLORS['primary'][i:i + 2], 16) for i in (1, 3, 5))
    success = tuple(int(COLORS['success'][i:i + 2], 16) for i in (1, 3, 5))
    purple = (155, 89, 182)

    bg = _diagonal_gradient(width, height, (16, 24, 38), (30, 41, 59), angle_deg=120)
    bg = _add_glow(bg, (width * 0.15, height * 0.15), width * 0.30, primary, alpha=90, blur=int(width * 0.11))
    bg = _add_glow(bg, (width * 0.88, height * 0.85), width * 0.34, success, alpha=70, blur=int(width * 0.13))
    bg = _add_glow(bg, (width * 0.75, height * 0.08), width * 0.21, purple, alpha=40, blur=int(width * 0.10))

    arr = np.array(bg).astype(np.int16)
    noise = np.random.default_rng(42).integers(-4, 4, arr.shape, dtype=np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, mode='RGB')


def _blend(arr, mask, color):
    for i in range(3):
        arr[:, :, i] = arr[:, :, i] * (1 - mask) + color[i] * mask
    return arr


def generate_panel_background(width, height, fade_power=1.6, strength=0.30):
    """İçeriğin altında kalan boşluk için arka plan üretir.

    Üst kenarı panel rengiyle aynıdır, aşağı indikçe renklenir. fade_power
    büyüdükçe üst bölge daha uzun süre düz kalır."""
    base = tuple(int(COLORS['bg_light'][i:i + 2], 16) for i in (1, 3, 5))
    primary = tuple(int(COLORS['primary'][i:i + 2], 16) for i in (1, 3, 5))
    success = tuple(int(COLORS['success'][i:i + 2], 16) for i in (1, 3, 5))

    arr = np.zeros((height, width, 3), dtype=np.float32)
    arr[:, :] = base

    yy, xx = np.ogrid[:height, :width]
    asagi = (yy / max(height - 1, 1)) ** fade_power
    saga = np.clip((xx / max(width - 1, 1) - 0.15) / 0.85, 0, 1) ** 1.2

    arr = _blend(arr, asagi * (0.30 + 0.70 * saga) * strength, primary)
    arr = _blend(arr, asagi * np.clip(1 - xx / (width * 0.45), 0, 1) ** 1.5 * strength * 0.4,
                  success)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode='RGB')

    cols, rows = 8, 4
    cell = min(height * 0.20, width * 0.045)
    if cell < 8:
        return img

    layer = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    gap = cell * 0.38
    motif_w = cols * cell + (cols - 1) * gap
    motif_h = rows * cell + (rows - 1) * gap
    x0 = width - motif_w * 0.70
    y0 = height - motif_h * 0.62

    for r in range(rows):
        for c in range(cols):
            x = x0 + c * (cell + gap)
            y = y0 + r * (cell + gap)
            # Bir sütun dolu, bir sütun boş.
            dolu = c % 2 == 0
            renk = (255, 255, 255, 105) if dolu else (255, 255, 255, 45)
            draw.rounded_rectangle([x, y, x + cell, y + cell], radius=cell * 0.24, fill=renk)

    return Image.alpha_composite(img.convert('RGBA'), layer).convert('RGB')


def fade_top_to_base(img, fade_ratio=0.55):
    """Görselin üst kısmını panel rengine karıştırır, arada çizgi görünmesin diye."""
    base = np.array([int(COLORS['bg_light'][i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)
    arr = np.array(img).astype(np.float32)
    height = arr.shape[0]

    yy = np.arange(height, dtype=np.float32).reshape(-1, 1, 1)
    t = np.clip(yy / max(height * fade_ratio, 1.0), 0.0, 1.0) ** 1.3
    arr = base * (1 - t) + arr * t
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode='RGB')


def generate_window_background(width, height):
    """Alt pencereler için daha sade arka plan."""
    return generate_panel_background(width, height, fade_power=3.4, strength=0.26)


def get_panel_background():
    """Panel arka planını hazırlar.

    assets/panel_background.png (veya .jpg) varsa o kullanılır."""
    for ext in ('png', 'jpg', 'jpeg'):
        path = os.path.join(_ASSETS_DIR, f'panel_background.{ext}')
        if os.path.isfile(path):
            try:
                asset = Image.open(path).convert('RGB')
                return lambda w, h: fade_top_to_base(cover_resize(asset, w, h))
            except Exception as e:
                print(f"Uyarı: assets/panel_background.{ext} okunamadı: {e}")
    return generate_panel_background


def cover_resize(img, target_w, target_h):
    """Görseli oranını bozmadan hedef boyutu kaplayacak şekilde ölçekleyip ortadan kırpar."""
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = max(1, round(src_w * scale)), max(1, round(src_h * scale))
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def get_login_background():
    """Giriş ekranı arka planı.

    assets/login_background.png (veya .jpg) varsa o kullanılır."""
    for ext in ('png', 'jpg', 'jpeg'):
        path = os.path.join(_ASSETS_DIR, f'login_background.{ext}')
        if os.path.isfile(path):
            try:
                return Image.open(path).convert('RGB')
            except Exception as e:
                print(f"Uyarı: assets/login_background.{ext} okunamadı: {e}")
    return generate_login_background()


def get_app_icon(size=512):
    """`assets/app_icon.png` varsa onu, yoksa üretilen ikonu döndürür."""
    path = os.path.join(_ASSETS_DIR, 'app_icon.png')
    if os.path.isfile(path):
        try:
            return Image.open(path).convert('RGBA').resize((size, size), Image.LANCZOS)
        except Exception as e:
            print(f"Uyarı: assets/app_icon.png okunamadı: {e}")
    return generate_app_icon(size)
