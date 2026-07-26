// --- 5dk Liquidity Sweep + 15dk yon teyidi (DENEYSEL, dogrulanmamis) ---
// NOT: Bu strateji rastgele kontrol testinde totolojik cikti (bkz. sohbet gecmisi).
// Buraya sadece GOZLEM/veri toplama amacli ekleniyor, canli islem onayi degil.
//
// uret(ctx) HER mumda cagrilir (5dk grafikte calismasi bekleniyor). ctx:
//   bar, i, c, p, h, s, pozisyon (Liquidity Sweep Reversal ile ayni format)
//
// 15dk yonu, GERCEK 15dk verisi yerine SON 3 ADET 5dk barin net degisiminden
// turetiliyor (3x5dk=15dk) -- eger motor gercek çoklu zaman dilimi verisi
// sunuyorsa (ör. ctx.c15 gibi bir alan varsa) onu tercih et, yoksa bu yaklasik
// yontemi kullan.

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
      if (isSwingHigh) { if (s.lastH !== null) s.prevH = s.lastH; s.lastH = candidate.high; }
      if (isSwingLow)  { if (s.lastL !== null) s.prevL = s.lastL; s.lastL = candidate.low; }
      if (s.lastH !== null && s.prevH !== null && s.lastL !== null && s.prevL !== null) {
        if (s.lastH > s.prevH && s.lastL > s.prevL) s.trend = 'up';
        else if (s.lastH < s.prevH && s.lastL < s.prevL) s.trend = 'down';
      }
      s.confirmedUpTo = confirmIdx;
    }

    const rng = bar.high - bar.low;
    if (rng <= 0) return null;

    // --- 15dk yonu (yaklasik): son 3 kapali 5dk barin net degisimi ---
    function derived15mDirection() {
      if (i < 3) return null;
      const b0 = c[i - 3];
      const b3 = bar;
      if (b3.close > b0.open) return 'up';
      if (b3.close < b0.open) return 'down';
      return 'flat';
    }

    let cand = null;
    if (s.trend === 'up' && s.prevH !== null && bar.high > s.prevH) {
      const bodyHi = Math.max(bar.open, bar.close);
      const upperWick = bar.high - bodyHi;
      if (upperWick > wickMin * rng && s.lastShortLevel !== s.prevH) {
        cand = { yon: 'short', level: s.prevH };
      }
    }
    if (s.trend === 'down' && s.prevL !== null && bar.low < s.prevL) {
      const bodyLo = Math.min(bar.open, bar.close);
      const lowerWick = bodyLo - bar.low;
      if (lowerWick > wickMin * rng && s.lastLongLevel !== s.prevL) {
        cand = { yon: 'long', level: s.prevL };
      }
    }
    if (!cand) return null;

    const dir15 = derived15mDirection();
    const agrees = (cand.yon === 'short' && dir15 === 'down') || (cand.yon === 'long' && dir15 === 'up');

    if (cand.yon === 'short') s.lastShortLevel = cand.level;
    if (cand.yon === 'long') s.lastLongLevel = cand.level;

    const sebep = agrees
      ? '5dk sweep + 15dk UYUSUYOR (deneysel, dogrulanmamis)'
      : '5dk sweep + 15dk TERS (deneysel, dogrulanmamis)';

    return {
      yon: cand.yon,
      stop: cand.yon === 'short' ? bar.high * 1.0005 : bar.low * 0.9995,
      sebep: sebep,
      etiket: agrees ? 'UYUSAN' : 'TERS'   // varsa UI'da renklendirmek icin (kirmizi/yesil)
    };
  }
}
