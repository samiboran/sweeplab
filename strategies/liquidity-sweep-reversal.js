// --- Liquidity Sweep Reversal (Trend Devami Sonrasi Donus) ---
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

    const w = p.swingWindow || 5;
    const wickMin = p.wickMinPct || 0.40;

    if (s.lastH === undefined) {
      s.lastH = null; s.prevH = null;
      s.lastL = null; s.prevL = null;
      s.trend = null;
      s.confirmedUpTo = -1;
      s.lastShortLevel = null;
      s.lastLongLevel = null;
    }

    const confirmIdx = i - w;
    if (confirmIdx >= w && confirmIdx > s.confirmedUpTo) {
      const seg = c.slice(confirmIdx - w, confirmIdx + w + 1);
      const segHi = seg.map(x => x.high);
      const segLo = seg.map(x => x.low);
      const hiMax = Math.max(...segHi);
      const loMin = Math.min(...segLo);
      const candidate = c[confirmIdx];

      const isSwingHigh = candidate.high === hiMax && segHi.filter(v => v === hiMax).length === 1;
      const isSwingLow  = candidate.low  === loMin && segLo.filter(v => v === loMin).length === 1;

      if (isSwingHigh) {
        if (s.lastH !== null) s.prevH = s.lastH;
        s.lastH = candidate.high;
      }
      if (isSwingLow) {
        if (s.lastL !== null) s.prevL = s.lastL;
        s.lastL = candidate.low;
      }

      if (s.lastH !== null && s.prevH !== null && s.lastL !== null && s.prevL !== null) {
        if (s.lastH > s.prevH && s.lastL > s.prevL) s.trend = 'up';
        else if (s.lastH < s.prevH && s.lastL < s.prevL) s.trend = 'down';
      }
      s.confirmedUpTo = confirmIdx;
    }

    const rng = bar.high - bar.low;
    if (rng <= 0) return null;

    if (s.trend === 'up' && s.prevH !== null && bar.high > s.prevH) {
      const bodyHi = Math.max(bar.open, bar.close);
      const upperWick = bar.high - bodyHi;
      if (upperWick > wickMin * rng && s.lastShortLevel !== s.prevH) {
        s.lastShortLevel = s.prevH;
        return { yon: 'short', stop: bar.high * 1.0005, sebep: 'Swing high supurme (' + w + ' bar onayli)' };
      }
    }

    if (s.trend === 'down' && s.prevL !== null && bar.low < s.prevL) {
      const bodyLo = Math.min(bar.open, bar.close);
      const lowerWick = bodyLo - bar.low;
      if (lowerWick > wickMin * rng && s.lastLongLevel !== s.prevL) {
        s.lastLongLevel = s.prevL;
        return { yon: 'long', stop: bar.low * 0.9995, sebep: 'Swing low supurme (' + w + ' bar onayli)' };
      }
    }

    return null;
  }
}
