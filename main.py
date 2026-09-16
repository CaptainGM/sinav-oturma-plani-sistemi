"""Sınav Oturma Planı Sistemi - başlangıç noktası."""
import tkinter as tk

from sinav_oturma_plani.app import SinavTakvimiApp

if __name__ == "__main__":
    root = tk.Tk()
    app = SinavTakvimiApp(root)
    root.mainloop()