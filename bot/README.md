# SweepLab Bot — Bağımsız Python Trading Botu

TradingView/Pine yolu terk edildi (ücretli plan + 3. parti köprü servisi
gerektiriyordu). Bunun yerine doğrudan Python: TradingView'a hiç ihtiyaç
yok, backtest'te doğrulanmış aynı likidite süpürme (liquidity sweep)
reversal mantığı burada çalışıyor.

Bu klasördeki kod, kök dizindeki `index.html` (SweepLab backtest terminali)
ile aynı stratejinin canlı, otomatik yürütmeli halidir. `index.html` veri
yüklenip strateji kodu **elle** yazılan bir backtest aracıyken, `bot/`
Binance'e doğrudan bağlanıp sinyal üretir ve (fazına göre) emir açar.

## Mimari

```
bot/
  config.py           Tüm parametreler (.env üzerinden) — sabit kodlanmış değer yok
  models.py            Candle / Swing / Signal / Position / Trade veri modelleri
  signals.py            SAF strateji mantığı: fraktal swing, trend, süpürme+fitil tespiti
  ws_client.py           Binance public kline WebSocket (4 sembol, tek combined stream)
  strategy_engine.py     Sinyal üretimini risk kontrolüne, yürütmeye, bildirime bağlar
  risk.py                Günlük zarar limiti, maks. eşzamanlı pozisyon, kill switch kapısı
  execution.py            Binance Futures REST (python-binance) — entry + SL + TP emirleri
  notifier.py             Telegram bildirimi + /dur /devam /durum komutları
  state.py                 Süreçler arası paylaşılan durum (bot_state/state.json)
  main.py                   Giriş noktası: python -m bot.main
panel/
  app.py               Streamlit izleme paneli (pozisyonlar, geçmiş, trend, İZLE seviyesi)
tests/
  test_signals.py, test_risk.py, ...    Strateji ve güvenlik mantığının birim testleri
```

Veri katmanı ile yürütme katmanı bilinçli olarak ayrıdır: fiyat akışı
Binance'in **genel** (public, API key gerektirmeyen) spot kline soketinden
gelir; emirler ise **Binance Futures** REST API'si üzerinden açılır. Bu,
task tanımındaki mimariyle birebir örtüşür.

## Strateji özeti

1. **Fraktal swing** (`swing_window`, varsayılan 5): bir mum, kendisinden
   önce ve sonra `w` bar içinde en yüksek/en düşük ise swing high/low'dur.
   Swing, ancak `w` bar sonra doğrulanabilir (lookahead yok).
2. **Trend**: son iki swing-high yükseliyorsa VE son iki swing-low
   yükseliyorsa (HH+HL) → yukarı trend. Simetrik olarak LH+LL → aşağı trend.
3. **Süpürme + reddetme**: yukarı trendde fiyat son swing-low'un altına
   sarkıp (likidite süpürme) kapanışta geri üstüne dönerse VE alt fitil
   mumun toplam aralığının en az `%wick_min_pct`'i (varsayılan %40) ise →
   **long** sinyali. Aşağı trendde simetriği → **short**.
4. **Emir seviyeleri**: `entry = kapanış`, `stop = süpürülen mumun ucu ±
   stop_buffer_pct`, `target = entry ± RR * risk` (varsayılan RR=2.0).

Referans backtest (AVAX, ~11 ay, w=5 + fitil filtresi, RR=2, tek TP):
n=1782, kazanma oranı %64.6, beklenti 0.944R/işlem — komisyon/slippage
hariç, gerçek sonuç bunun altında kalır.

## Güvenlik katmanları (CRITICAL_safety_requirements)

| Gereksinim | Nerede uygulanıyor |
|---|---|
| Testnet önce | `BOT_PHASE=testnet_auto` → `Config.is_testnet` → `python-binance` `testnet=True` |
| Sadece "Futures Trading" izni, Withdrawal KAPALI | API key'i Binance panelinde bu şekilde oluşturmak kullanıcı sorumluluğu; kod hiçbir çekim (withdraw) endpoint'i çağırmaz |
| Günlük zarar limiti | `risk.py::RiskManager.evaluate_daily_loss` — gün başı bakiyeye göre %'lik zarar hesaplanır, aşılınca `can_open_position` yeni işlemi reddeder + Telegram bildirimi |
| Maks. eşzamanlı pozisyon | `risk.py::RiskManager.can_open_position` — `MAX_CONCURRENT_POSITIONS` (varsayılan 1) |
| Kill switch | Dosya bayrağı `bot_state/DUR` (panel butonu veya Telegram `/dur`); her sinyalde kontrol edilir |
| Ayarlanabilir kaldıraç | `LEVERAGE` ortam değişkeni, sabit kodlanmamış |

Kill switch'i kaldırmak / günü devam ettirmek için panelde "Devam et"
butonu veya Telegram'da `/devam` yazılır. `/durum` anlık durumu (faz, kill
switch, günlük PnL, açık pozisyon sayısı) döner.

## Fazlı geçiş (phased_rollout)

`BOT_PHASE` ortam değişkeni ile kontrol edilir:

1. **`testnet_auto`** — Binance Futures **testnet** + tam otomatik emir.
   Sahte parayla, gerçek API mekanizmasıyla doğrulama. Gerçek API key'e
   geçmeden önce en az birkaç gün/hafta burada sorunsuz çalışmalı.
2. **`live_notify_only`** — gerçek hesap ama SADECE Telegram bildirimi;
   `auto_execute=False` olduğu için `strategy_engine.py` emir açmaz, Sami
   sinyali görüp elle açar.
3. **`live_auto`** — gerçek hesap + tam otomatik, küçük sermaye (~$150) ve
   günlük zarar limitiyle.

## Kurulum ve çalıştırma

```bash
pip install -r requirements.txt
cp .env.example .env   # değerleri doldurun (bkz. yukarıdaki tablo)

# Botu başlat (WebSocket + sinyal + risk + yürütme + Telegram)
python -m bot.main

# Panel — ayrı bir terminalde
streamlit run panel/app.py
```

Testler (strateji mantığı ve risk katmanı için — ağ/API gerektirmez):

```bash
pytest tests/ -q
```

## Panel

Streamlit tercih edildi (Flask'a göre daha az kod, hazır tablo/metrik
bileşenleri, tek dosyada dashboard). Panel `bot_state/state.json`'ı okuyarak
şunları gösterir: aktif pozisyonlar, geçmiş işlemler, her sembol için
güncel trend + bir sonraki tetik seviyesi (Pine v4'teki "İZLE" çizgisinin
karşılığı), günlük PnL ve kill switch kontrolü.

**Açık soru:** Panel'i 7/24 çalışır tutmak için bir VPS/sunucu mevcut mu,
yoksa bu da mı kurulacak? Yoksa botu ve paneli aynı sürekli çalışan
makinede (`systemd` servisi veya `tmux`/`screen` içinde) çalıştırmak
gerekecek.

## Uyarı

Bu bir trading botudur, finansal tavsiye değildir. Geçmiş backtest
performansı gelecekteki sonuçların garantisi değildir. Kaldıraçlı vadeli
işlemler yüksek risk taşır; testnet doğrulaması tamamlanmadan gerçek
paraya geçilmemelidir.
