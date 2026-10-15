# -*- coding: utf-8 -*-
from __future__ import division
import sys, os, json, time, math, datetime, threading

try:
    import urllib2 as urllib_request
    from urllib import urlencode
except ImportError:
    import urllib.request as urllib_request
    from urllib.parse import urlencode

from PySide import QtCore, QtGui
QtWidgets = QtGui

CONFIG_FILE = os.path.expanduser("~/.n9_market_config.json")
DEFAULT_MI9T = "http://192.168.8.239:8083"

CATALOG = [
    ("BTC",    u"Bitcoin",      68500.0, 2, u"$"),
    ("ETH",    u"Ethereum",     2650.0,  2, u"$"),
    ("SOL",    u"Solana",       155.0,   2, u"$"),
    ("XRP",    u"Ripple",       0.585,   4, u"$"),
    ("DOGE",   u"Dogecoin",     0.125,   4, u"$"),
    ("BNB",    u"BNB",          590.0,   2, u"$"),
    ("AVAX",   u"Avalanche",    28.5,    2, u"$"),
    ("XAU",    u"Ons Altin",    2665.0,  2, u"$"),
    ("XAG",    u"Ons Gumus",    31.45,   2, u"$"),
    ("BRENT",  u"Brent",        77.80,   2, u"$"),
    ("NASDAQ", u"Nasdaq",       18450.0, 2, u""),
    ("SP500",  u"S&P 500",      5810.0,  2, u""),
    ("NVDA",   u"Nvidia",       132.0,   2, u"$"),
    ("TSLA",   u"Tesla",        218.0,   2, u"$"),
    ("AAPL",   u"Apple",        228.0,   2, u"$"),
    ("USDTRY", u"Dolar/TL",     34.25,   4, u"TL"),
    ("EURTRY", u"Euro/TL",      37.30,   4, u"TL")
]

DEF_ASSETS = [
    {"id": s, "name": n, "base": b, "dec": d, "unit": u}
    for s, n, b, d, u in CATALOG[:8]
]

INTERVALS = [
    ("1m",  u"1dk",  60),
    ("3m",  u"3dk",  180),
    ("5m",  u"5dk",  300),
    ("15m", u"15dk", 900),
    ("1h",  u"1S",   3600),
    ("4h",  u"4S",   14400),
    ("1d",  u"1G",   86400),
    ("1wk", u"1H",   604800)
]


def load_config():
    cfg = {"proxy_url": DEFAULT_MI9T, "assets": DEF_ASSETS,
           "indicator": "SMA", "show_rsi": True, "candles": 42}
    if os.path.exists(CONFIG_FILE):
        try:
            f = open(CONFIG_FILE, "r")
            cfg.update(json.loads(f.read()))
            f.close()
            if not cfg.get("assets"): cfg["assets"] = DEF_ASSETS
        except Exception: pass
    cfg["proxy_url"] = DEFAULT_MI9T
    return cfg


def save_config(cfg):
    try:
        f = open(CONFIG_FILE, "w")
        f.write(json.dumps(cfg, indent=2))
        f.close()
    except Exception: pass


def fmt_price(val, dec=2, u=u""):
    if val is None: return u"--"
    raw = ("%%.%df" % dec) % float(val)
    parts = raw.split(".")
    ip = parts[0]
    neg = "-" if ip.startswith("-") else ""
    if neg: ip = ip[1:]
    rev = ip[::-1]
    grp = ",".join([rev[i:i+3] for i in range(0, len(rev), 3)])[::-1]
    res = neg + grp + ("." + parts[1] if len(parts) > 1 else "")
    return (u + res) if u else res


def calc_sma(c, p):
    return [None if i+1 < p else sum(c[i+1-p:i+1])/float(p) for i in range(len(c))]


def calc_ema(c, p):
    res, k, prev = [], 2.0/(p+1.0), None
    for i in range(len(c)):
        if i+1 < p: res.append(None)
        elif i+1 == p: prev = sum(c[:p])/float(p); res.append(prev)
        else: prev = (c[i]*k) + (prev*(1.0-k)); res.append(prev)
    return res


def calc_bb(c, p=20, mult=2.0):
    up, low, sma = [], [], calc_sma(c, p)
    for i in range(len(c)):
        if sma[i] is None: up.append(None); low.append(None)
        else:
            m = sma[i]
            dev = math.sqrt(sum((x-m)**2 for x in c[i+1-p:i+1])/p) * mult
            up.append(m+dev); low.append(m-dev)
    return up, low


def calc_macd(c, fast=12, slow=26, signal=9):
    ef, es = calc_ema(c, fast), calc_ema(c, slow)
    ml = [None if (ef[i] is None or es[i] is None) else (ef[i]-es[i]) for i in range(len(c))]
    val = [x if x is not None else 0.0 for x in ml]
    sl = calc_ema(val, signal)
    hist = [0.0 if (ml[i] is None or sl[i] is None) else (ml[i]-sl[i]) for i in range(len(c))]
    return ml, sl, hist


def calc_rsi(c, p=14):
    if len(c) < 15: return [50.0] * len(c)
    g, l = [0.0], [0.0]
    for i in range(1, len(c)):
        d = c[i] - c[i-1]
        g.append(d if d > 0 else 0.0)
        l.append(-d if d < 0 else 0.0)
    ag, al = sum(g[1:15])/14.0, sum(l[1:15])/14.0
    res = [50.0] * 14
    for i in range(14, len(c)):
        ag = (ag*13.0 + g[i])/14.0
        al = (al*13.0 + l[i])/14.0
        rs = ag / max(1e-9, al)
        res.append(100.0 - (100.0 / (1.0 + rs)))
    return res


def make_demo(asset, inv_sec=3600, count=60):
    candles, base, scale = [], float(asset.get("base", 100.0)), math.sqrt(inv_sec/3600.0)
    p = base * (0.96 + (int(inv_sec)%7)*0.008)
    now = int(time.time())
    seed = sum(ord(x) for x in asset.get("id", "BTC"))*37 + int(inv_sec)
    for i in range(count):
        t = now - (count-i)*inv_sec
        wave = math.sin((seed+i*1.3)*0.43) + math.cos(i*0.71)*0.6
        c = max(base*0.05, p + wave*(base*0.008*scale))
        h = max(p, c) + abs(math.sin(i*0.89+seed))*(base*0.005*scale)
        l = min(p, c) - abs(math.cos(i*0.67+seed))*(base*0.005*scale)
        v = (abs(math.sin(i*0.5+seed)) + 0.3) * 1500.0
        candles.append({"t": t, "o": p, "h": h, "l": l, "c": c, "v": v})
        p = c
    return candles


class Signaler(QtCore.QObject):
    dataReady = QtCore.Signal(dict, int)


class ChartWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ChartWidget, self).__init__(parent)
        self.setMinimumSize(360, 240)
        self.candles, self.asset, self.count = [], DEF_ASSETS[0], 42
        self.mode_ind, self.show_rsi, self.sel_idx, self.online = "SMA", True, None, False
        self.inv_sec = 3600
        self.c_sma7, self.c_sma20, self.c_ema9, self.c_ema21 = [], [], [], []
        self.c_bbu, self.c_bbl, self.c_ml, self.c_ms, self.c_mh, self.c_rsi = [], [], [], [], [], []

    def set_data(self, c, a, online):
        self.candles, self.asset, self.online, self.sel_idx = c or [], a, online, None
        self._precalc(); self.update()

    def _precalc(self):
        if not self.candles: return
        cl = [x["c"] for x in self.candles]
        if self.mode_ind == "SMA": self.c_sma7, self.c_sma20 = calc_sma(cl, 7), calc_sma(cl, 20)
        elif self.mode_ind == "EMA": self.c_ema9, self.c_ema21 = calc_ema(cl, 9), calc_ema(cl, 21)
        elif self.mode_ind == "BB": self.c_bbu, self.c_bbl = calc_bb(cl, 20, 2.0)
        elif self.mode_ind == "MACD": self.c_ml, self.c_ms, self.c_mh = calc_macd(cl, 12, 26, 9)
        if self.show_rsi: self.c_rsi = calc_rsi(cl, 14)

    def zoom_in(self):
        if self.count > 18: self.count -= 6; self.update()
    def zoom_out(self):
        if self.count < 72: self.count += 6; self.update()
    def _vis(self):
        return self.candles[-min(len(self.candles), self.count):]
    def mousePressEvent(self, e): self._tap(e.pos().x())
    def mouseMoveEvent(self, e):
        if e.buttons() & QtCore.Qt.LeftButton: self._tap(e.pos().x())

    def _tap(self, x):
        vis = self._vis()
        if not vis: return
        pw = max(10, self.width() - 88)
        idx = int(((x - 10) / float(pw)) * len(vis)) if pw > 0 else 0
        self.sel_idx = max(0, min(len(vis) - 1, idx))
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QtGui.QColor("#000000"))
        vis = self._vis()
        if not vis: return

        top_p, left_p, right_p = 28, 8, 78
        pw = max(20, w - left_p - right_p)
        rsi_h = 58 if self.show_rsi else 0
        ph = max(20, h - top_p - (24 + rsi_h))

        min_p, max_p = min(c["l"] for c in vis), max(c["h"] for c in vis)
        if max_p <= min_p: max_p = min_p + 1.0
        pad = (max_p - min_p) * 0.05
        min_p, max_p = min_p - pad, max_p + pad
        span = max(1.0, max_p - min_p)

        def y_val(v): return int(top_p + ph - ((v - min_p) / float(span)) * ph)

        p.setFont(QtGui.QFont("Sans", 8))
        for i in range(5):
            gy = int(top_p + (ph / 4.0) * i)
            pv = max_p - (span / 4.0) * i
            p.setPen(QtGui.QPen(QtGui.QColor("#111720"), 1))
            p.drawLine(left_p, gy, left_p + pw, gy)
            p.setPen(QtGui.QColor("#788898"))
            p.drawText(left_p + pw + 4, gy + 4, fmt_price(pv, self.asset.get("dec", 2)))

        n = len(vis)
        sx = pw / float(n)
        cw = max(3, min(15, int(sx * 0.65)))

        if n >= 4:
            p.setFont(QtGui.QFont("Sans", 7))
            p.setPen(QtGui.QColor("#607080"))
            for i in range(0, n, max(1, n // 3)):
                cx = int(left_p + (i + 0.5) * sx)
                t_obj = datetime.datetime.fromtimestamp(vis[i]["t"])
                fmt = "%d/%m" if self.inv_sec >= 86400 else "%H:%M"
                p.drawText(cx - 18, top_p + ph + 13, 36, 12, QtCore.Qt.AlignCenter, t_obj.strftime(fmt))

        max_v = max(c.get("v", 1.0) for c in vis)
        for i, c in enumerate(vis):
            cx = int(left_p + (i + 0.5) * sx)
            vh = int((c.get("v", 0.0) / max(1.0, max_v)) * (ph * 0.18))
            col = QtGui.QColor("#00E676" if c["c"] >= c["o"] else "#FF5252")
            col.setAlpha(40)
            p.fillRect(int(cx - cw/2.0), top_p + ph - vh, cw, vh, col)

        bull, bear = QtGui.QColor("#00E676"), QtGui.QColor("#FF5252")
        for i, c in enumerate(vis):
            cx = int(left_p + (i + 0.5) * sx)
            col = bull if c["c"] >= c["o"] else bear
            p.setPen(QtGui.QPen(col, 1))
            p.drawLine(cx, y_val(c["h"]), cx, y_val(c["l"]))
            p.fillRect(int(cx - cw/2.0), min(y_val(c["o"]), y_val(c["c"])), cw, max(2, abs(y_val(c["c"]) - y_val(c["o"]))), col)

        if self.mode_ind == "SMA" and self.c_sma7:
            self._plot(p, self.c_sma7[-n:], sx, left_p, y_val, "#FFD54F")
            self._plot(p, self.c_sma20[-n:], sx, left_p, y_val, "#40C4FF")
        elif self.mode_ind == "EMA" and self.c_ema9:
            self._plot(p, self.c_ema9[-n:], sx, left_p, y_val, "#E040FB")
            self._plot(p, self.c_ema21[-n:], sx, left_p, y_val, "#FF9100")
        elif self.mode_ind == "BB" and self.c_bbu:
            self._plot(p, self.c_bbu[-n:], sx, left_p, y_val, "#00E5FF")
            self._plot(p, self.c_bbl[-n:], sx, left_p, y_val, "#00E5FF")
        elif self.mode_ind == "MACD" and self.c_ml:
            mh = self.c_mh[-n:]
            m_max = max(1e-4, max(abs(x) for x in mh if x is not None))
            for i, hv in enumerate(mh):
                cx = int(left_p + (i + 0.5) * sx)
                hp = int((hv / m_max) * (ph * 0.25))
                col_h = QtGui.QColor("#00E676" if hv >= 0 else "#FF5252")
                col_h.setAlpha(120)
                y0 = int(top_p + ph * 0.7)
                if hp >= 0: p.fillRect(int(cx - cw/2.0), y0 - hp, cw, hp, col_h)
                else: p.fillRect(int(cx - cw/2.0), y0, cw, abs(hp), col_h)
            self._plot(p, self.c_ml[-n:], sx, left_p, lambda v: int(top_p + ph*0.7 - (v/m_max)*(ph*0.25)), "#40C4FF")
            self._plot(p, self.c_ms[-n:], sx, left_p, lambda v: int(top_p + ph*0.7 - (v/m_max)*(ph*0.25)), "#FF5252")

        if self.show_rsi and self.c_rsi:
            ry_top, ry_h = top_p + ph + 8, 44
            p.setPen(QtGui.QPen(QtGui.QColor("#16202E"), 1))
            p.drawRect(left_p, ry_top, pw, ry_h)
            p.setPen(QtGui.QPen(QtGui.QColor("#243348"), 1, QtCore.Qt.DotLine))
            p.drawLine(left_p, ry_top + int(ry_h * 0.3), left_p + pw, ry_top + int(ry_h * 0.3))
            p.drawLine(left_p, ry_top + int(ry_h * 0.7), left_p + pw, ry_top + int(ry_h * 0.7))
            p.setPen(QtGui.QColor("#788898"))
            p.drawText(left_p + pw + 4, ry_top + 14, u"70")
            p.drawText(left_p + pw + 4, ry_top + 34, u"30")
            self._plot(p, self.c_rsi[-n:], sx, left_p, lambda v: int(ry_top + ry_h - (v/100.0)*ry_h), "#FF9100")

        last_c = vis[-1]
        ly = y_val(last_c["c"])
        lcol = bull if last_c["c"] >= last_c["o"] else bear
        p.fillRect(QtCore.QRect(left_p + pw + 2, ly - 9, right_p - 4, 18), lcol)
        p.setPen(QtGui.QColor("#000000"))
        p.drawText(QtCore.QRect(left_p + pw + 2, ly - 9, right_p - 4, 18), QtCore.Qt.AlignCenter, fmt_price(last_c["c"], self.asset.get("dec", 2)))

        i_cur = self.sel_idx if self.sel_idx is not None else (n - 1)
        cur = vis[i_cur]
        if self.sel_idx is not None:
            p.setPen(QtGui.QPen(QtGui.QColor("#CCD7E2"), 1, QtCore.Qt.DotLine))
            cx = int(left_p + (self.sel_idx + 0.5) * sx)
            p.drawLine(cx, top_p, cx, top_p + ph)

        dt = datetime.datetime.fromtimestamp(cur["t"])
        chg = ((cur["c"] - cur["o"]) / float(cur["o"]) * 100.0) if cur["o"] else 0.0
        dec = self.asset.get("dec", 2)
        info = u"%s | A:%s Y:%s D:%s K:%s (%+.2f%%)" % (
            dt.strftime("%d.%m %H:%M"), fmt_price(cur["o"], dec), fmt_price(cur["h"], dec), fmt_price(cur["l"], dec), fmt_price(cur["c"], dec), chg
        )
        p.setFont(QtGui.QFont("Sans", 9, QtGui.QFont.Bold))
        p.setPen(QtGui.QColor("#FFFFFF"))
        p.drawText(left_p, 18, info)

        p.setFont(QtGui.QFont("Sans", 8))
        p.setPen(QtGui.QColor("#00E676" if self.online else "#FFB300"))
        p.drawText(w - 74, 18, u"[CANLI]" if self.online else u"[DEMO]")

    def _plot(self, p, vals, sx, left_p, y_func, col_hex):
        p.setPen(QtGui.QPen(QtGui.QColor(col_hex), 1.5))
        prev = None
        for i, v in enumerate(vals):
            if v is not None:
                pt = QtCore.QPoint(int(left_p + (i + 0.5) * sx), y_func(v))
                if prev: p.drawLine(prev, pt)
                prev = pt


class SearchPairDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(SearchPairDialog, self).__init__(parent)
        self.setWindowTitle(u"Parite Ekle")
        self.resize(360, 400)
        self.selected_pair = None
        self.setStyleSheet("QDialog { background: #0A0E14; color: #FFF; font-family: Sans; } QLineEdit { background: #141C28; color: #FFF; border: 1px solid #28374E; border-radius: 6px; padding: 10px; font-size: 14px; } QListWidget { background: #101620; color: #EAECEF; border: 1px solid #1E2838; border-radius: 6px; font-size: 13px; } QListWidget::item { padding: 10px; border-bottom: 1px solid #182; } QListWidget::item:selected { background: #0E3524; color: #00E676; } QPushButton { background: #14283C; color: #40C4FF; border: 1px solid #40C4FF; border-radius: 6px; padding: 10px; font-weight: bold; }")

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.search_box = QtWidgets.QLineEdit(self)
        self.search_box.setPlaceholderText(u"Parite ara (SOL, DOGE, NVDA...)")
        self.search_box.textChanged.connect(self._on_search)
        layout.addWidget(self.search_box)

        self.list_widget = QtWidgets.QListWidget(self)
        self.list_widget.itemDoubleClicked.connect(self._accept_item)
        layout.addWidget(self.list_widget)

        bb = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton(u"+ Ekle")
        btn_add.clicked.connect(self._accept_custom)
        bb.addWidget(btn_add)
        btn_close = QtWidgets.QPushButton(u"Vazgec")
        btn_close.setStyleSheet("color: #8C9BAA; border-color: #28374E;")
        btn_close.clicked.connect(self.reject)
        bb.addWidget(btn_close)
        layout.addLayout(bb)
        self._populate_list(CATALOG)

    def _populate_list(self, items):
        self.list_widget.clear()
        for sym, name, base, dec, u in items:
            item = QtWidgets.QListWidgetItem(u"%s  •  %s (%s)" % (sym, name, u))
            item.setData(QtCore.Qt.UserRole, (sym, name, base, dec, u))
            self.list_widget.addItem(item)

    def _on_search(self, txt):
        q = str(txt).strip().upper()
        matched = [x for x in CATALOG if (q in x[0] or q in x[1].upper())]
        self._populate_list(matched)

    def _accept_item(self, item):
        d = item.data(QtCore.Qt.UserRole)
        self.selected_pair = {"id": d[0], "name": d[1], "base": d[2], "dec": d[3], "unit": d[4]}
        self.accept()

    def _accept_custom(self):
        curr = self.list_widget.currentItem()
        if curr: self._accept_item(curr); return
        raw = str(self.search_box.text()).strip().upper()
        if raw: self.selected_pair = {"id": raw, "name": raw, "base": 100.0, "dec": 2, "unit": u"$"}; self.accept()


class SmoothScrollFilter(QtCore.QObject):
    def __init__(self, scroll_area, parent=None):
        super(SmoothScrollFilter, self).__init__(parent)
        self.scroll = scroll_area
        self.drag_start_y, self.is_dragging = 0, False

    def eventFilter(self, obj, e):
        if e.type() == QtCore.QEvent.MouseButtonPress:
            self.drag_start_y, self.is_dragging = e.globalY(), False
        elif e.type() == QtCore.QEvent.MouseMove:
            dy = self.drag_start_y - e.globalY()
            if abs(dy) > 6:
                self.is_dragging = True
                sb = self.scroll.verticalScrollBar()
                sb.setValue(sb.value() + dy)
                self.drag_start_y = e.globalY()
                return True
        elif e.type() == QtCore.QEvent.MouseButtonRelease:
            if self.is_dragging:
                self.is_dragging = False
                return True
        return False


class MainWin(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWin, self).__init__()
        self.cfg = load_config()
        self.assets = self.cfg.get("assets", DEF_ASSETS)
        self.cur_idx = 0
        self.cur_inv_code, self.cur_inv_sec, self.cur_inv_label = "1h", 3600, u"1S"
        self.signaler = Signaler()
        self.signaler.dataReady.connect(self._on_data)
        self.cur_req_id = 0
        self.buttons, self.inv_buttons = [], []

        self.setWindowTitle(u"MeeFin")
        self.resize(854, 480)
        self.setStyleSheet("QMainWindow, QWidget { background: #000; color: #FFF; font-family: Sans; } QPushButton { background: #0E131A; color: #A0B0C0; border: 1px solid #1C2534; border-radius: 6px; padding: 6px; font-size: 13px; font-weight: bold; } QPushButton[active='true'] { background: #00E676; color: #000000; border: 1px solid #00E676; font-weight: bold; } QPushButton#IconBtn { background: #141B26; color: #00E676; border: 1px solid #202D40; font-size: 16px; } QPushButton#MiniBtn { background: #101620; font-size: 16px; font-weight: bold; border: 1px solid #202D40; }")
        self._ui()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(4000)
        self.refresh()

    def _ui(self):
        c = QtWidgets.QWidget(self)
        self.setCentralWidget(c)
        root = QtWidgets.QHBoxLayout(c)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        self.scroll = QtWidgets.QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFixedWidth(146)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { border: none; background: #000; width: 4px; } QScrollBar::handle:vertical { background: #202D40; border-radius: 2px; }")

        self.scroll_filter = SmoothScrollFilter(self.scroll, self)
        self.scroll.viewport().installEventFilter(self.scroll_filter)

        self.scroll_widget = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout(self.scroll_widget)
        self.list_layout.setContentsMargins(0, 0, 2, 0)
        self.list_layout.setSpacing(4)
        self._rebuild_list()
        self.scroll.setWidget(self.scroll_widget)
        root.addWidget(self.scroll, 0)

        rp = QtWidgets.QVBoxLayout()
        rp.setSpacing(4)

        tb = QtWidgets.QHBoxLayout()
        tb.setSpacing(4)

        self.btn_toggle = QtWidgets.QPushButton(u"◀")
        self.btn_toggle.setObjectName("IconBtn")
        self.btn_toggle.setFixedSize(44, 38)
        self.btn_toggle.clicked.connect(self._toggle_side)
        tb.addWidget(self.btn_toggle)

        self.btn_full = QtWidgets.QPushButton(u"⛶")
        self.btn_full.setObjectName("IconBtn")
        self.btn_full.setFixedSize(40, 38)
        self.btn_full.clicked.connect(self._toggle_full)
        tb.addWidget(self.btn_full)

        self.title_lbl = QtWidgets.QLabel(u"BTC • 1S")
        self.title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; margin-left: 4px;")
        tb.addWidget(self.title_lbl)

        self.price_lbl = QtWidgets.QLabel(u"--")
        self.price_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #00E676;")
        tb.addWidget(self.price_lbl)

        tb.addStretch(1)

        self.inv_buttons = []
        for code, label, sec in INTERVALS:
            ib = QtWidgets.QPushButton(label)
            ib.setFixedSize(36, 32)
            ib.setProperty("active", "true" if code == self.cur_inv_code else "false")
            ib.clicked.connect(self._make_inv_cb(code, sec, label))
            tb.addWidget(ib)
            self.inv_buttons.append((code, ib))
        rp.addLayout(tb)

        self.chart = ChartWidget(self)
        self.chart.inv_sec = self.cur_inv_sec
        self.chart.mode_ind = self.cfg.get("indicator", "SMA")
        self.chart.show_rsi = self.cfg.get("show_rsi", True)
        rp.addWidget(self.chart, 1)

        bb = QtWidgets.QHBoxLayout()
        bb.setSpacing(4)

        b_in = QtWidgets.QPushButton(u"+")
        b_in.setFixedSize(38, 36)
        b_in.clicked.connect(self.chart.zoom_in)
        bb.addWidget(b_in)

        b_out = QtWidgets.QPushButton(u"-")
        b_out.setFixedSize(38, 36)
        b_out.clicked.connect(self.chart.zoom_out)
        bb.addWidget(b_out)

        self.btn_ind = QtWidgets.QPushButton(u"IND: " + self.chart.mode_ind)
        self.btn_ind.setFixedHeight(36)
        self.btn_ind.clicked.connect(self._cycle_indicator)
        bb.addWidget(self.btn_ind)

        self.btn_rsi = QtWidgets.QPushButton(u"RSI")
        self.btn_rsi.setFixedHeight(36)
        self.btn_rsi.setProperty("active", "true" if self.chart.show_rsi else "false")
        self.btn_rsi.clicked.connect(self._toggle_rsi)
        bb.addWidget(self.btn_rsi)

        bb.addStretch(1)

        b_ref = QtWidgets.QPushButton(u"⟳")
        b_ref.setFixedSize(40, 36)
        b_ref.clicked.connect(self.refresh)
        bb.addWidget(b_ref)
        rp.addLayout(bb)

        root.addLayout(rp, 1)

    def _toggle_side(self):
        if self.scroll.isVisible():
            self.scroll.hide()
            self.btn_toggle.setText(u"☰")
        else:
            self.scroll.show()
            self.btn_toggle.setText(u"◀")

    def _toggle_full(self):
        if self.isFullScreen(): self.showNormal()
        else: self.showFullScreen()

    def _rebuild_list(self):
        for b in self.buttons: b.setParent(None)
        self.buttons = []

        for idx, a in enumerate(self.assets):
            btn = QtWidgets.QPushButton(u"%s\n%s" % (a["id"], a["name"]))
            btn.setMinimumHeight(50)
            btn.setProperty("active", "true" if idx == self.cur_idx else "false")
            btn.clicked.connect(self._make_asset_cb(idx))
            btn.installEventFilter(self.scroll_filter)
            self.list_layout.addWidget(btn)
            self.buttons.append(btn)

        bot_bar = QtWidgets.QHBoxLayout()
        bot_bar.setSpacing(4)
        b_add = QtWidgets.QPushButton(u"+")
        b_add.setObjectName("MiniBtn")
        b_add.setFixedHeight(44)
        b_add.setStyleSheet("color: #40C4FF; border-color: #40C4FF;")
        b_add.clicked.connect(self._open_search_dialog)
        bot_bar.addWidget(b_add)
        self.buttons.append(b_add)

        b_del = QtWidgets.QPushButton(u"-")
        b_del.setObjectName("MiniBtn")
        b_del.setFixedHeight(44)
        b_del.setStyleSheet("color: #FF5252; border-color: #FF5252;")
        b_del.clicked.connect(self._on_del)
        bot_bar.addWidget(b_del)
        self.buttons.append(b_del)
        self.list_layout.addLayout(bot_bar)

    def _make_asset_cb(self, idx):
        def _cb():
            if getattr(self.scroll_filter, "is_dragging", False): return
            self.cur_idx = idx
            for i, b in enumerate(self.buttons[:len(self.assets)]):
                b.setProperty("active", "true" if i == idx else "false")
                b.style().unpolish(b); b.style().polish(b)
            self.refresh()
        return _cb

    def _make_inv_cb(self, code, sec, label):
        def _cb():
            self.cur_inv_code, self.cur_inv_sec, self.cur_inv_label = code, sec, label
            for c, btn in self.inv_buttons:
                btn.setProperty("active", "true" if c == code else "false")
                btn.style().unpolish(btn); btn.style().polish(btn)
            a = self.assets[self.cur_idx]
            self.title_lbl.setText(u"%s • %s" % (a["id"], label))
            self.chart.inv_sec = sec
            self.chart.set_data(make_demo(a, sec), a, False)
            # Canli otomatik yenileme araligi (1dk: 3sn, 3-5dk: 4sn, 15dk: 8sn, saatlik: 15sn)
            poll_ms = 3000 if self.cur_inv_sec <= 60 else (4000 if self.cur_inv_sec <= 300 else (8000 if self.cur_inv_sec <= 900 else 15000))
            self.timer.setInterval(poll_ms)
            self.refresh()
        return _cb

    def _cycle_indicator(self):
        modes = ["SMA", "EMA", "BB", "MACD", "KAPALI"]
        nxt = modes[(modes.index(self.chart.mode_ind) + 1) % len(modes)]
        self.chart.mode_ind = nxt
        self.btn_ind.setText(u"IND: " + nxt)
        self.cfg["indicator"] = nxt
        save_config(self.cfg)
        self.chart._precalc(); self.chart.update()

    def _toggle_rsi(self):
        self.chart.show_rsi = not self.chart.show_rsi
        self.btn_rsi.setProperty("active", "true" if self.chart.show_rsi else "false")
        self.btn_rsi.style().unpolish(self.btn_rsi); self.btn_rsi.style().polish(self.btn_rsi)
        self.cfg["show_rsi"] = self.chart.show_rsi
        save_config(self.cfg)
        self.chart._precalc(); self.chart.update()

    def _open_search_dialog(self):
        dlg = SearchPairDialog(self)
        if dlg.exec_() == QtWidgets.QDialog.Accepted and dlg.selected_pair:
            self.assets.append(dlg.selected_pair)
            self.cfg["assets"] = self.assets
            save_config(self.cfg)
            self.cur_idx = len(self.assets) - 1
            self._rebuild_list(); self.refresh()

    def _on_del(self):
        if len(self.assets) <= 1: return
        del self.assets[self.cur_idx]
        self.cur_idx = max(0, self.cur_idx - 1)
        self.cfg["assets"] = self.assets
        save_config(self.cfg)
        self._rebuild_list(); self.refresh()

    def refresh(self):
        if not self.assets: return
        self.cur_idx = min(self.cur_idx, len(self.assets) - 1)
        a = self.assets[self.cur_idx]
        lbl = getattr(self, "cur_inv_label", u"1S")
        self.title_lbl.setText(u"%s • %s" % (a["id"], lbl))
        self.cur_req_id += 1
        req_id = self.cur_req_id

        def _fetch_task(proxy, asset, inv_code, inv_sec, rid):
            sym = asset["id"]
            q = urlencode({"symbol": sym, "interval": inv_code, "limit": 75})
            res = {"candles": [], "online": False}
            try:
                req = urllib_request.Request("%s/api/ohlc?%s" % (proxy.rstrip("/"), q))
                raw = urllib_request.urlopen(req, timeout=5.0).read()
                if isinstance(raw, bytes): raw = raw.decode("utf-8")
                d = json.loads(raw)
                if "candles" in d and len(d["candles"]) > 0:
                    res["candles"], res["online"] = d["candles"], True
            except Exception: pass
            if not res["candles"]: res["candles"] = make_demo(asset, inv_sec)
            self.signaler.dataReady.emit(res, rid)

        t = threading.Thread(target=_fetch_task, args=(DEFAULT_MI9T, a, self.cur_inv_code, self.cur_inv_sec, req_id))
        t.daemon = True
        t.start()

    def _on_data(self, d, rid):
        if rid != self.cur_req_id: return
        a = self.assets[self.cur_idx]
        c = d.get("candles", [])
        online = d.get("online", False)
        self.chart.set_data(c, a, online)
        if c:
            cur_p = c[-1]["c"]
            prev_p = getattr(self, "prev_price", None)
            col = "#00E676" if (prev_p is None or cur_p >= prev_p) else "#FF5252"
            self.prev_price = cur_p
            self.price_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: %s;" % col)
            self.price_lbl.setText(fmt_price(cur_p, a.get("dec", 2), a.get("unit", u"")))


def main():
    if "--install-desktop" in sys.argv:
        p = os.path.expanduser("~/.local/share/applications")
        if not os.path.exists(p): os.makedirs(p)
        f = open(os.path.join(p, "n9_market.desktop"), "w")
        cmd = "/usr/bin/python /home/user/MyDocs/n9_market_tracker.py\n"
        f.write("[Desktop Entry]\nType=Application\nName=MeeFin\nExec=" + cmd + "Icon=icon-l-browser\nTerminal=false\nCategories=Finance;\n")
        f.close()
        print("Desktop shortcut created.")
        return

    app = QtWidgets.QApplication(sys.argv)
    w = MainWin()
    w.showFullScreen()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()