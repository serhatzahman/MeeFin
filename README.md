# MeeFin 📈

> **Nokia N9 (MeeGo 1.2 Harmattan) için Gerçek Zamanlı Finans & Mum Grafiği Terminali**  
> *Real-Time Market Tracker & Candlestick Chart Terminal for Nokia N9 (MeeGo 1.2 Harmattan)*

[![Platform](https://img.shields.io/badge/Platform-MeeGo%201.2%20Harmattan-blue.svg)](https://en.wikipedia.org/wiki/MeeGo)
[![Device](https://img.shields.io/badge/Device-Nokia%20N9%20%28RM--696%29-green.svg)](https://en.wikipedia.org/wiki/Nokia_N9)
[![UI Framework](https://img.shields.io/badge/Framework-PySide%20Qt%204.7.4-brightgreen.svg)](https://wiki.qt.io/PySide)
[![Python Client](https://img.shields.io/badge/Python%20Client-2.6-yellow.svg)](https://www.python.org/)
[![Proxy Engine](https://img.shields.io/badge/Proxy%20Engine-Python%203%20TLS%201.3-orange.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 🌐 Diller / Languages
- [English Documentation](#-english-documentation)
- [Türkçe Dokümantasyon](#-türkçe-dokümantasyon)

---

# 🇬🇧 English Documentation

## 📖 Overview
**MeeFin** is a high-performance financial tracking terminal and candlestick charting application developed natively for the legendary **Nokia N9** running **MeeGo 1.2 Harmattan** (Qt 4.7.4 / PySide, Python 2.6).

Because Nokia N9's embedded Linux kernel and OpenSSL 0.9.8 stack do not support modern TLS 1.2/1.3 cipher suites required by modern crypto/stock exchanges, MeeFin utilizes a lightweight **TLS Bridge Proxy** (`n9_tls_proxy.py`) running on any local companion device (Android / Termux, Raspberry Pi, or PC) to fetch real-time OHLCV data from **Binance** and **Yahoo Finance**, presenting it as clean, fast JSON to the Nokia N9.

```text
                      LOCAL WI-FI NETWORK                               INTERNET
┌───────────────────────┐             ┌─────────────────────────┐             ┌─────────────────────┐
│       Nokia N9        │  HTTP JSON  │    Xiaomi Mi 9T / PC    │  TLS 1.3    │   Binance REST API  │
│  (MeeGo 1.2 Harmattan)│ ──────────> │   (Termux / Python 3)   │ ──────────> │  (Crypto OHLCV)     │
│  - PySide / Qt 4.7.4  │  Port 8083  │   - n9_tls_proxy.py     │   HTTPS     ├─────────────────────┤
│  - AMOLED Dark Theme  │ <────────── │   - In-memory Caching   │ ──────────> │  Yahoo Finance API  │
│  - Real-time Engine   │             │   - Symbol Resolution   │             │  (Stocks/Gold/Forex)│
└───────────────────────┘             └─────────────────────────┘             └─────────────────────┘
```

---

## ✨ Features
- **Real-Time Candlestick Charting**: Live candlestick charts supporting **1dk (1m)**, **3dk (3m)**, **5dk (5m)**, **15dk (15m)**, **1S (1h)**, **4S (4h)**, **1G (1d)**, and **1H (1wk)** timeframes.
- **Auto-Updating Live Ticker**: Automatically pulls live ticks in the background every 3–4 seconds without needing to press the refresh button. The current forming candle dynamically morphs in real time!
- **Dynamic Price Flash**: Price header glows neon green (`#00E676`) on upward ticks and bright red (`#FF5252`) on downward ticks.
- **Technical Indicators**:
  - **SMA** (Simple Moving Average 7 & 20)
  - **EMA** (Exponential Moving Average 9 & 21)
  - **BB** (Bollinger Bands 20, 2.0 std dev)
  - **MACD** (12, 26, 9 with dual-color Histogram)
  - **RSI** (14-period Relative Strength Index with dedicated 30/70 sub-chart)
  - **Volume Bars** integrated into chart base.
- **AMOLED Pitch-Black Interface**: Pure `#000000` AMOLED dark design tailored to the Nokia N9's 3.9" 854x480 ClearBlack AMOLED display.
- **Collapsible Sidebar Menu**: Tapping `[ ◀ ]` / `[ ☰ ]` folds away the asset list, expanding the candlestick chart to the full 854px screen width.
- **Touch-Friendly Crosshair**: Drag across candles to inspect Date/Time, Open, High, Low, Close, and percentage change.
- **Search & Add Custom Pairs**: Add any crypto symbol (Binance) or stock/commodity/forex ticker (Yahoo Finance) via the built-in search dialog.
- **Native Harmattan Integration**: 80x80 squircle icon and `.desktop` launcher entry in `/usr/share/applications/meefin.desktop`.

---

## 📂 Project Structure
```text
meefin/
├── meefin.py           # Main client application for Nokia N9 (Python 2.6 / PySide)
├── n9_tls_proxy.py     # Local TLS 1.3 bridge server (Python 3.8+)
├── meefin.desktop      # MeeGo Harmattan application launcher file
├── meefin.png          # Official 80x80 Harmattan squircle icon
├── install_n9.sh       # One-command installer for Nokia N9
├── start_proxy.sh      # One-command proxy runner (Termux / Linux / macOS)
├── README.md           # Documentation (English & Turkish)
└── LICENSE             # MIT License
```

---

## 🚀 Installation & Setup

### Part 1: Start the Companion Proxy Server (on Android / PC)

#### Option A: On an Android Phone using Termux (e.g. Xiaomi Mi 9T)
1. Open **Termux** on your Android device (must be on the same Wi-Fi as your Nokia N9).
2. Install Python:
   ```bash
   pkg update && pkg install python -y
   ```
3. Start the proxy:
   ```bash
   termux-wake-lock
   python n9_tls_proxy.py --port 8083
   ```
   *(To run silently in the background: `nohup python n9_tls_proxy.py --port 8083 > ~/proxy.log 2>&1 &`)*
4. Note your Android device's local IP (e.g., `192.168.8.239`).

#### Option B: On a Windows / Linux / macOS PC
Run in PowerShell or Terminal:
```bash
python3 n9_tls_proxy.py --port 8083
```

---

### Part 2: Install MeeFin on Nokia N9

1. In Windows PowerShell, copy the project files to your Nokia N9:
   ```powershell
   scp -O -oHostKeyAlgorithms=+ssh-rsa -oPubkeyAcceptedKeyTypes=+ssh-rsa meefin.py meefin.png meefin.desktop install_n9.sh user@<NOKIA_N9_IP>:/home/user/MyDocs/
   ```
2. In the Nokia N9 Terminal, switch to root and run the installer:
   ```bash
   devel-su
   # Password is: rootme
   sh /home/user/MyDocs/install_n9.sh
   ```
3. Configure the proxy IP (if different from default `192.168.8.239`):
   Open `~/.n9_market_config.json` and set `"proxy_url": "http://<YOUR_PROXY_IP>:8083"`.

4. **Launch**:
   - Tap the **MeeFin** icon from the Nokia N9 Application Grid, OR
   - Run from terminal:
     ```bash
     DISPLAY=:0 XAUTHORITY=/home/user/.Xauthority python /opt/meefin/meefin.py
     ```

---

# 🇹🇷 Türkçe Dokümantasyon

## 📖 Genel Bakış
**MeeFin**, **Nokia N9** (**MeeGo 1.2 Harmattan**, Qt 4.7.4 / PySide, Python 2.6) için özel olarak geliştirilmiş, gerçek zamanlı bir finans takip ve borsa mum grafiği uygulamasıdır.

Nokia N9'un 2011 yılından kalma eski OpenSSL 0.9.8 kütüphanesi modern TLS 1.2/1.3 şifreleme protokollerini desteklemediği için, Binance ve Yahoo Finance gibi modern borsa API'lerine doğrudan bağlanamaz. MeeFin bu sorunu yerel ağda (aynı Wi-Fi) çalışan hafif bir **Finans Köprü Sunucusu** (`n9_tls_proxy.py`) ile çözer. Köprü sunucusu verileri TLS 1.3 ile çeker, sade JSON olarak Nokia N9'a aktarır.

---

## ✨ Özellikler
- **Gerçek Zamanlı Mum Grafikleri (Candlestick)**: **1dk**, **3dk**, **5dk**, **15dk**, **1S**, **4S**, **1G**, **1H** periyotlarında canlı mumlar.
- **Otomatik Canlı Akış**: Yenile butonuna basmaya gerek kalmadan, 1dk periyodunda her 3 saniyede bir arka planda otomatik güncellenir. Oluşmakta olan son mum ekranda canlı olarak hareket eder.
- **Anlık Fiyat Flaş Animasyonu**: Fiyat yükseldiğinde başlık neon yeşil (`#00E676`), düştüğünde canlı kırmızı (`#FF5252`) renge döner.
- **Teknik İndikatörler**:
  - **SMA** (Basit Hareketli Ortalama 7 & 20)
  - **EMA** (Üstel Hareketli Ortalama 9 & 21)
  - **BB** (Bollinger Bantları 20, 2.0 standart sapma)
  - **MACD** (12, 26, 9 periyotlu çizgi ve iki renkli histogram)
  - **RSI** (14 periyotlu Göreceli Güç Endeksi, 30/70 çizgili alt grafik)
  - **Hacim Barları (Volume)**.
- **Saf AMOLED Siyah Tasarım**: Nokia N9'un 3.9 inç 854x480 ClearBlack AMOLED ekranına özel saf `#000000` siyah arayüz.
- **Kapanabilir Yan Menü**: Sol üstteki `[ ◀ ]` butonuna dokunulduğunda sol liste gizlenir ve grafik tüm ekrana (854 px) yayılır.
- **Dokunmatik İmleç (Crosshair)**: Mumların üzerine dokunup parmağınızı kaydırarak Açılış, Yüksek, Düşük, Kapanış, Hacim ve % değişim değerlerini anlık inceleyebilirsiniz.
- **Parite Ekleme & Katalog Arama**: Arama penceresiyle Binance'deki tüm kriptoları veya Yahoo Finance'deki hisse senedi, altın, gümüş, petrol ve döviz kurlarını ekleyebilirsiniz.
- **N9 Başlatıcı Simgesi**: Harmattan squircle standartlarında 80x80 piksel uygulama ikonu ile menüye tam entegrasyon.

---

## 🛠️ Kurulum Adımları

### 1. Adım: Köprü Sunucusunu Başlatın (Android Telefon veya PC)

#### Android Telefondan (Termux ile - Örn: Xiaomi Mi 9T)
1. Telefonunuza **Termux** uygulamasını yükleyin (Nokia N9 ile aynı Wi-Fi ağında olmalıdır).
2. Python kurun:
   ```bash
   pkg update && pkg install python -y
   ```
3. `n9_tls_proxy.py` dosyasını çalıştırın:
   ```bash
   termux-wake-lock
   python n9_tls_proxy.py --port 8083
   ```
   *(Arka planda kesintisiz çalışması için: `nohup python n9_tls_proxy.py --port 8083 > ~/proxy.log 2>&1 &`)*
4. Telefonunuzun yerel Wi-Fi IP adresini öğrenin (`ifconfig` ile; örn: `192.168.8.239`).

#### Bilgisayardan (Windows / Linux / macOS)
Terminal veya PowerShell'de:
```bash
python3 n9_tls_proxy.py --port 8083
```

---

### 2. Adım: Nokia N9'a MeeFin'i Kurun

1. Windows PowerShell'den dosyaları Nokia N9'a kopyalayın:
   ```powershell
   scp -O -oHostKeyAlgorithms=+ssh-rsa -oPubkeyAcceptedKeyTypes=+ssh-rsa meefin.py meefin.png meefin.desktop install_n9.sh user@<NOKIA_N9_IP>:/home/user/MyDocs/
   ```
2. Nokia N9 terminalinde (`devel-su` ile root olarak) kurulum scriptini çalıştırın:
   ```bash
   devel-su
   # Şifre: rootme
   sh /home/user/MyDocs/install_n9.sh
   ```
3. **Başlatma**:
   - Nokia N9 uygulama menüsündeki **MeeFin** simgesine dokunarak açabilirsiniz.
   - Veya terminalden:
     ```bash
     DISPLAY=:0 XAUTHORITY=/home/user/.Xauthority python /opt/meefin/meefin.py
     ```

---

## 🔧 Teknik Notlar & Çözülen Sorunlar (MeeGo Harmattan)

1. **Python GIL & Thread Güvenliği**:
   PySide 1.0.8 (MeeGo Harmattan) sürümünde `QThread.terminate()` çağrıldığında POSIX thread'i aniden sonlandırıldığı için Python GIL kilitlenmekte ve `Fatal Python error: This thread state must be current when releasing` hatasıyla çökmekteydi. MeeFin, arkaplan isteklerini Python'un yerel `threading.Thread` kütüphanesi ve `QtCore.QObject` sinyalleri ile yöneterek bu çökmeyi %100 engellemiştir.

2. **N9 TTY Tampon Taşması (Buffer Overflow)**:
   Nokia N9 Linux çekirdeğinin sanal terminal tamponu 4096 bayttır (`N_TTY_BUF_SIZE = 4096`). SSH terminaline büyük kod blokları yapıştırıldığında karakterler yutulur. Bu nedenle kodlar terminale yapıştırılmak yerine doğrudan `scp` ile binary olarak aktarılmalıdır.

3. **Modern OpenSSH Uyumluluğu**:
   Windows 10/11 OpenSSH istemcisi eski `ssh-rsa` anahtar türlerini varsayılan olarak devre dışı bırakmıştır. N9'a bağlanırken `-O -oHostKeyAlgorithms=+ssh-rsa -oPubkeyAcceptedKeyTypes=+ssh-rsa` parametreleri kullanılır.

4. **Termux:Widget Entegrasyonu**:
   Android ana ekranına tek dokunuşla proxy açıp kapatmak için `~/.shortcuts/tasks/` dizinine başlatıcı scriptler eklenebilir.

---

## 📄 Lisans
Bu proje [MIT Lisansı](LICENSE) altında lisanslanmıştır.
