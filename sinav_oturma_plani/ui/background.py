"""Pencere boyutuna uyum sağlayan arka plan."""
from PIL import ImageTk

from ..styles import cover_resize


class ResponsiveBackground:
    """Pencere boyutu değiştikçe arka plan görselini yeniden ölçekler.

    `source` bir görsel ya da genişlik/yükseklik alıp görsel üreten bir
    fonksiyon olabilir."""

    REDRAW_DELAY_MS = 60

    def __init__(self, canvas, source):
        self.canvas = canvas
        self.source = source
        self.item = canvas.create_image(0, 0, anchor="nw")
        self._size = None
        self._job = None
        self._photo = None
        canvas.bind("<Configure>", self._on_configure, add="+")
        canvas.after(0, self._on_configure)

    def _render(self, width, height):
        if callable(self.source):
            return self.source(width, height)
        return cover_resize(self.source, width, height)

    def _draw(self, width, height):
        self._job = None
        # Ekran değişmişse çizilecek bir şey kalmamıştır.
        if not self.canvas.winfo_exists():
            return
        self._photo = ImageTk.PhotoImage(self._render(width, height))
        self.canvas.itemconfig(self.item, image=self._photo)

    def _on_configure(self, _event=None):
        if not self.canvas.winfo_exists():
            return

        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width < 2 or height < 2 or self._size == (width, height):
            return

        self._size = (width, height)
        if self._job is not None:
            self.canvas.after_cancel(self._job)
        self._job = self.canvas.after(self.REDRAW_DELAY_MS,
                                       lambda: self._draw(width, height))
