#!/usr/bin/env python3
"""
Richtungsdiagramm Generator
Erzeugt eine organische Polarform aus 8 Richtungswerten und speichert sie als PDF.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import math
import os


def polar_to_xy(cx, cy, angle_deg, radius):
    """Kompass-Winkel (N=0°, im Uhrzeigersinn) -> kartesische Koordinaten."""
    rad = math.radians(90 - angle_deg)
    return cx + radius * math.cos(rad), cy + radius * math.sin(rad)


def catmull_rom_to_bezier(pts):
    """Geschlossene Catmull-Rom-Kurve -> kubische Bezier-Segmente."""
    n = len(pts)
    segs = []
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        cp1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        cp2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segs.append((p1, cp1, cp2, p2))
    return segs


def bezier_pts(seg, steps=24):
    p0, cp1, cp2, p1 = seg
    out = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = mt**3*p0[0] + 3*mt**2*t*cp1[0] + 3*mt*t**2*cp2[0] + t**3*p1[0]
        y = mt**3*p0[1] + 3*mt**2*t*cp1[1] + 3*mt*t**2*cp2[1] + t**3*p1[1]
        out.append((x, y))
    return out


DIRS   = [0, 45, 90, 135, 180, 225, 270, 315]
LBLS   = ['N', 'NO', 'O', 'SO', 'S', 'SW', 'W', 'NW']
GREEN  = '#7DC97A'
DGREEN = '#3A8A36'
GRID   = '#e0e0e0'


# ── Vorschau ─────────────────────────────────────────────────────────────────

class PreviewCanvas(tk.Canvas):
    def __init__(self, master, size=300, **kw):
        super().__init__(master, width=size, height=size,
                         bg='white', highlightthickness=1,
                         highlightbackground='#ccc', **kw)
        self.sz = size
        self.cx = size // 2
        self.cy = size // 2

    def redraw(self, values):
        self.delete('all')
        if not values or any(v <= 0 for v in values):
            return
        max_v  = max(values)
        radius = self.sz * 0.37

        # Gitter
        for frac in [0.25, 0.5, 0.75, 1.0]:
            r = radius * frac
            self.create_oval(self.cx-r, self.cy-r, self.cx+r, self.cy+r,
                             outline=GRID, dash=(4,4))
        for d in DIRS:
            x, y = polar_to_xy(self.cx, self.cy, d, radius)
            self.create_line(self.cx, self.cy, x, y, fill=GRID, dash=(4,4))

        # Datenpunkte
        pts = [polar_to_xy(self.cx, self.cy, d, v/max_v*radius)
               for d, v in zip(DIRS, values)]

        # Smooth polygon
        segs = catmull_rom_to_bezier(pts)
        poly = []
        for seg in segs:
            poly.extend(bezier_pts(seg)[:-1])
        flat = [c for p in poly for c in p]
        self.create_polygon(flat, fill=GREEN, outline=DGREEN, width=2, smooth=False)

        # Punkte
        for x, y in pts:
            r = 4
            self.create_oval(x-r, y-r, x+r, y+r, fill=DGREEN, outline='white', width=1)

        # Labels
        for d, v, lbl in zip(DIRS, values, LBLS):
            x, y = polar_to_xy(self.cx, self.cy, d, v/max_v*radius + 18)
            self.create_text(x, y, text=f'{lbl}\n{v:.3g}',
                             font=('Helvetica', 7, 'bold'), fill='#333', justify='center')


# ── PDF ───────────────────────────────────────────────────────────────────────

def generate_pdf(values, title, output_path):
    from reportlab.pdfgen import canvas as RC
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor

    FILL   = HexColor('#7DC97A')
    STROKE = HexColor('#3A8A36')
    GRIDC  = HexColor('#dddddd')

    pw, ph = A4
    c = RC.Canvas(output_path, pagesize=A4)

    cx     = pw / 2
    cy     = ph / 2 - 20
    max_v  = max(values)
    radius = min(pw, ph) * 0.36

    def pxy(deg, val):
        rad = math.radians(90 - deg)
        r   = (val / max_v) * radius
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    # Gitter
    c.setStrokeColor(GRIDC)
    c.setLineWidth(0.5)
    for frac in [0.25, 0.5, 0.75, 1.0]:
        c.circle(cx, cy, radius * frac)
    for deg in DIRS:
        rad = math.radians(90 - deg)
        c.line(cx, cy, cx + radius*math.cos(rad), cy + radius*math.sin(rad))

    # Form
    pts  = [pxy(d, v) for d, v in zip(DIRS, values)]
    segs = catmull_rom_to_bezier(pts)

    c.setFillColor(FILL)
    c.setStrokeColor(STROKE)
    c.setLineWidth(2)

    path = c.beginPath()
    path.moveTo(*pts[0])
    for (p0, cp1, cp2, p1) in segs:
        path.curveTo(cp1[0], cp1[1], cp2[0], cp2[1], p1[0], p1[1])
    path.close()
    c.drawPath(path, fill=1, stroke=1)

    # Datenpunkte
    c.setFillColor(STROKE)
    c.setStrokeColor(HexColor('#ffffff'))
    c.setLineWidth(1.5)
    for p in pts:
        c.circle(p[0], p[1], 4, fill=1, stroke=1)

    # Labels
    for deg, val, lbl in zip(DIRS, values, LBLS):
        rad = math.radians(90 - deg)
        r   = (val / max_v) * radius + 30
        lx  = cx + r * math.cos(rad)
        ly  = cy + r * math.sin(rad)
        c.setFillColor(HexColor('#1a1a1a'))
        c.setFont('Helvetica-Bold', 10)
        c.drawCentredString(lx, ly + 5, lbl)
        c.setFont('Helvetica', 9)
        c.drawCentredString(lx, ly - 7, str(val))

    # Titel
    c.setFillColor(HexColor('#1a1a1a'))
    c.setFont('Helvetica-Bold', 18)
    c.drawCentredString(cx, ph - 65, title)

    c.save()


# ── Hauptfenster ──────────────────────────────────────────────────────────────

DEFAULTS = [1.0, 0.8, 1.2, 0.7, 1.0, 0.9, 0.6, 1.1]
INPUT_LABELS = [
    ('N  (0°)',   '↑'), ('NO (45°)',  '↗'), ('O  (90°)',  '→'), ('SO (135°)', '↘'),
    ('S  (180°)', '↓'), ('SW (225°)', '↙'), ('W  (270°)', '←'), ('NW (315°)', '↖'),
]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Richtungsdiagramm Generator')
        self.resizable(False, False)
        self.configure(bg='#f5f7f5')
        self._build()

    def _build(self):
        # ── Links: Eingaben ───────────────────────────────────────────────────
        left = tk.Frame(self, bg='#f5f7f5', padx=20, pady=20)
        left.grid(row=0, column=0, sticky='ns')

        tk.Label(left, text='Richtungsdiagramm', bg='#f5f7f5',
                 fg='#2a6e27', font=('Helvetica', 16, 'bold')).pack(anchor='w')
        tk.Label(left, text='Werte für die 8 Himmelsrichtungen eingeben',
                 bg='#f5f7f5', fg='#666', font=('Helvetica', 9)).pack(anchor='w', pady=(2, 12))

        # Diagramm-Titel
        tf = tk.Frame(left, bg='#f5f7f5')
        tf.pack(fill='x', pady=(0, 12))
        tk.Label(tf, text='Diagramm-Titel:', bg='#f5f7f5',
                 font=('Helvetica', 9, 'bold'), fg='#333').pack(anchor='w')
        self.title_var = tk.StringVar(value='Richtungsdiagramm')
        ttk.Entry(tf, textvariable=self.title_var, width=28,
                  font=('Helvetica', 10)).pack(fill='x')

        # Wert-Eingaben
        self.vars = []
        for (lbl, arrow), default in zip(INPUT_LABELS, DEFAULTS):
            row = tk.Frame(left, bg='#f5f7f5')
            row.pack(fill='x', pady=2)
            tk.Label(row, text=arrow, width=2, bg='#f5f7f5',
                     fg='#3a8a36', font=('Helvetica', 12)).pack(side='left')
            tk.Label(row, text=lbl, width=11, anchor='w', bg='#f5f7f5',
                     font=('Helvetica', 10, 'bold'), fg='#333').pack(side='left')
            var = tk.StringVar(value=str(default))
            var.trace_add('write', lambda *_: self._update_preview())
            ttk.Entry(row, textvariable=var, width=10,
                      font=('Helvetica', 10)).pack(side='left', padx=4)
            self.vars.append(var)

        tk.Button(left, text='📄  PDF speichern',
                  font=('Helvetica', 12, 'bold'), bg='#4caf50', fg='white',
                  relief='flat', activebackground='#388e3c', activeforeground='white',
                  padx=14, pady=9, cursor='hand2',
                  command=self._save).pack(fill='x', pady=(16, 4))

        self.status = tk.Label(left, text='', bg='#f5f7f5', fg='#2a6e27',
                               font=('Helvetica', 8), wraplength=250, justify='left')
        self.status.pack(anchor='w')

        # ── Rechts: Vorschau ──────────────────────────────────────────────────
        right = tk.Frame(self, bg='#f5f7f5', padx=10, pady=20)
        right.grid(row=0, column=1, sticky='nsew')
        tk.Label(right, text='Live-Vorschau', bg='#f5f7f5',
                 fg='#666', font=('Helvetica', 9)).pack(anchor='w', pady=(0, 4))
        self.preview = PreviewCanvas(right, size=320)
        self.preview.pack()

        self._update_preview()

    def _values(self):
        out = []
        for var in self.vars:
            try:
                v = float(var.get().replace(',', '.'))
                if v <= 0:
                    raise ValueError
                out.append(v)
            except ValueError:
                return None
        return out

    def _update_preview(self):
        v = self._values()
        if v:
            self.preview.redraw(v)

    def _save(self):
        values = self._values()
        if values is None:
            messagebox.showerror('Eingabefehler',
                'Bitte nur positive Zahlen eingeben (z. B. 1.5).')
            return
        path = filedialog.asksaveasfilename(
            defaultextension='.pdf',
            filetypes=[('PDF-Datei', '*.pdf')],
            initialfile='richtungsdiagramm.pdf',
            title='PDF speichern unter …')
        if not path:
            return
        try:
            generate_pdf(values, self.title_var.get() or 'Richtungsdiagramm', path)
            self.status.config(text=f'✓ Gespeichert:\n{path}')
        except Exception as e:
            messagebox.showerror('Fehler', str(e))


if __name__ == '__main__':
    import subprocess, sys
    try:
        import reportlab
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install',
                               'reportlab', '-q', '--break-system-packages'])
    App().mainloop()
