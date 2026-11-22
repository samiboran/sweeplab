# Yayın planı — "özel motor, herkese açık vitrin"

Bu belge Boran içindir. Hiçbir hesap, token veya repo otomatik olarak
açılmaz; aşağıdaki ⏸ adımlarını sen yaparsın. Repo lisansı ve görünürlüğü
değiştirilmedi.

## Bugünkü durum ve neden değişmeli

- `samiboran/sweeplab` **herkese açık**. GitHub Pages `main` dalının kökünden
  yayın yapıyor → kök `index.html` (SweepLab terminali) ve birleşince
  `piyasa/` herkese açık.
- `data-feed` dalı da herkese açık ve **ham girdileri** içeriyor:
  `data/derivs/` (OKX/Hyperliquid türev verisi, FRED serileri, CFTC, notebook
  satırları, likidasyon haritaları), `data/research/candles_1d/` ve
  `data/research/us_1d/` (Yahoo/OKX günlük mumları), `data/market/`.
  - **Kopyalama riski:** motorun girdileri ve kodu (`tools/`) açık olduğu için
    herkes aynı sonucu kendi üretebilir; asıl değerimiz (motor + ham veri +
    tazelik + zaman damgalı sicil) korunmuyor.
  - **Lisans riski:** Yahoo verisi kişisel kullanım şartlıdır; ICE BofA HY OAS
    (FRED) ve S&P/Nasdaq endeks seviyelerinin yeniden dağıtımı kısıtlıdır.
    Ham mumların açık bir dalda toplu olarak durması bu şartlarla çelişebilir.
- Hedef: repo **özel** olur; dışarıya yalnızca **statik site (`piyasa/`) +
  türetilmiş veri (`data/site/`)** çıkar. Workflow'daki deploy işleri tam
  olarak bu iki klasörü kopyalar, başka hiçbir şeyi değil.

## Seçenekler

| | A — Cloudflare Pages (ÖNERİLEN) | B — GitHub Pro | C — ayrı public repo |
|---|---|---|---|
| Maliyet | 0 ₺ | ~4 $/ay | 0 ₺ |
| sweeplab özel olabilir mi | Evet | Evet (Pages özel repoda çalışır) | Evet |
| data-feed gizli kalır mı | Evet | Evet (ama Pages'e giden her şey açık; ayrım dikkat ister) | Evet |
| Alan adı | Ücretsiz, kolay | Var | Var |
| Koruma (DDoS, bot, önbellek) | Cloudflare dahili | Yok | Yok |
| Çerezsiz analitik | Cloudflare Web Analytics | Yok | Yok |
| İleride ücretli erişim (S12) | Aynı yerde (Workers / Monetization Gateway) | Yok | Yok |

**Öneri: A.** Ücretsiz, özel repoyla çalışır, alan adı + koruma + ileride
gelir kapısı tek yerde. C, Cloudflare hesabı açmak istemezsen sıfır maliyetli
ara çözümdür. B en az iş ama aylık ücretli ve Pages'te neyin yayımlandığını
ayırmak zorlaşır.

## A — Cloudflare Pages (önerilen), adım adım ⏸ Boran

1. https://dash.cloudflare.com/sign-up → ücretsiz hesap aç, e-postayı doğrula.
2. Sol menü **Workers & Pages** → **Create** → **Pages** sekmesi → **Upload
   assets** (Direct Upload; Git bağlantısı GEREKMEZ — repoya Cloudflare'in
   erişmesini istemiyoruz). Proje adı: `piyasa-hava-durumu`. İlk yüklemede
   boş bir klasör/tek bir `index.html` yeterli; sonra workflow günceller.
3. **Account ID:** Workers & Pages sayfasının sağ panelinde "Account ID" →
   kopyala.
4. **API token:** sağ üst profil → **My Profile** → **API Tokens** → **Create
   Token** → **Custom token** → İzin: *Account* → *Cloudflare Pages* → *Edit*;
   Account Resources: yalnız kendi hesabın; TTL istersen 1 yıl → **Continue**
   → **Create** → token'ı kopyala (bir kez gösterilir).
5. GitHub → `samiboran/sweeplab` → **Settings** → **Secrets and variables** →
   **Actions** → **New repository secret**:
   - `CLOUDFLARE_API_TOKEN` = 4. adımdaki token
   - `CLOUDFLARE_ACCOUNT_ID` = 3. adımdaki ID
   - (isteğe bağlı) **Variables** sekmesinde `CLOUDFLARE_PAGES_PROJECT` =
     `piyasa-hava-durumu` (yoksa bu ad varsayılır)
6. **Actions** → **daily-brief** → **Run workflow**. `deploy-cloudflare` işi
   artık atlanmaz; `https://piyasa-hava-durumu.pages.dev` açılmalı.
7. Alan adı (isteğe bağlı, sonra): Pages projesi → **Custom domains** → **Set
   up a custom domain**.
8. Her şey çalışınca repoyu özel yap (aşağıdaki "Repoyu özel yapma").

## B — GitHub Pro ⏸ Boran

1. https://github.com/settings/billing → **Upgrade to Pro**.
2. Repoyu özel yap (aşağıda). Pages ayarları korunur.
3. Dikkat: Pages `main` kökünü yayımlar → kök terminal + `piyasa/` açık kalır
   (istenen), ama `main` içine ham veri konmamalı. `data/site/` ise main'de
   yok; sayfanın veriyi okuyabilmesi için Pages'i bir Actions workflow'una
   (`actions/deploy-pages`) çevirmek gerekir — bu A'dan daha fazla iş.

## C — ayrı public repo ⏸ Boran

1. https://github.com/new → ad `piyasa` (sahibi `samiboran`), **Public**,
   README ile başlat.
2. Yeni repo → **Settings** → **Pages** → Source: *Deploy from a branch* →
   `main` / `(root)` → **Save**. Adres: `https://samiboran.github.io/piyasa/`.
3. Token: https://github.com/settings/personal-access-tokens/new
   (fine-grained) → Repository access: **Only select repositories** →
   `samiboran/piyasa` → Permissions → **Contents: Read and write** → süre
   1 yıl → **Generate** → kopyala.
4. `samiboran/sweeplab` → Settings → Secrets and variables → Actions:
   - `SITE_DEPLOY_TOKEN` = token
   - `SITE_DEPLOY_REPO` = `samiboran/piyasa`
5. daily-brief'i elle çalıştır; `deploy-repo` işi `piyasa` reposunun köküne
   `piyasa/` içeriğini ve `data/site/` klasörünü yazar (tek commit, eski
   dosyalar silinmez — arşiv yalnız büyür).

## Repoyu özel yapma ⏸ Boran (A veya C çalıştıktan sonra)

`samiboran/sweeplab` → **Settings** → en alt **Danger Zone** → **Change
repository visibility** → **Make private**.

Ne bozulur, nasıl korunur:

- **SweepLab terminali (kök `index.html`, GitHub Pages):** ücretsiz planda
  özel repoda Pages kapanır → `samiboran.github.io/sweeplab/` çalışmaz.
  Koruma: terminal tek dosya ve verisini kullanıcı yükler, sır içermez.
  (A) aynı deploy işine `index.html`'i `/terminal/` altına kopyalatabilir ya
  da ayrı bir Pages projesi; (C) `samiboran/piyasa` içine `terminal/` olarak
  kopyalanabilir. İstersen bunu S-sonrası küçük bir iş olarak eklerim; şu an
  deploy işi **yalnız** `piyasa/` + `data/site/` kopyalar.
- **raw.githubusercontent.com:** özel repoda anonim erişim biter. Önizleme
  sayfası veriyi oradan çeker; son barındırıcıda sayfa göreli
  `data/site/` yolunu kullanır (deploy işi kopyalar), bu yüzden etkilenmez.
- **Actions:** çalışmaya devam eder. Ücretsiz planda özel repolar için ayda
  2.000 dakika var; daily-brief günde birkaç dakika, diğer iki workflow elle
  tetikleniyor → sınırın çok altında.
- **Telegram bot / daily-brief / panel / bot:** etkilenmez (sırlar aynı).
- **Altınkulak** ayrı repo, etkilenmez.

## Neden veri raw.githubusercontent.com'dan (önizleme dönemi)

- Her sabah `main`'e commit atmadan taze veri: data-feed zaten her gün
  güncelleniyor; sayfa JSON'u doğrudan oradan okur.
- 2026-11-21 kontrolü: `access-control-allow-origin: *`, `max-age=300` →
  tarayıcıdan okunabilir, en çok 5 dk önbellek gecikmesi.
- Geçici: repo özel olunca biter; bu yüzden uç yolları (`data/site/…`) son
  barındırıcıda aynı kalacak şekilde tasarlandı.

## Workflow deploy işleri (eklenen)

`.github/workflows/daily-brief.yml` içinde:

- `site-deploy-check` — yalnız sırların **var olup olmadığını** çıktı olarak
  verir (değerleri asla yazdırmaz).
- `deploy-repo` (C) — `SITE_DEPLOY_TOKEN` ve `SITE_DEPLOY_REPO` yoksa
  **atlanır**.
- `deploy-cloudflare` (A) — `CLOUDFLARE_API_TOKEN` ve
  `CLOUDFLARE_ACCOUNT_ID` yoksa **atlanır**.
- İkisi de yalnız `contents: read` yetkisiyle çalışır ve yalnız `piyasa/` +
  `data/site/` kopyalar. Ham veri (`data/derivs`, `data/research`) ve kod
  (`tools/`) hedefe gitmez.

## Ölçüm — izleyicisiz (S11) ⏸ Boran

Sitede üçüncü taraf analitik betiği ve çerez **yoktur**. Ziyaretçi ve arama verisini görmenin iki
yolu var; ikisi de sitenin koduna izleyici eklemez.

### 1) Google Search Console (önerilen, hemen yapılabilir)

Hangi aramalarla bulunduğunu, kaç kez gösterildiğini ve tıklandığını, dizine alınma sorunlarını
gösterir. Sitenin son adresi (alan adı ya da Cloudflare Pages adresi) belli olunca:

1. https://search.google.com/search-console → **Mülk ekle** → **URL öneki** → sitenin tam adresi
   (ör. `https://piyasahavadurumu.com/`). Alan adı Cloudflare'deyse **Alan** türü ve DNS TXT kaydı
   daha kalıcıdır (Cloudflare → DNS → Kayıt ekle → TXT → Google'ın verdiği değer); o zaman 2–3. adım gerekmez.
2. Doğrulama yöntemi olarak **HTML etiketi**ni seç. Verilen satırdaki `content="…"` değerini kopyala
   (yalnız tırnak içindeki kod).
3. `piyasa/config.js` → `verification: { google: "BURAYA_KOD", bing: "" }` → commit + PR. Deploy işi
   `tools/build_static.py` ile kodu ana sayfanın `<head>` kısmına statik `<meta name="google-site-verification">`
   olarak ekler (betikle eklenen etiketi Google görmez; bu yüzden statik). Deploy bitince Search Console'da **Doğrula**.
4. Search Console → **Site haritaları** → `sitemap.xml` ekle.
5. Bing için: https://www.bing.com/webmasters → **Search Console'dan içe aktar** (en kolayı) ya da
   HTML meta etiketi → kodu `verification.bing` alanına yaz (etiket adı `msvalidate.01`).

GitHub Pages önizlemesi (`samiboran.github.io/sweeplab/piyasa/`) kökte olmadığı için robots.txt ve
alan doğrulaması orada tam çalışmaz; son barındırıcıya geçince yapılmalı.

### 2) Cloudflare Web Analytics (yalnız A seçilirse, isteğe bağlı)

Çerez kullanmaz, kişisel veri tutmaz, sayfa görüntüleme ve hız ölçer. Cloudflare Pages projesinde:
**Workers & Pages → proje → Metrics → Web Analytics → Enable**. Cloudflare bu durumda sayfalara
kendi küçük betiğini (`static.cloudflareinsights.com/beacon.min.js`) ekler. Sitemizin CSP'si bu betiği
şu an **engeller**; açmaya karar verirsen tüm sayfalardaki CSP'ye `script-src`'ye
`https://static.cloudflareinsights.com`, `connect-src`'ye `https://cloudflareinsights.com` eklenmeli
(bu bir karar: "üçüncü taraf betik yok" ilkesinden bilinçli istisna olur). Daha temiz alternatif:
betik eklemeden **Cloudflare → Analytics & Logs → Traffic** (sunucu tarafı istek sayıları; DNS proxy
açıksa ücretsiz planda vardır) — sitede hiçbir değişiklik gerekmez.
