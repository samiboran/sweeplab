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
  if (!host || !C || !saved || !C.ASSETS[saved.a]) return;

  function render(d) {
    var P = d && d.prices;
    if (!P) return;
    var p = {};
    Object.keys(P).forEach(function (k) { p[k] = P[k]; });
    p.custom_tl = val(saved.cp);
    var a = saved.a, cost = val(saved.m), qty = val(saved.q), sp = val(saved.s);
    var invested = qty;
    if (a === "bist100" && cost > 0) qty = qty / cost;
    var r = C.compute(a, cost, saved.c === "USD" ? "USD" : "TL", qty, p, sp > 0 ? sp : 0);
    if (!r) return;
    var ga = (d.assets || []).filter(function (x) { return x && x.id === "gram_altin"; })[0];
    var name = a === "diger" && saved.on ? String(saved.on).slice(0, 30) : null;

    host.textContent = "";
    host.setAttribute("data-noi18n", "");
    host.appendChild(el("p", "label", L("Senin pozisyonun · yalnız bu cihazda", "Your position · on this device only")));
    var big = el("p", "poz-big" + (r.plPct < 0 ? " neg" : ""), pct(r.plPct));
    host.appendChild(big);
    var amt = a === "bist100" ? num(invested, 0) : num(r.amount, Number.isInteger(r.amount) ? 0 : 2);
    var what = name ? amt + " × " + name : amt + " " + UNIT[a];
    var line = what + L(" · bugünkü değer ", " · value today ") + money(r.value, r.ccy);
    if (a !== "bist100") {
      line += L(" · maliyetine dönmek için ", " · breakeven for ") + ONE[a] + " " + money(r.breakeven, r.ccy);
      if (r.spreadPct) line += L(" (makas dahil ", " (incl. spread ") + money(r.netBreakeven, r.ccy) + ")";
    } else {
      line += L(" · maliyetine dönmek için BIST 100 ", " · breakeven BIST 100 ") + num(r.breakeven, 0) + L(" puan", " points");
    }
    host.appendChild(el("p", "poz-line", line));
    var when = a === "diger" ? L("Bugünkü fiyatı sen girdin; değiştiyse hesaplayıcıda güncelle.", "You entered today's price; update it in the calculator if it changed.")
      : L("Fiyatlar ", "Prices: data of ") + day((ga && ga.asof) || P.usdtry_asof) + L(" verisi. Yatırım tavsiyesi değildir.", ". Not investment advice.");
    host.appendChild(el("p", "mute small", when));
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
