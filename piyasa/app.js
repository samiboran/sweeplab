/* Piyasa Hava Durumu — home page. Fetched JSON is treated as data:
   only textContent / DOM APIs, never innerHTML. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  // GitHub Pages preview reads data-feed directly; any other host serves data/site/ next to the page.
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  var WORD = { YESIL: "YEŞİL", SARI: "SARI", KIRMIZI: "KIRMIZI" };
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function trDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] + " " + m[1] : "—";
  }
  function safeLevel(x) { return WORD[x] ? x : null; }
  var I18N = window.PHD_I18N || { en: false };
  var EN = I18N.en;
  // English mode: use the build's *_en fields; mark those nodes so i18n.js leaves them alone.
  function enText(node, tr, en) {
    if (EN && typeof en === "string" && en) { node.textContent = en; node.setAttribute("data-noi18n", ""); }
    else node.textContent = tr == null ? "" : String(tr);
    return node;
  }

  // Plain-language explanations per rule (same thresholds as yontem.html; static text).
  var EXPLAIN = {
    L1: { ne: "Dolara sabitlenmiş kripto paraların (USDT, USDC…) toplam piyasa değeri.",
          neden: "Kripto piyasasına giren ya da çıkan nakdin kaba bir ölçüsüdür. Arz küçülüyorsa piyasadan nakit çekiliyor demektir.",
          nasil: "Son 7 günde toplam arz azaldıysa işaret verir.", kaynak: "DefiLlama", keys: ["stables"] },
    L2: { ne: "Fed bilançosundan Hazine'nin Fed'deki hesabı ve ters repo çıkarıldığında kalan tutar.",
          neden: "Piyasadaki dolar bolluğunun yaygın bir göstergesidir; azalması likiditenin daraldığına işaret eder.",
          nasil: "20 gün öncesine göre azaldıysa işaret verir. Haftalık yayımlanır.", kaynak: "FRED (Federal Reserve)", keys: ["netliq"] },
    L3: { ne: "ABD'nin 10 yıllık enflasyona endeksli tahvil faizi: enflasyondan arındırılmış borçlanma maliyeti.",
          neden: "Reel faiz yükselince parayı riskli varlıkta tutmanın maliyeti artar.",
          nasil: "20 günde en az 0,15 puan (15 baz puan) yükseldiyse işaret verir.", kaynak: "FRED", keys: ["real10y"] },
    D1: { ne: "Doların başlıca para birimlerine karşı değerini ölçen endeks.",
          neden: "Hızlı dolar güçlenmesi dünya genelinde finansmanı zorlaştırır.",
          nasil: "20 günde en az %1 yükseldiyse işaret verir. Endeks lisanslı olduğu için yalnız yön gösterilir.", kaynak: "Yahoo Finance (ICE DXY)", keys: ["dxy"] },
    K1: { ne: "ABD'de düşük kredi notlu şirket tahvillerinin devlet tahviline göre ödediği ek faiz.",
          neden: "Bu fark açılıyorsa piyasa şirketlerin borcunu daha riskli görüyor demektir.",
          nasil: "20 günde en az 0,25 puan açıldıysa işaret verir. Lisanslı seri: yalnız işaret ve yön.", kaynak: "FRED (ICE BofA)", keys: ["hy_oas"] },
    K2: { ne: "S&P 500 opsiyonlarından hesaplanan beklenen oynaklık; \"korku endeksi\" olarak da bilinir.",
          neden: "Yükselmesi piyasada belirsizliğin ve korumaya talebin arttığını gösterir.",
          nasil: "18 veya üzerindeyse işaret verir.", kaynak: "FRED (Cboe VIX)", keys: ["vix"] },
    K3: { ne: "ABD teknoloji ağırlıklı Nasdaq Bileşik endeksi.",
          neden: "Risk iştahının en hızlı tepki veren göstergelerinden biridir.",
          nasil: "20 günde en az %3 düştüyse işaret verir. Lisanslı endeks: yalnız işaret ve yön.", kaynak: "FRED", keys: ["ndx"] },
    N1: { ne: "Altın ile doların aynı anda nasıl hareket ettiği.",
          neden: "Normalde güvenli liman olan altın düşerken dolar yükseliyorsa, yatırımcılar her şeyi satıp nakde geçiyor olabilir.",
          nasil: "Altın 20 günde en az %3 düştüyse ve aynı dönemde dolar endeksi yükseldiyse işaret verir.", kaynak: "Yahoo Finance (altın vadeli, DXY)", keys: ["gold", "dxy"] },
    P1: { ne: "WTI ham petrol vadeli fiyatı.",
          neden: "Sert yükseliş enflasyon baskısına, kredi primi açılırken sert düşüş talep zayıflığına işaret edebilir. Bunlar olası yorumlardır: petrol arz artışı ya da jeopolitik primin sönmesiyle de düşebilir.",
          nasil: "20 günde en az %10 yükseldiyse ya da en az %15 düşüp kredi primi açılıyorsa işaret verir.", kaynak: "Yahoo Finance (WTI vadeli)", keys: ["wti", "hy_oas"] }
  };

  function explain(code, asof, compareDate) {
    var e = EXPLAIN[code];
    var box = el("div", "explain");
    if (!e) { box.appendChild(el("p", null, "Bu kural için açıklama yok.")); return box; }
    [["Nedir?", e.ne], ["Neden izleniyor?", e.neden], ["Nasıl hesaplanıyor?", e.nasil], ["Kaynak:", e.kaynak]].forEach(function (x) {
      var p = el("p");
      p.appendChild(el("strong", null, x[0] + " "));
      p.appendChild(document.createTextNode(x[1]));
      box.appendChild(p);
    });
    var dates = e.keys.map(function (k) { return asof[k]; }).filter(Boolean).map(trDate);
    var meta = "Verinin tarihi: " + (dates.length ? dates.join(", ") : "—") +
      (compareDate ? " · Karşılaştırma: " + trDate(compareDate) : "");
    box.appendChild(el("p", "mute small", meta));
    var a = el("a", "small", "Yöntem sayfasında oku");
    a.href = "yontem.html#" + encodeURIComponent(code.toLowerCase());
    var p = el("p"); p.appendChild(a); box.appendChild(p);
    return box;
  }

  function render(d, archived) {
    var lvl = safeLevel(d.level);
    var dot = document.querySelector("#headline .dot");
    dot.className = "dot " + (lvl ? "lv-" + lvl.toLowerCase() : "lv-none");
    $("headline-text").textContent = lvl
      ? trDate(d.publish_date) + " — Makro hava: " + WORD[lvl]
      : "Makro hava verisi yok";
    document.title = lvl ? "Makro hava: " + WORD[lvl] + " — Piyasa Hava Durumu" : document.title;

    // One line under the band so the level is visible on the first screen (the full block is further down).
    var ml = $("macro-line");
    if (ml && lvl && !archived) {
      ml.textContent = "";
      ml.setAttribute("data-noi18n", "");
      var LV_EN = { YESIL: "GREEN", SARI: "YELLOW", KIRMIZI: "RED" };
      ml.appendChild(el("span", "dot lv-" + lvl.toLowerCase()));
      var mm = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(d.data_date || ""));
      var MEN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      var dd = mm ? (+mm[3]) + " " + (EN ? MEN[+mm[2] - 1] : MONTHS[+mm[2] - 1].slice(0, 3)) : "";
      ml.appendChild(document.createTextNode((EN ? "Macro weather: " + LV_EN[lvl] : "Makro hava: " + WORD[lvl]) +
        (dd ? (EN ? " · US data of " + dd : " · " + dd + " ABD verisi") : "") + " · "));
      var ma = el("a", null, EN ? "what it means" : "ne anlatıyor?");
      ma.href = "#kicker";
      ml.appendChild(ma);
      ml.hidden = false;
    }

    var mode = d.mode === "live" ? "canlı" : d.mode === "retro" ? "geriye dönük" : "—";
    $("meta").textContent = "Veri: " + trDate(d.data_date) + " kapanışı · Kural sürümü " +
      (d.rules_version || "—") + " · Kayıt: " + mode;

    var n = $("notice");
    n.hidden = true;
    n.textContent = "";
    n.removeAttribute("data-noi18n");
    if (archived) {
      n.hidden = false;
      n.textContent = "Arşiv kaydı: " + trDate(d.publish_date) + ". O gün yayımlandığı gibi gösteriliyor; yeniden hesaplanmadı." +
        (d.duzeltme ? " Bu kayıtta belgelenmiş bir düzeltme var (Yöntem sayfası)." : "") +
        " TL tarafı bugünün verisini gösterir.";
    } else if (d.status !== "güncel") {
      n.hidden = false;
      n.textContent = "Güncellenmedi. Gösterilen son iyi veri: " + trDate(d.last_good_date) +
        ". Yeni veri gelene kadar seviye değişmez.";
    } else if (d.level_held && d.held_note) {
      n.hidden = false;
      enText(n, d.held_note, d.held_note_en);
    }

    var list = $("rules");
    list.textContent = "";
    var asof = d.inputs_asof || {};
    (d.rules || []).forEach(function (r, idx) {
      var code = String(r.code || "");
      var li = el("li", r.flag === 1 ? "on" : r.flag === 0 ? "off" : "na");
      li.appendChild(el("span", "mark"));
      var body = el("span", "body");
      var btn = enText(el("button", "rtitle"), r.title, r.title_en);
      btn.type = "button";
      btn.setAttribute("aria-expanded", "false");
      var pid = "acik-" + idx;
      btn.setAttribute("aria-controls", pid);
      body.appendChild(btn);
      body.appendChild(enText(el("span", "rgroup"), r.group, r.group_en));
      body.appendChild(enText(el("span", "rtext"), r.sentence, r.sentence_en));
      var panel = explain(code, asof, d.compare_date);
      panel.id = pid;
      panel.hidden = true;
      body.appendChild(panel);
      btn.addEventListener("click", function () {
        var open = btn.getAttribute("aria-expanded") === "true";
        btn.setAttribute("aria-expanded", open ? "false" : "true");
        panel.hidden = open;
      });
      li.appendChild(body);
      li.setAttribute("aria-label", (r.flag === 1 ? "İşaret var: " : r.flag === 0 ? "İşaret yok: " : "Veri yok: ") + r.title);
      list.appendChild(li);
    });

    var det = $("detail-body");
    det.textContent = "";
    var big = el("p", "big", (d.raw_score != null ? d.raw_score : "–") + "/" + (d.max_score || 9));
    det.appendChild(big);
    det.appendChild(el("p", "mute small", "Ham skor. 0–2 YEŞİL, 3–4 SARI, 5 ve üzeri KIRMIZI; seviye ikinci gün onayıyla değişir."));
    var tbl = el("table", "groups");
    var cap = el("caption", "label", "Başlıklara göre");
    tbl.appendChild(cap);
    Object.keys(d.groups || {}).forEach(function (g) {
      var tr = el("tr");
      tr.appendChild(el("th", null, g));
      tr.appendChild(el("td", null, d.groups[g].points + " / " + d.groups[g].max));
      tbl.appendChild(tr);
    });
    det.appendChild(tbl);
    det.appendChild(el("p", "mute small", "Karşılaştırma tarihi: " + trDate(d.compare_date) + " (20 gün önce)."));

    var qs = $("questions");
    qs.textContent = "";
    if (timer) clearTimeout(timer);
    $("answer").textContent = "";
    var ans = (EN && Array.isArray(d.answers_en) && d.answers_en.length) ? d.answers_en : (d.answers || []);
    if (EN && ans === d.answers_en) qs.setAttribute("data-noi18n", ""); else qs.removeAttribute("data-noi18n");
    answersEn = EN && ans === d.answers_en;
    // The rules list above already says which rules signal; keep only questions that add something.
    ans.filter(function (q) { return q && q.id !== "isaretler"; }).forEach(function (q) {
      var b = el("button", "q", q.q);
      b.type = "button";
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", function () { ask(q, b); });
      qs.appendChild(b);
    });

    $("foot-meta").textContent = "Veri tarihi " + trDate(d.data_date) + " · Kural sürümü " +
      (d.rules_version || "—") + " · Üretildi " + String(d.generated_at || "—").replace("T", " ").replace("Z", " UTC");
  }

  var timer = null, answersEn = false;
  function ask(q, btn) {
    Array.prototype.forEach.call(document.querySelectorAll(".q"), function (b) { b.setAttribute("aria-pressed", "false"); });
    btn.setAttribute("aria-pressed", "true");
    var box = $("answer");
    box.textContent = "";
    var aq = el("p", "aq", q.q);
    if (answersEn) aq.setAttribute("data-noi18n", "");
    box.appendChild(aq);
    var lines = (q.a || []).slice();
    if (timer) clearTimeout(timer);
    (function next() {
      if (!lines.length) {
        if (window.PHDCharts) window.PHDCharts.attach(q.id, box);
        if (q.link === "yontem.html") {
          var p = el("p", "line");
          var a = el("a", null, EN ? "Method page" : "Yöntem sayfası");
          a.href = "yontem.html";
          p.appendChild(a);
          box.appendChild(p);
        }
        return;
      }
      var ln = el("p", "line", lines.shift());
      if (answersEn) ln.setAttribute("data-noi18n", "");
      box.appendChild(ln);
      timer = setTimeout(next, reduce ? 0 : 260);
    })();
  }

  function fail() {
    $("headline-text").textContent = "Veri şu an yüklenemedi";
    var n = $("notice");
    n.hidden = false;
    n.textContent = "Günlük veri dosyasına ulaşılamadı. Biraz sonra yeniden deneyin.";
  }

  function getJson(path) {
    return fetch(DATA + path, { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }

  // "Tarih seç": show a past day's published record from archive/YYYY-MM-DD.json (never recomputed).
  var ISO = /^\d{4}-\d{2}-\d{2}$/;
  var today = null;
  var input = $("tarih"), back = $("bugun");
  function setUrl(day) {
    try { history.replaceState(null, "", day ? "?tarih=" + day : location.pathname); } catch (e) { /* ignore */ }
  }
  function showToday() {
    if (!today) return;
    render(today, false);
    input.value = "";
    back.hidden = true;
    setUrl(null);
  }
  function showDay(day) {
    if (!ISO.test(day) || !today) return;
    if (day >= today.data_date) { showToday(); return; }
    getJson("archive/" + day + ".json").then(function (d) {
      render(d, true);
      input.value = day;
      back.hidden = false;
      setUrl(day);
    }).catch(function () {
      var n = $("notice");
      n.hidden = false;
      n.textContent = trDate(day) + " için kayıt bulunamadı. Arşiv sayfasında kayıtlı günler listelenir.";
    });
  }
  input.addEventListener("change", function () { if (input.value) showDay(input.value); else showToday(); });
  back.addEventListener("click", showToday);

  getJson("today.json")
    .then(function (d) {
      today = d;
      if (ISO.test(String(d.data_date))) input.max = d.data_date;
      render(d, false);
      var q = /[?&]tarih=(\d{4}-\d{2}-\d{2})/.exec(location.search);
      if (q) showDay(q[1]);
    })
    .catch(fail);
})();
