# sweeplab# SweepLab — Likidite Süpürme Backtest Terminali

Tek dosyalık, sunucusuz, tamamen tarayıcıda çalışan bir forex/emtia backtest aracı. TradingView'ın görsel deneyimine yakın bir arayüzde **kendi OHLC verinizi** yükleyip, **kendi strateji kodunuzu** yazıp, sonuçları **istatistiksel dürüstlük** süzgecinden geçirerek test edersiniz.

**Canlı demo:** https://samiboran.github.io/sweeplab/

Çekirdek soru şu: *Gördüğünüz kazanç gerçek bir edge mi, yoksa şans mı?* SweepLab her testin yanında aynı parametrelerle bir rastgele kontrol grubu çalıştırır ve sonucu açıkça etiketler.

---

## Ne yapar

- **Veri yükleme** — Twelve Data formatında JSON veya OHLC CSV. Sürükle-bırak ya da yapıştır. Birden çok sembol (XAUUSD, EURUSD, SOLUSDT…) ayrı ayrı saklanır, tarayıcı belleğinde (localStorage) kalıcıdır.
- **Mum grafiği** — Lightweight Charts (TradingView'ın açık kaynak kütüphanesi). İşlem giriş/çıkış okları ve strateji referans seviyeleri (örn. Asya seansı high/low) grafik üzerine çizilir.
- **Strateji editörü** — CodeMirror tabanlı, JavaScript. Hazır yardımcılar: `ATR`, `EMA`, `SMA`, seans kontrolü, en yüksek/en düşük. Varsayılan şablon: mekanik "Judas Swing" likidite süpürme stratejisi.
- **Gerçekçi motor** — Lookahead bias yok. Stop ve hedef her mumda sırayla kontrol edilir; aynı mumda ikisi de tetiklenirse kötümser (stop önce) kabul edilir. Opsiyonel cross-margin likidasyon simülasyonu.
- **Dürüstlük katmanı** — Her test için rastgele kontrol grubu, t-istatistiği, düşük örneklem (n<30) uyarısı ve "rastgeleden ayrışmıyor" bayrağı.
- **Dönemsel rapor** — Sonuçlar 3 veya 6 aylık bloklara bölünür; her blok yeşil/kırmızı kart olarak gösterilir.
- **Train/Test ayrımı** — %70 in-sample / %30 out-of-sample, overfitting kontrolü için.
- **Çoklu sembol** — Aynı stratejiyi tüm yüklü veri setlerinde çalıştırıp yan yana karşılaştırır.
- **Dışa aktarma** — İşlem listesi ve istatistikler CSV / JSON.

---

## Kullanım

1. **Veri yönet** → JSON/CSV yükleyin veya yapıştırın.
2. Sol panelden parametreleri ayarlayın (seans saatleri, süpürme eşikleri, R:Ödül, filtreler).
3. Saat dilimini seçin (veri UTC okunur; seans saatleri seçtiğiniz dilime göre yorumlanır).
4. **Backtest çalıştır** → verdict, kartlar, grafik, equity eğrisi ve dönemsel rapor gelir.

### Veri formatı

Twelve Data `time_series` çıktısı doğrudan çalışır:

```json
{
  "meta": { "symbol": "XAU/USD", "interval": "15min" },
  "values": [
    { "datetime": "2025-03-19 15:45:00", "open": "3036.4", "high": "3036.8", "low": "3034.9", "close": "3036.4" }
  ]
}
```

CSV de kabul edilir (`datetime,open,high,low,close`). Sıralama önemli değil; araç kronolojik sıralar ve tekrarlı barları temizler.

`XAUUSD_15min_ornek.json` deposunda örnek (sentetik) bir veri seti bulunur — yalnızca aracı denemek içindir, gerçek piyasa değildir.

---

## Veri kaynağı / API hakkında

SweepLab **veriyi kendisi canlı çekmez** — bilinçli bir tasarım tercihidir. Veriyi siz sağlarsınız (kendi Twelve Data / HistData / broker dışa aktarımınız). Böylece araç herhangi bir sağlayıcıya, herhangi bir API anahtarına veya CORS yapılandırmasına bağımlı kalmaz; isteyen kendi veri akışını bağlar.

İleride doğrudan API'den canlı veri çekmek isterseniz: tarayıcıdan Twelve Data'ya doğrudan erişim CORS nedeniyle engellenir. Çözüm, isteği ileten küçük bir vekil (proxy) — örneğin bir Cloudflare Worker — kurmak ve aracı ona yöneltmektir. Mimari buna izin verecek şekilde tasarlandı.

---

## Strateji yazma

Editördeki kod, her mumda çağrılan bir `uret(ctx)` fonksiyonu döndürür:

```js
return {
  uret(ctx){
    const { bar, i, p, h, s, pozisyon } = ctx;
    // ... mantığınız ...
    // dönüş: null  veya  { yon:'long'|'short', stop:<fiyat>, sebep:'...' }
  }
}
```

| Alan | Açıklama |
|------|----------|
| `bar` | `{ time, open, high, low, close, datetime }` |
| `i` | Mevcut mum indeksi |
| `c` | Tüm mumlar (yalnızca `i`'ye kadar olanı kullanın — lookahead yok) |
| `p` | Parametreler (sol paneldeki değerler) |
| `h` | Yardımcılar: `h.atr(p,i)` `h.ema(p,i)` `h.sma(p,i)` `h.seansIcinde(i,"0300-0900")` `h.enYuksek(i,n)` `h.enDusuk(i,n)` |
| `s` | Kalıcı durum (mumlar arası taşınır, her testte sıfırlanır) |
| `pozisyon` | Açık pozisyon ya da `null` |

Take-profit, dönen `stop` ile Risk:Ödül oranından otomatik hesaplanır. Grafikte referans çizgisi çizmek için `s.refUst` / `s.refAlt` ayarlayın.

---

## Yerelde çalıştırma

Bağımlılık yok, derleme yok. `index.html` dosyasını tarayıcıda açın. Grafik ve editör kütüphaneleri CDN'den geldiği için ilk açılışta internet gerekir. localStorage'ın çalışması için dosyayı yerelde veya yayınlanmış (https) bir adreste açın.

## Yayınlama (GitHub Pages)

Saf statik dosya olduğu için derleme adımı yoktur:

1. Dosyayı `index.html` olarak repoya koyun.
2. Settings → Pages → Deploy from a branch → `main` / `root`.

Güncelleme: `git add . && git commit -m "..." && git push`.

---

## Teknik

Kütüphaneler (CDN üzerinden): Lightweight Charts, Chart.js, CodeMirror. Çerçeve yok, build yok, tek HTML dosyası.

## Uyarı

Bu bir araştırma/eğitim aracıdır, finansal tavsiye değildir. Geçmiş performans gelecek sonuçların garantisi değildir. Kaldıraçlı işlemler yüksek risk taşır.
