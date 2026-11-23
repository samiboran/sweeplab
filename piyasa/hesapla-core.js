/* Piyasa Hava Durumu — position calculator math. Pure functions, no network, no DOM.
   Works in the browser (window.PHDCalc) and in node (module.exports) for tests. */
(function (root) {
  "use strict";
  var OZ = 31.1035;
  // unit: what one "amount" means; metal: true when TL price comes from USD/oz × USDTRY
  var ASSETS = {
    gram_altin: { label: "Gram altın", unit: "gram", metal: true },
    gram_gumus: { label: "Gram gümüş", unit: "gram", metal: true },
    btc: { label: "Bitcoin (BTC)", unit: "BTC" },
    eth: { label: "Ether (ETH)", unit: "ETH" },
    dolar: { label: "Dolar", unit: "dolar", tlOnly: true },
    bist100: { label: "BIST 100", unit: "puan", tlOnly: true },
    // çeyrek / cumhuriyet altını, bilezik, euro…: no reliable free price, so the user types today's price
    diger: { label: "Diğer (fiyatı sen gir)", unit: "adet", tlOnly: true, custom: true }
  };

  /* Current price of one unit in TL and USD from tl.json "prices". */
  function prices(asset, p) {
    var u = +p.usdtry;
    if (!(u > 0)) return null;
    var tl = null, usd = null;
    if (asset === "gram_altin" && p.gram_altin_tl) tl = +p.gram_altin_tl;
    else if (asset === "gram_gumus" && p.gram_gumus_tl) tl = +p.gram_gumus_tl;
    else if (asset === "dolar") tl = u;
    else if (asset === "bist100" && p.bist100_tl) tl = +p.bist100_tl;
    else if (asset === "diger") { if (+p.custom_tl > 0) tl = +p.custom_tl; else return null; }
    else if ((asset === "btc" || asset === "eth") && p[asset + "_usd"]) usd = +p[asset + "_usd"];
    if (tl == null && usd == null) return null;
    if (tl == null) tl = usd * u;
    if (usd == null) usd = tl / u;
    return { tl: tl, usd: usd, usdtry: u };
  }

  /* Breakeven ounce price in USD for a TL cost per gram at a given USD/TRY. */
  function breakevenOunceUsd(costTlPerGram, usdtry) { return costTlPerGram * OZ / usdtry; }

  /* Spread % from the two prices a dealer quotes: sell (what you pay) and buy (what you get). */
  function spreadFromPrices(sell, buy) {
    sell = +sell; buy = +buy;
    if (!(sell > 0) || !(buy > 0) || buy > sell) return null;
    return (sell - buy) / sell * 100;
  }

  /* cost: average cost per unit in `ccy` ("TL" | "USD"); amount: units held.
     spreadPct (optional, 0–50): dealer spread / commission taken when selling; the market price
     must be this much higher for the cash you receive to cover your cost. */
  function compute(asset, cost, ccy, amount, p, spreadPct) {
    var a = ASSETS[asset];
    var px = prices(asset, p || {});
    cost = +cost; amount = +amount;
    if (!a || !px || !(cost > 0) || !(amount > 0)) return null;
    if (a.tlOnly) ccy = "TL";
    var cur = ccy === "USD" ? px.usd : px.tl;
    var r = {
      asset: asset, label: a.label, unit: a.unit, ccy: ccy, cost: cost, amount: amount,
      price: cur, priceTl: px.tl, priceUsd: px.usd, usdtry: px.usdtry,
      costTotal: cost * amount, value: cur * amount,
      plPct: (cur / cost - 1) * 100,
      toBreakevenPct: (cost / cur - 1) * 100,
      breakeven: cost,
      scenarios: []
    };
    r.pl = r.value - r.costTotal;
    var sp = +spreadPct;
    if (sp > 0 && sp < 50) {
      var k = 1 - sp / 100;
      r.spreadPct = sp;
      r.netValue = r.value * k;
      r.netPl = r.netValue - r.costTotal;
      r.netPlPct = (r.netValue / r.costTotal - 1) * 100;
      r.netBreakeven = cost / k;                       // market price at which the cash received = cost
      r.netToBreakevenPct = (r.netBreakeven / cur - 1) * 100;
    }
    [0, 10, 20].forEach(function (k) {
      var u = px.usdtry * (1 + k / 100);
      var s = { shockPct: k, usdtry: u };
      if (ccy === "TL") {
        // what the asset must cost in USD for the TL cost to be met at this rate
        s.breakevenUsd = a.metal ? breakevenOunceUsd(cost, u) : cost / u;
        s.breakevenUsdUnit = a.metal ? "ons" : a.unit;
        // TL value if the USD price stays as today
        s.valueTl = asset === "dolar" ? u * amount : (asset === "bist100" || asset === "diger" ? null : px.usd * u * amount);
        s.plPct = s.valueTl == null ? null : (s.valueTl / r.costTotal - 1) * 100;
      } else {
        s.breakevenTl = cost * u;
        s.valueTl = px.usd * u * amount;
      }
      r.scenarios.push(s);
    });
    return r;
  }

  /* Several purchases [[amount, unitCost], …] -> total amount and weighted average cost (rows with a bad number are skipped). */
  function averageLots(lots) {
    var q = 0, c = 0, n = 0;
    (lots || []).forEach(function (l) {
      var a = +l[0], k = +l[1];
      if (a > 0 && k > 0) { q += a; c += a * k; n++; }
    });
    return q > 0 ? { amount: q, cost: c / q, rows: n } : null;
  }

  /* Saved positions on this device. v1/v2 = one position object; v3 = { v: 3, list: [...], cur: i }.
     Always returns { list, cur } with at most 10 valid positions. */
  function normalizeStore(raw) {
    var list = [];
    if (raw && raw.v === 3 && Array.isArray(raw.list)) list = raw.list;
    else if (raw && typeof raw === "object" && raw.a) list = [raw];
    list = list.filter(function (x) { return x && typeof x === "object" && ASSETS[x.a]; }).slice(0, 10);
    var cur = raw && raw.v === 3 ? Math.floor(+raw.cur) : 0;
    if (!(cur >= 0 && cur < list.length)) cur = 0;
    return { list: list, cur: cur };
  }

  var api = { ASSETS: ASSETS, OZ: OZ, prices: prices, compute: compute, breakevenOunceUsd: breakevenOunceUsd,
              spreadFromPrices: spreadFromPrices, averageLots: averageLots, normalizeStore: normalizeStore };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.PHDCalc = api;
})(this);
