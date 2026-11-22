# Gelir modeli — PARK (S12)

> **Durum: park edildi.** Kod yok, cüzdan yok, hesap yok. Bu belge yalnız gerçek bir kitle
> oluştuğunda nereden başlanacağını hatırlatır. Aşağıdakiler hukuki ya da mali tavsiye değildir;
> her adım öncesinde sermaye piyasası alanında çalışan bir avukat ve mali müşavirle konuşulmalı.

## Ne satılabilir (ne satılmaz)

Satılacak olan **veri ve erişim**, asla yön/öneri değil. Site "haber/veri" dilinde kalır.

1. **Türkiye pazarı türetilmiş veri — ücretli API katmanı.** Yabancı kullanıcılar, botlar ve
   uygulamalar için Türkçe/Türkiye'ye özgü, başka yerde hazır bulunmayan seriler:
   - TL katmanı: gram altın / gram gümüş TL, dolar/TL, BIST 100'ün dolar bazında seyri, 1g/7g/30g/YTD
     değişimleri, 200 günlük ortalamaya uzaklık;
   - makro hava seviyesi + 9 kural işareti + zaman damgalı sicil (dondurma tarihinden beri canlı);
   - ortalamalara göre konum, günün hareketlileri ve anomaliler (BIST dahil);
   - Türkçe şablon cümleler (bot/uygulama içinde doğrudan gösterilebilir).
   Ücretsiz katman bugünkü gibi kalır (günlük dosyalar, atıfla). Ücretli katman: daha uzun geçmiş,
   gün içi güncelleme, toplu indirme, kararlı SLA, ticari kullanım hakkı.
2. **Toplu / yapay zekâ ajanı erişimi için makine ödemesi.** İnsan ziyaretçiler ve arama
   motorları ücretsiz kalır; yüksek hacimli otomatik erişim ücretli olur. İki aday:
   - **x402** (HTTP 402 "Payment Required" üzerine kurulu, istek başına küçük ödeme protokolü);
   - **Cloudflare'in tarayıcı/ajan erişimini ücretlendirme araçları** (ör. "pay per crawl" ve
     x402 desteği). Ürün adları, koşullar ve ülke kısıtları hızla değişiyor: karar anında
     Cloudflare'in güncel belgelerinden doğrulanacak.
   Her ikisi de A seçeneğini (Cloudflare Pages + alan adı) varsayar; site zaten statik olduğu için
   ödeme kapısı yalnız `data/site/` uçlarının önüne konur, sayfalar ücretsiz kalır.
3. **Satılmayacaklar:** sinyal, "al/sat", hedef fiyat, portföy önerisi, kişiye özel yönlendirme,
   kopya işlem. Bunlar hem ilkemize hem büyük olasılıkla izin gerektiren faaliyetlere girer.

## Önkoşullar (hepsi tamamlanmadan ücret alınmaz)

| # | Önkoşul | Neden | Durum |
|---|---|---|---|
| 1 | **Özel motor**: sweeplab özel, vitrin ayrı (DEPLOY_PLAN A veya C) | Ham veri ve puanlama kodu bugün herkese açık | ⏸ Boran |
| 2 | **Lisanslı/kamu veri kaynakları**: Yahoo Finance (kişisel kullanım şartlı), OKX, ICE (DXY, HY OAS), Cboe (VIX), Nasdaq girdileri ya lisanslanır ya kamu kaynaklarla değiştirilir (ör. TCMB EVDS döviz/altın, Borsa İstanbul veri lisansı, FRED'in kamu serileri) | Lisanssız veriden türetilen çıktı satılamaz; bugün bu alanlar "yalnızca görüntüleme" etiketli | ⬜ |
| 3 | **Alan adı + Cloudflare** | Ödeme kapısı, hız sınırı, bot yönetimi tek yerde | ⏸ Boran |
| 4 | **Hukuki kontrol (Türkiye)**: SPK (yatırım danışmanlığı / yatırım tavsiyesi sınırları, sermaye piyasası verisi yayımlama), MASAK (ödeme ve kimlik yükümlülükleri, özellikle kripto ödeme alınırsa), kripto varlık hizmet sağlayıcılarına ilişkin düzenlemeler, KVKK, vergi (şahıs şirketi / şirket, yurt dışından gelir, KDV) | Ücretli veri, "tavsiye" algısı ve kripto ödeme ayrı ayrı yükümlülük doğurabilir | ⬜ avukat + mali müşavir |
| 5 | **Kullanım şartları + gizlilik metni** | Ücretli API sözleşmesi, sorumluluk reddi | ⬜ |
| 6 | **Sicil**: en az 6–12 ay canlı, dürüst (yanlış alarmlar dahil) kayıt | Satılan şeyin değeri buradan gelir | ⏳ 21 Kasım 2026'da başladı |

## Riskler

- **Kopyalanma:** türetilmiş günlük dosyalar ücretsiz kaldıkça biri yeniden yayımlayabilir. Savunma:
  tazelik, zaman damgalı sicil, marka, Türkçe bağlam; ücretli katmanda gün içi ve uzun geçmiş.
- **Veri lisansı:** önkoşul 2 karşılanmadan ücret almak en büyük hukuki risk.
- **"Tavsiye" algısı:** ücretli bir üründe sözcük seçimi daha da sıkı denetlenir; yasak kelime
  testleri her uçta çalışır.
- **Kripto ile ödeme:** MASAK ve kripto düzenlemeleri açısından ayrı inceleme gerektirir; gerekirse
  yalnız itibari para ile ödeme.
- **Bakım yükü:** tek geliştirici; SLA vaadi gerçekçi tutulmalı.

## Yeniden bakma tetikleyicileri (biri gerçekleşince bu belge açılır)

- Ayda **10.000+ tekil ziyaretçi** ya da Search Console'da ayda **50.000+ gösterim** (S11 ölçümü).
- `data/site/` uçlarına **düzenli otomatik erişim** (Cloudflare trafik kayıtlarında bot/ajan payı belirgin).
- En az bir kurumsal/uygulama kullanıcısının **ücretli erişim talebi**.
- Canlı sicilin **6 ayı** dolması.

İlk adım o zaman: önkoşul 4 için avukat görüşmesi ve önkoşul 2 için veri kaynağı envanteri
(`docs/` altında ayrı belge). Kod en son gelir.
