/* Piyasa Hava Durumu — "Senin pozisyonun" card on the home page.
   Shown only when the visitor ticked "Bu cihazda hatırla" in the calculator. The saved numbers stay in this
   browser (localStorage); the only request is the public tl.json. DOM APIs only. */
(function () {
  "use strict";
  var C = window.PHDCalc;
  var RAW = "https://raw.githubusercontent.com/samiboran/sweeplab/data-feed/data/site/";
  var DATA = /\.github\.io$/.test(location.hostname) ? RAW : "data/site/";
  var KEY = "phd-hesapla-v1";
  var I = window.PHD_I18N, EN = !!(I && I.en);
  var MONTHS = EN ? ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                  : ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  var UNIT = EN ? { gram_altin: "g of gold", gram_gumus: "g of silver", dolar: "dollars", btc: "BTC", eth: "ETH", bist100: "TL in BIST 100", diger: "units" }
                : { gram_altin: "gram altın", gram_gumus: "gram gümüş", dolar: "dolar", btc: "BTC", eth: "ETH", bist100: "TL BIST 100", diger: "adet" };
  var ONE = EN ? { gram_altin: "1 gram", gram_gumus: "1 gram", dolar: "1 dollar", btc: "1 BTC", eth: "1 ETH", diger: "1 unit" }
               : { gram_altin: "1 gram", gram_gumus: "1 gram", dolar: "1 dolar", btc: "1 BTC", eth: "1 ETH", diger: "1 adet" };
  function L(tr, en) { return EN ? en : tr; }
  function $(id) { return document.getElementById(id); }
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = String(text);
    return e;
  }
  function num(v, nd) {
    if (typeof v !== "number" || !isFinite(v)) return "—";
    return v.toLocaleString(EN ? "en-US" : "tr-TR", { minimumFractionDigits: nd, maximumFractionDigits: nd });
  }
  function pct(v) { var sg = v > 0 ? "+" : v < 0 ? "−" : ""; return EN ? sg + num(Math.abs(v), 2) + "%" : sg + "%" + num(Math.abs(v), 2); }
  function parse(s) {                       // same rules as the calculator
    s = String(s || "").trim().replace(/\s/g, "");
    if (EN && /\./.test(s)) s = s.replace(/,/g, "");
    else if (/,/.test(s)) s = s.replace(/\./g, "").replace(",", ".");
    else if (!EN && /^\d{1,3}(\.\d{3})+$/.test(s)) s = s.replace(/\./g, "");
    else if (EN) s = s.replace(/,/g, "");
    var v = parseFloat(s);
    return isFinite(v) ? v : NaN;
  }
  function val(v) { return typeof v === "number" ? v : parse(v); }   // v2 numbers, v1 raw text
  function day(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    return m ? (+m[3]) + " " + MONTHS[+m[2] - 1] : "";
  }
  function money(v, c) { return num(v, Math.abs(v) < 10 ? 4 : 2) + (c === "USD" ? " $" : " TL"); }

  var saved = null;
  try { saved = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { saved = null; }
  var host = $("pozisyon");
  var LIST = C && C.normalizeStore ? C.normalizeStore(saved).list : (saved && C && C.ASSETS[saved.a] ? [saved] : []);
  if (!host || !C || !LIST.length) return;

  function calc(sv, P) {
    var p = {};
    Object.keys(P).forEach(function (k) { p[k] = P[k]; });
    p.custom_tl = val(sv.cp);
    var a = sv.a, cost = val(sv.m), qty = val(sv.q), sp = val(sv.s);
    var invested = qty;
    if (a === "bist100" && cost > 0) qty = qty / cost;
    var r = C.compute(a, cost, sv.c === "USD" ? "USD" : "TL", qty, p, sp > 0 ? sp : 0);
    if (!r) return null;
    var name = a === "diger" && sv.on ? String(sv.on).slice(0, 30) : null;
    var amt = a === "bist100" ? num(invested, 0) : num(r.amount, Number.isInteger(r.amount) ? 0 : 2);
    var what = name ? amt + " × " + name : amt + " " + UNIT[a];
    var line = what + L(" · bugünkü değer ", " · value today ") + money(r.value, r.ccy);
    if (a !== "bist100") {
      line += L(" · maliyetine dönmek için ", " · breakeven for ") + ONE[a] + " " + money(r.breakeven, r.ccy);
      if (r.spreadPct) line += L(" (makas dahil ", " (incl. spread ") + money(r.netBreakeven, r.ccy) + ")";
    } else {
      line += L(" · maliyetine dönmek için BIST 100 ", " · breakeven BIST 100 ") + num(r.breakeven, 0) + L(" puan", " points");
    }
    var entered = /^\d{4}-\d{2}-\d{2}$/.test(String(sv.t || "")) ? day(sv.t) : "";
    return { r: r, a: a, what: what, name: name || what, line: line, entered: entered };
  }

  function render(d) {
    var P = d && d.prices;
    if (!P) return;
    var rows = LIST.map(function (sv) { return calc(sv, P); }).filter(Boolean);
    if (!rows.length) return;
    var ga = (d.assets || []).filter(function (x) { return x && x.id === "gram_altin"; })[0];
    var u = +P.usdtry;

    host.textContent = "";
    host.setAttribute("data-noi18n", "");
    if (rows.length === 1) {
      var x = rows[0];
      host.appendChild(el("p", "label", L("Senin pozisyonun · yalnız bu cihazda", "Your position · on this device only")));
      host.appendChild(el("p", "poz-big" + (x.r.plPct < 0 ? " neg" : ""), pct(x.r.plPct)));
      host.appendChild(el("p", "poz-line", x.line));
    } else {
      host.appendChild(el("p", "label", L("Senin pozisyonların · yalnız bu cihazda", "Your positions · on this device only")));
      // totals in TL; a total P/L only when every cost was entered in TL (no guessing past exchange rates)
      var valTl = 0, costTl = 0, allTl = true;
      rows.forEach(function (x) {
        valTl += x.r.ccy === "USD" ? x.r.value * u : x.r.value;
        if (x.r.ccy === "TL") costTl += x.r.costTotal; else allTl = false;
      });
      if (allTl && costTl > 0) {
        var tp = (valTl / costTl - 1) * 100;
        host.appendChild(el("p", "poz-big" + (tp < 0 ? " neg" : ""), pct(tp)));
        host.appendChild(el("p", "poz-line", L("Toplam bugünkü değer ", "Total value today ") + money(valTl, "TL") + L(" · toplam maliyet ", " · total cost ") + money(costTl, "TL")));
      } else {
        host.appendChild(el("p", "poz-big", money(valTl, "TL")));
        host.appendChild(el("p", "poz-line", L("Toplam bugünkü değer (dolar maliyetli pozisyonlar bugünkü kurla TL'ye çevrildi; toplam kâr/zarar gösterilmez).",
          "Total value today (dollar-cost positions converted at today's rate; no combined profit/loss shown).")));
      }
      var ul = el("ul", "poz-rows");
      rows.forEach(function (x) {
        var li = el("li");
        li.appendChild(el("span", "poz-pl" + (x.r.plPct < 0 ? " neg" : ""), pct(x.r.plPct)));
        li.appendChild(el("span", null, x.line));
        ul.appendChild(li);
      });
      host.appendChild(ul);
    }
    var custom = rows.filter(function (x) { return x.a === "diger"; });
    var note = L("Fiyatlar ", "Prices: data of ") + day((ga && ga.asof) || P.usdtry_asof) + L(" verisi.", ".");
    custom.forEach(function (x) {
      note += " " + (x.entered ? L(x.name + " fiyatını " + x.entered + " tarihinde sen girdin.", "You entered the price of " + x.name + " on " + x.entered + ".")
        : L(x.name + " fiyatını sen girdin.", "You entered the price of " + x.name + "."));
    });
    host.appendChild(el("p", "mute small", note + L(" Yatırım tavsiyesi değildir.", " Not investment advice.")));
    var act = el("p", "poz-act");
    var edit = el("a", null, L("Düzenle", "Edit"));
    edit.href = "hesapla.html" + (EN ? "?lang=en" : "");
    act.appendChild(edit);
    act.appendChild(document.createTextNode(" · "));
    var del = el("button", "poz-del", L("Bu cihazdan sil", "Remove from this device"));
    del.type = "button";
    del.addEventListener("click", function () {
      try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ }
      host.textContent = "";
      host.hidden = true;
      var tl = document.querySelector(".tl-link.top");
      if (tl) tl.hidden = false;
    });
    act.appendChild(del);
    host.appendChild(act);
    host.hidden = false;
    var tlLink = document.querySelector(".tl-link.top");     // the card already links to the calculator
    if (tlLink) tlLink.hidden = true;
  }

  fetch(DATA + "tl.json", { cache: "no-cache", credentials: "omit", referrerPolicy: "no-referrer" })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(render)
    .catch(function () { /* no card without prices */ });
})();
