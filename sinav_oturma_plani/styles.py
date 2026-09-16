"""Ortak renk paleti, ttk stilleri, uygulama ikonu ve şifre hashleme yardımcıları."""
import hashlib
import tkinter as tk

import bcrypt
from PIL import Image, ImageDraw


def hash_password(password):
    """Yeni şifreler için bcrypt hash üretir."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')


def _is_bcrypt_hash(stored_hash):
    return isinstance(stored_hash, str) and stored_hash.startswith(('$2a$', '$2b$', '$2y$')) and len(stored_hash) == 60


def verify_password(password, stored_hash):
    """Şifreyi doğrular. bcrypt hash'lerini destekler; eski (salt'sız SHA256)
    hash'lerle oluşturulmuş hesaplarla da geriye dönük uyumludur."""
    if _is_bcrypt_hash(stored_hash):
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
}


def configure_styles(style):
    """Giriş ekranı, ana menü/dashboard ve yeni eklenen ekranlarda kullanılan
    ortak ttk stilleri. 'clam' temel alınır çünkü Windows'un varsayılan
    temaları (vista/winnative) buton/çerçeve arka plan rengi gibi birçok
    stil seçeneğini yok sayar; 'clam' platformlar arası tutarlı şekilde
    özelleştirilebiliyor."""
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
    style.configure('Accent.TButton', background=COLORS['success'], foreground=COLORS['text_light'],
                     font=('Segoe UI', 11, 'bold'), padding=8)
    style.map('Accent.TButton', background=[('active', COLORS['success_dark'])])
    style.configure('Primary.TButton', background=COLORS['primary'], foreground=COLORS['text_light'],
                     font=('Segoe UI', 10, 'bold'), padding=8)
    style.map('Primary.TButton', background=[('active', COLORS['primary_dark'])])

    style.configure('TEntry', padding=5)

    style.configure('Treeview', rowheight=26, font=('Segoe UI', 10))
    style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))


class _HoverButton(tk.Button):
    """tk.Button ile birebir aynı davranır, tek farkı: üzerine gelindiğinde
    arka plan rengini otomatik olarak açar/koyulaştırır ve imleci ele işaret
    parmağına çevirir. Aşağıdaki `tk.Button = _HoverButton` satırı sayesinde
    uygulamadaki ~30 ekranın TAMAMINDAKİ mevcut `tk.Button(...)` çağrıları,
    her dosyayı tek tek değiştirmeye gerek kalmadan bu davranışı otomatik
    kazanır (tkinter modülündeki Button referansı burada değiştiriliyor)."""

    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.bind('<Enter>', self._on_enter, add='+')
        self.bind('<Leave>', self._on_leave, add='+')

    def _on_enter(self, event):
        if str(self['state']) == 'disabled':
            return
        self._normal_bg = self.cget('background')
        self.config(background=self._hover_color(self._normal_bg), cursor='hand2')

    def _on_leave(self, event):
        if hasattr(self, '_normal_bg'):
            self.config(background=self._normal_bg, cursor='')

    def _hover_color(self, color):
        try:
            r, g, b = (c >> 8 for c in self.winfo_rgb(color))
        except tk.TclError:
            return color
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        if luminance > 140:
            r, g, b = (max(0, int(c * 0.88)) for c in (r, g, b))
        else:
            r, g, b = (min(255, int(c + (255 - c) * 0.18)) for c in (r, g, b))
        return f'#{r:02x}{g:02x}{b:02x}'


tk.Button = _HoverButton


def generate_app_icon(size=512):
    """Uygulama için soyut/jenerik bir rozet ikonu üretir: bir oturma planını
    çağrıştıran kare 'koltuk' ızgarası. Gerçek bir üniversite logosu YERİNE
    kullanılır (telif/marka bağımlılığı olmadan), harici bir görsel dosyasına
    ihtiyaç duymaz — tamamen PIL ile programatik olarak çizilir."""
    scale = 4
    s = size * scale
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = int(s * 0.04)
    primary = tuple(int(COLORS['primary'][i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    success = tuple(int(COLORS['success'][i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    draw.rounded_rectangle([pad, pad, s - pad, s - pad], radius=int(s * 0.22), fill=primary)

    cols, rows = 3, 3
    grid_pad = int(s * 0.17)
    gap = int(s * 0.05)
    cell = (s - 2 * grid_pad - (cols - 1) * gap) / cols
    seat_radius = cell * 0.22
    highlighted = {(0, 1), (1, 0), (1, 2), (2, 1)}

    for r in range(rows):
        for c in range(cols):
            x0 = grid_pad + c * (cell + gap)
            y0 = grid_pad + r * (cell + gap)
            color = success if (r, c) in highlighted else (255, 255, 255, 235)
            draw.rounded_rectangle([x0, y0, x0 + cell, y0 + cell], radius=seat_radius, fill=color)

    return img.resize((size, size), Image.LANCZOS)
