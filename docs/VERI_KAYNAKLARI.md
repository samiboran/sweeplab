# Veri kaynakları — ücretsiz ve yeniden yayına izinli seçenekler (araştırma: 23 Kasım 2026)

**Karar (Boran, 23 Kasım):** ücretsiz *ve* doğru (güncel) bir kaynağı olan veri oraya geçer; olmayanlar şimdiki
kaynaktan (Yahoo Finance) devam eder. Gelir modeline geçerken ya da bir kaynak sahibinden uyarı gelirse yeniden ele alınır.
Hukuki görüş değildir.

| Veri | Şimdi | Ücretsiz + izinli aday | Neden henüz geçilmedi |
|---|---|---|---|
| Dolar/TL | Yahoo TRY=X (gün içi) | TCMB gösterge kurları (`kurlar/today.xml`, arşiv `kurlar/YYYYMM/GGAAYYYY.xml`; EVDS anahtarlı). Şart: "kaynak gösterilmek suretiyle yayımlanabilir", ticari kullanım TCMB'nin yazılı iznine tabi. | Günde bir kez (~15:30). Gram altın = ons × dolar/TL olduğu için gün içi gram altın bayat kurla hesaplanırdı → doğruluk düşer. **Kullanılan yer:** hesaplayıcıdaki makas referansı (efektif alış/satış). |
| Brent / WTI | Yahoo BZ=F / CL=F | EIA spot (RBRTE, RWTC) — kamu malı; FRED `fredgraph.csv?id=DCOILBRENTEU` / `DCOILWTICO` anahtarsız. | EIA spot haftalık toplu güncellenir (birkaç gün–1 hafta gecikme) → bantta "1 günlük değişim" yanlış olur. |
| Ons altın | Yahoo GC=F | TCMB EVDS `TP.ALTINPIYASA.AGORT03` (Borsa İstanbul kıymetli madenler piyasası USD/ons ağırlıklı ortalama; doğrulanmadı, EVDS anahtarı gerekir). LBMA lisanslı; FRED'deki LBMA serileri 2022'de kaldırıldı; ücretsiz API'ler (freegoldapi, goldprice.dev, metalcharts) ya Yahoo'dan türetilmiş ya 30 gün geçmişle sınırlı ya da yeniden yayını yasaklıyor. | ⏸ EVDS anahtarı (Boran) + seri doğrulaması; ağırlıklı ortalama kapanış değildir. |
| Ons gümüş | Yahoo SI=F | Doğrulanmış serbest kaynak bulunamadı. | — |
| BIST 100 ve hisseler | Yahoo XU100.IS / .IS | Borsa İstanbul verisi yalnız lisanslı dağıtıcılar üzerinden; gün sonu dahil serbest yeniden yayın maddesi bulunamadı. | Yazılı izin: vyk-marketing@borsaistanbul.com |
| Kripto | OKX herkese açık API (+ Yahoo BTC-USD/ETH-USD uzun geçmiş için) | Borsa API'leri | — |

Kaynaklar: TCMB kullanım koşulları (tcmb.gov.tr → Diğer), EVDS kullanım koşulları (evds3.tcmb.gov.tr belge 18),
EIA telif/yeniden kullanım (eia.gov/about/copyrights_reuse.php), LBMA fiyat lisansı (lbma.org.uk/prices-and-data),
FRED duyurusu 2022-01 (IBA verisinin kaldırılması), Borsa İstanbul veri yayımı (borsaistanbul.com/en/data/data-dissemination).
