// --- Mod B (FVG - Fair Value Gap) Stratejisi, 1H ---
// uret(ctx) HER mumda cagrilir. ctx icerigi:
//   bar : { time, open, high, low, close }
//   i   : mevcut mum indeksi
//   c   : tum mumlar (yalnizca i'ye kadar, gelecek yok -- causal)
//   p   : parametreler (sol paneldeki degerler)
//   h   : yardimcilar -> h.atr(periyot,i), h.ema(periyot,i)
//   s   : kalici durum (mumlar arasi tasinir)
//   pozisyon : acik pozisyon ya da null
// Donus: { yon:'long'|'short', stop:..., sebep:'...' } VEYA null

return {
  uret(ctx){
    const { bar, i, c, p, h, s, pozisyon } = ctx;

    if (pozisyon) return null;

    const emaPeriyot = p.emaPeriyot || 50;
    const atrPeriyot = p.atrPeriyot || 14;
    const maxGapATR = p.maxGapATR || 0.3;   // gap < 0.3 x ATR
    const retestWindow = p.retestWindow || 100; // kac bar icinde retest beklensin

    if (s.pendingGaps === undefined) {
      s.pendingGaps = []; // { top, bot, dir, createdAt }
    }

    // --- Yeterli gecmis yoksa cik ---
    if (i < 3) return null;

    const atrVal = h.atr(atrPeriyot, i);
    const emaVal = h.ema(emaPeriyot, i);
    if (atrVal == null || emaVal == null || atrVal === 0) return null;

    // --- YENI FVG (3 mumluk bosluk) var mi? mum i-2, i-1, i uclusune bak ---
    const b0 = c[i - 2], b2 = bar; // b2 = su anki (i) bar
    const bias = bar.close > emaVal ? 1 : (bar.close < emaVal ? -1 : 0);

    if (bias === 1 && b0.high < b2.low) {
      // bullish gap
      const gap = b2.low - b0.high;
      if (gap > 0 && gap < atrVal * maxGapATR) {
        s.pendingGaps.push({ top: b2.low, bot: b0.high, dir: 1, createdAt: i });
      }
    }
    if (bias === -1 && b0.low > b2.high) {
      // bearish gap
      const gap = b0.low - b2.high;
      if (gap > 0 && gap < atrVal * maxGapATR) {
        s.pendingGaps.push({ top: b0.low, bot: b2.high, dir: -1, createdAt: i });
      }
    }

    // --- Bekleyen gap'lerden biri bu barda retest edildi mi? ---
    // Eskiyenleri (retestWindow asilanlari) temizle
    s.pendingGaps = s.pendingGaps.filter(g => i - g.createdAt <= retestWindow);

    for (let k = 0; k < s.pendingGaps.length; k++) {
      const g = s.pendingGaps[k];
      const zone = (g.top + g.bot) / 2;
      if (bar.low <= zone && zone <= bar.high) {
        s.pendingGaps.splice(k, 1); // bu gap kullanildi, listeden cikar
        const fvgYas = i - g.createdAt; // gap kac bar once olustu (log icin, filtre degil)
        if (g.dir === 1) {
          return { yon: 'long', stop: g.bot, sebep: 'Bullish FVG retest (EMA' + emaPeriyot + ' ustunde)', fvgYas };
        } else {
          return { yon: 'short', stop: g.top, sebep: 'Bearish FVG retest (EMA' + emaPeriyot + ' altinda)', fvgYas };
        }
      }
    }

    return null;
  }
}
