"""Ortak renk paleti, ttk stilleri, uygulama ikonu ve şifre hashleme yardımcıları."""
import hashlib
import os
import tkinter as tk

import bcrypt
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ASSETS_DIR = os.path.join(_PROJECT_ROOT, 'assets')


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')


def is_bcrypt_hash(stored_hash):
    return (isinstance(stored_hash, str)
            and stored_hash.startswith(('$2a$', '$2b$', '$2y$'))
            and len(stored_hash) == 60)


def verify_password(password, stored_hash):
    """bcrypt hash'lerini doğrular; eski salt'sız SHA256 hesaplarıyla da uyumludur."""
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
}


def configure_styles(style):
    # 'clam' kullanılıyor: Windows'un vista/winnative temaları buton ve çerçeve
    # arka plan renklerini yok sayıyor.
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
    """Üzerine gelindiğinde arka planı açılan/koyulaşan tk.Button."""

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
    """Oturma planını çağrıştıran kare koltuk ızgarasından oluşan rozet ikonu."""
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
    """`assets/login_background.png|jpg` varsa onu, yoksa üretilen gradyanı döndürür.

    Görsel ham çözünürlüğünde döner; pencere boyutuna uyarlama işi çağıranda."""
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
