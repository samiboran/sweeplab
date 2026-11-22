/* Piyasa Hava Durumu — "Dünya" (S10b). Fetched JSON is data: textContent / DOM APIs
   only, never innerHTML. Order is the file's (region / asset class, alphabetical
   lists); the page never re-sorts by change. Headlines: title + source + time + link. */
(function () {
  "use strict";
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var MONTHS = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function trDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] + " " + m[1] : "—";
  }
  function short(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1].slice(0, 3) : "—";
  }
  function pct(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    var a = Math.abs(v).toLocaleString("tr-TR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
    if (a === "0,0") return "%0,0";
    return (v > 0 ? "+" : "−") + "⁠%" + a;
  }
  function num(v) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    var a = Math.abs(v), nd = a >= 1000 ? 0 : a >= 1 ? 2 : 4;
    return v.toLocaleString("tr-TR", { minimumFractionDigits: nd, maximumFractionDigits: nd });
  }
  function istTime(iso) {
    var d = new Date(String(iso || ""));
    if (isNaN(d.getTime())) return "";
    try {
      return d.toLocaleString("tr-TR", { timeZone: "Europe/Istanbul", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    } catch (e) { return d.toISOString().slice(0, 16).replace("T", " ") + " UTC"; }
  }
  function mark(v, w) {
    var td = el("td", "pm m" + w);
    if (v === 1 || v === 0) {
      td.appendChild(el("span", v === 1 ? "fm up" : "fm", null));
      td.appendChild(el("span", "sr", w + " günlük ortalamanın " + (v === 1 ? "üstünde" : "altında")));
    } else {
      td.appendChild(el("span", "mute", "—"));
      td.appendChild(el("span", "sr", "yeterli geçmiş yok"));
    }
    return td;
  }
  function chg(v, cls) { return el("td", "r " + cls + (typeof v === "number" && v < 0 ? " neg" : ""), pct(v)); }

  /* cols: level? → Varlık | Seviye | 1g | 7g | 30g | YB | 20g | 50g | 200g | Veri */
  function table(caption, rows, withLevel, nameOf) {
    var wrap = el("div", "tablewrap");
    var t = el("table", "konum dunya" + (withLevel ? "" : " nolevel"));
    t.appendChild(el("caption", "sr", caption));
    var hr = el("tr"), head = [["Varlık", "l"]];
    if (withLevel) head.push(["Seviye", "r lv"]);
    head = head.concat([["1g", "r c1"], ["7g", "r c7"], ["30g", "r c30"], ["YB", "r cy"], ["20g", "c m20"], ["50g", "c m50"], ["200g", "c m200"], ["Veri", "r d"]]);
    head.forEach(function (h) { var c = el("th", h[1], h[0]); c.scope = "col"; hr.appendChild(c); });
    var th = el("thead"); th.appendChild(hr); t.appendChild(th);
    var tb = el("tbody");
    rows.forEach(function (r) {
      var tr = el("tr", r.eski ? "stale" : null);
      var n = el("th", "l", nameOf(r)); n.scope = "row"; tr.appendChild(n);
      if (withLevel) tr.appendChild(el("td", "r lv", num(r.seviye)));
      tr.appendChild(chg(r.chg_1g, "c1 v"));
      tr.appendChild(chg(r.chg_7g, "c7"));
      tr.appendChild(chg(r.chg_30g, "c30"));
      tr.appendChild(chg(r.chg_ytd, "cy"));
      tr.appendChild(mark(r.ust20, 20));
      tr.appendChild(mark(r.ust50, 50));
      tr.appendChild(mark(r.ust200, 200));
      tr.appendChild(el("td", "r d", r.asof ? short(r.asof) + (r.eski ? " · eski" : "") : "veri yok"));
      tb.appendChild(tr);
    });
    t.appendChild(tb);
    wrap.appendChild(t);
    return wrap;
  }

  function section(id, title) {
    var s = el("section", "kg");
    var h = el("h2", "sh", title);
    h.id = "d-" + String(id).replace(/[^a-z0-9_-]/gi, "");
    s.setAttribute("aria-labelledby", h.id);
    s.appendChild(h);
    return s;
  }

  function headlines(b) {
    var box = $("d-heads");
    box.textContent = "";
    if (!b) { box.appendChild(el("p", "mute small", "Başlıklar henüz yok.")); return; }
    var any = false;
    (b.konular || []).forEach(function (t) {
      var items = t.basliklar || [];
      if (!items.length) return;
      any = true;
      box.appendChild(el("h3", "dh", t.konu));
      var ul = el("ul", "heads");
      items.forEach(function (it) {
        var li = el("li");
        var u = String(it.url || "");
        if (/^https:\/\//.test(u)) {
          var a = el("a", null, it.baslik);
          a.href = u;
          a.rel = "noopener noreferrer";
          li.appendChild(a);
        } else {
          li.appendChild(el("span", null, it.baslik));
        }
        li.appendChild(el("span", "hs", String(it.kaynak || "") + " · " + istTime(it.zaman)));
        ul.appendChild(li);
      });
      box.appendChild(ul);
    });
    if (!any) box.appendChild(el("p", "mute small", "Bugün listelenecek başlık yok."));
    if (b.not) box.appendChild(el("p", "mute small", b.not));
    var w = b.bekleyen || [];
    if (w.length) {
      var d = el("details", "detail");
      d.appendChild(el("summary", null, "Kaynaklar ve bekleyen konular"));
      (b.kaynaklar || []).forEach(function (k) {
        d.appendChild(el("p", "small", k.konu + " — " + k.kaynak + " (" + k.durum + ")"));
      });
      w.forEach(function (x) { d.appendChild(el("p", "small mute", x.konu + ": " + x.not)); });
      box.appendChild(d);
    }
  }

  function render(d) {
    if (d.status === "örnek") {
      var n = $("d-notice"); n.hidden = false;
      n.textContent = "Önizleme: bu sayfadaki sayılar örnek veridir, gerçek piyasa verisi değildir.";
    }
    $("d-meta").textContent = "Son kapanış: " + trDate(d.data_date) + " · Liste " + trDate(d.universe_set_date) +
      " tarihinde belirlendi, " + (d.universe_review || "üç ayda bir gözden geçirilir");
    var box = $("d-markets");
    box.textContent = "";
    (d.markets || []).forEach(function (m) {
      var s = section(m.id, m.baslik);
      s.appendChild(table(m.baslik + ": endeks ve fonlar", m.endeksler || [], true, function (r) { return r.ad; }));
      if ((m.sirketler || []).length) {
        var det = el("details", "detail comp");
        det.appendChild(el("summary", null, "En büyük şirketler (" + m.sirketler.length + ", alfabetik)"));
        det.appendChild(table(m.baslik + ": büyük şirketler", m.sirketler, false, function (r) { return r.ad; }));
        det.appendChild(el("p", "mute small", "Yerel para birimiyle değişim. Liste piyasa değeri büyüklüğüne göre bir kez belirlendi; sıralama değildir."));
        s.appendChild(det);
      }
      box.appendChild(s);
    });
    var cb = $("d-emtia");
    cb.textContent = "";
    (d.emtia || []).forEach(function (g) {
      cb.appendChild(el("h3", "dh", g.grup));
      cb.appendChild(table(g.grup, g.satirlar || [], true, function (r) { return r.ad + " (" + r.birim + ")"; }));
    });
    var rb = $("d-ref");
    rb.textContent = "";
    var dl = el("dl", "ref");
    (d.referans_metaller || []).forEach(function (r) {
      dl.appendChild(el("dt", null, r.ad));
      var dd = el("dd", null, r.aciklama + " ");
      dd.appendChild(el("span", "mute", "— " + r.durum + "."));
      dl.appendChild(dd);
    });
    rb.appendChild(dl);
    headlines(d.basliklar);
    $("d-note").textContent = d.note || "";
    $("foot-meta").textContent = "Veri tarihi " + trDate(d.data_date) + " · Üretildi " +
      String(d.generated_at || "—").replace("T", " ").replace("Z", " UTC");
  }

  fetch(DATA + "dunya.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(render)
    .catch(function () { $("d-meta").textContent = "Dünya verisi henüz yayımlanmadı ya da yüklenemedi."; });
})();
