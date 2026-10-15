#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Xiaomi Mi 9T (192.168.8.239:8083) Üzerinden Nokia N9 (192.168.8.144) İçin
Dinamik Parite Destekli Finans Köprü Sunucusu
-------------------------------------------------------------------------
Özellikler:
  - Nokia N9'dan dinamik olarak eklenen HERHANGİ BİR yeni pariteyi
    (kripto, hisse, endeks, döviz, emtia) otomatik algılar.
  - Kripto ise Binance üzerinden (örn. BTC, ETH, SOL, DOGE, AVAX),
    hisse/emtia/endeks ise Yahoo Finance üzerinden (örn. NVDA, TSLA, GC=F, USDTRY=X)
    OHLC mum verilerini TLS 1.3 ile çeker ve N9'a sade JSON olarak sunar.

Çalıştırma:
  python3 n9_tls_proxy.py --port 8083
"""

import argparse
import json
import os
import time
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

MI9T_IP = "192.168.8.239"
N9_IP = "192.168.8.144"
DEFAULT_PORT = 8083

# Sabit Eşleştirmeler (Kullanıcı yeni sembol eklerse dinamik olarak da sorgulanır)
DEFAULT_MAP = {
    "BTC":    {"source": "binance", "ticker": "BTCUSDT"},
    "ETH":    {"source": "binance", "ticker": "ETHUSDT"},
    "XRP":    {"source": "binance", "ticker": "XRPUSDT"},
    "SOL":    {"source": "binance", "ticker": "SOLUSDT"},
    "DOGE":   {"source": "binance", "ticker": "DOGEUSDT"},
    "BNB":    {"source": "binance", "ticker": "BNBUSDT"},
    "AVAX":   {"source": "binance", "ticker": "AVAXUSDT"},
    "XAU":    {"source": "yahoo",   "ticker": "GC=F"},     # Ons Altın
    "XAG":    {"source": "yahoo",   "ticker": "SI=F"},     # Ons Gümüş
    "BRENT":  {"source": "yahoo",   "ticker": "BZ=F"},     # Brent Petrol
    "NASDAQ": {"source": "yahoo",   "ticker": "^IXIC"},    # Nasdaq Composite
    "SP500":  {"source": "yahoo",   "ticker": "^GSPC"},    # S&P 500
    "USDTRY": {"source": "yahoo",   "ticker": "USDTRY=X"},  # Dolar / TL
}

CACHE = {}
CACHE_TTL_SEC = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}


def fetch_url_json(url, timeout=8):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw)


def fetch_binance_ohlc(binance_symbol, interval="1h", limit=80):
    b_map = {"1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d", "1wk": "1w"}
    params = urllib.parse.urlencode({
        "symbol": binance_symbol,
        "interval": b_map.get(interval, "1h"),
        "limit": min(int(limit), 120),
    })
    url = f"https://api.binance.com/api/v3/klines?{params}"
    rows = fetch_url_json(url)
    candles = []
    for r in rows:
        candles.append({
            "t": int(r[0]) // 1000,
            "o": float(r[1]),
            "h": float(r[2]),
            "l": float(r[3]),
            "c": float(r[4]),
            "v": float(r[5]),
        })
    return candles


def fetch_yahoo_ohlc(yahoo_symbol, interval="1h", limit=80):
    y_map = {
        "1m":  ("1m",  "1d"),
        "3m":  ("2m",  "1d"),
        "5m":  ("5m",  "1d"),
        "15m": ("15m", "5d"),
        "1h":  ("60m", "1mo"),
        "4h":  ("60m", "3mo"),
        "1d":  ("1d",  "6mo"),
        "1wk": ("1wk", "2y"),
    }
    y_int, y_range = y_map.get(interval, ("60m", "1mo"))
    encoded_sym = urllib.parse.quote(yahoo_symbol)
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded_sym}"
        f"?interval={y_int}&range={y_range}"
    )
    data = fetch_url_json(url)
    result = data["chart"]["result"][0]
    timestamps = result.get("timestamp", [])
    quote = result["indicators"]["quote"][0]
    opens = quote.get("open", [])
    highs = quote.get("high", [])
    lows = quote.get("low", [])
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    raw_candles = []
    for i, ts in enumerate(timestamps):
        o = opens[i] if i < len(opens) else None
        h = highs[i] if i < len(highs) else None
        l = lows[i] if i < len(lows) else None
        c = closes[i] if i < len(closes) else None
        v = volumes[i] if (i < len(volumes) and volumes[i] is not None) else 0.0
        if None in (o, h, l, c):
            continue
        raw_candles.append({
            "t": int(ts),
            "o": float(o),
            "h": float(h),
            "l": float(l),
            "c": float(c),
            "v": float(v),
        })

    if interval == "4h" and len(raw_candles) >= 4:
        agg = []
        for i in range(0, len(raw_candles), 4):
            chunk = raw_candles[i:i + 4]
            agg.append({
                "t": chunk[0]["t"],
                "o": chunk[0]["o"],
                "h": max(x["h"] for x in chunk),
                "l": min(x["l"] for x in chunk),
                "c": chunk[-1]["c"],
                "v": sum(x["v"] for x in chunk),
            })
        raw_candles = agg

    return raw_candles[-int(limit):]


def get_ohlc_auto(symbol, interval="1h", limit=80):
    symbol = symbol.strip().upper()
    cache_key = f"{symbol}_{interval}_{limit}"
    now = time.time()
    if cache_key in CACHE:
        ts, cached = CACHE[cache_key]
        if now - ts < CACHE_TTL_SEC:
            return cached

    # 1. Bilinen harita kontrolü
    if symbol in DEFAULT_MAP:
        info = DEFAULT_MAP[symbol]
        if info["source"] == "binance":
            candles = fetch_binance_ohlc(info["ticker"], interval=interval, limit=limit)
        else:
            candles = fetch_yahoo_ohlc(info["ticker"], interval=interval, limit=limit)
        CACHE[cache_key] = (now, candles)
        return candles

    # 2. Dinamik Kripto kontrolü (Örn: SOL, DOGE -> SOLUSDT)
    binance_ticker = symbol if symbol.endswith("USDT") else f"{symbol}USDT"
    try:
        candles = fetch_binance_ohlc(binance_ticker, interval=interval, limit=limit)
        if candles:
            CACHE[cache_key] = (now, candles)
            return candles
    except Exception:
        pass

    # 3. Dinamik Yahoo Finance kontrolü (Örn: NVDA, TSLA, AAPL, GC=F)
    try:
        candles = fetch_yahoo_ohlc(symbol, interval=interval, limit=limit)
        if candles:
            CACHE[cache_key] = (now, candles)
            return candles
    except Exception:
        pass

    raise ValueError(f"Sembol bulunamadı: {symbol}")


class N9ProxyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/api/ohlc":
            symbol = params.get("symbol", ["BTC"])[0].upper()
            interval = params.get("interval", ["1h"])[0]
            limit = int(params.get("limit", ["80"])[0])

            try:
                candles = get_ohlc_auto(symbol, interval=interval, limit=limit)
                body = json.dumps({
                    "symbol": symbol,
                    "interval": interval,
                    "count": len(candles),
                    "candles": candles,
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except Exception as exc:
                err_body = json.dumps({
                    "error": str(exc),
                    "symbol": symbol,
                }).encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(err_body)))
                self.end_headers()
                self.wfile.write(err_body)
            return

        status_html = (
            "<html><head><meta charset='utf-8'><title>N9 Finans Köprüsü</title></head>"
            "<body style='background:#06080C;color:#EAECEF;font-family:sans-serif;padding:20px;'>"
            f"<h2>Xiaomi Mi 9T ({MI9T_IP}:{DEFAULT_PORT}) Finans Köprüsü Aktif</h2>"
            "<p>Dinamik Parite Desteği: Kripto (Binance) ve Hisse/Emtia/Döviz (Yahoo Finance) otomatik sorgulanır.</p>"
            "</body></html>"
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(status_html)))
        self.end_headers()
        self.wfile.write(status_html)

    def log_message(self, fmt, *args):
        client_ip = self.client_address[0]
        tag = "Nokia-N9" if client_ip == N9_IP else client_ip
        print(f"[Mi9T:8083 <- {tag}] {fmt % args}")


def main():
    parser = argparse.ArgumentParser(description="Dinamik N9 Finans Köprü Sunucusu")
    parser.add_argument("--host", default="0.0.0.0", help="Dinlenecek IP")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Dinlenecek port")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), N9ProxyHandler)
    print("==============================================================")
    print(f" Mi 9T Dinamik Finans Köprüsü Aktif : http://{MI9T_IP}:{args.port}")
    print(f" Hedef Nokia N9 IP                  : {N9_IP}")
    print("==============================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSunucu kapatıldı.")


if __name__ == "__main__":
    main()