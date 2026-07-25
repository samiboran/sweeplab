"""SweepLab Bot — Streamlit izleme paneli.

Botla aynı `bot_state/state.json` dosyasını okur, ayrı bir süreç olarak
çalışır. Çalıştırma: `streamlit run panel/app.py`

Kill switch butonu, dosya tabanlı bayrağı (`bot_state/DUR`) doğrudan
oluşturur/kaldırır — bot her yeni sinyalde bu dosyayı kontrol eder.
"""
from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from bot.config import CONFIG
from bot.state import StateStore

st.set_page_config(page_title="SweepLab Bot Panel", page_icon="🤖", layout="wide")

state = StateStore(CONFIG)
snap = state.snapshot()
kill_active = state.is_kill_switch_active()

st.title("🤖 SweepLab — Likidite Süpürme Bot Paneli")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Faz", snap.get("phase", CONFIG.phase))
col2.metric("Kill switch", "AKTİF 🛑" if kill_active else "kapalı ✅")
col3.metric("Günlük PnL (USDT)", f"{snap.get('daily_pnl_usdt', 0):.2f}")
limit_hit = snap.get("daily_loss_limit_hit", False)
col4.metric(
    "Günlük zarar limiti",
    "AŞILDI 🚨" if limit_hit else f"%{CONFIG.daily_loss_limit_pct} (normal)",
)

st.divider()

st.subheader("Acil durdurma")
kcol1, kcol2 = st.columns(2)
if kcol1.button("🛑 BOTU DURDUR", type="primary", disabled=kill_active, use_container_width=True):
    state.set_kill_switch(True)
    st.rerun()
if kcol2.button("▶️ Devam et", disabled=not kill_active, use_container_width=True):
    state.set_kill_switch(False)
    state.set_daily_loss_limit_hit(False)
    st.rerun()
st.caption("Aynı işlem Telegram üzerinden de yapılabilir: `/dur` ve `/devam`.")

st.divider()

st.subheader("Sembol durumu")
rows = []
for symbol in CONFIG.symbols:
    info = snap.get("symbols", {}).get(symbol, {})
    rows.append(
        {
            "Sembol": symbol,
            "Son fiyat": info.get("last_price"),
            "Trend": info.get("trend", "-"),
            "İzlenen seviye (İZLE)": info.get("watch_level"),
            "Tetiklenirse yön": info.get("watch_direction"),
            "Son swing high": info.get("last_swing_high"),
            "Son swing low": info.get("last_swing_low"),
            "Güncelleme": info.get("updated_at"),
        }
    )
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

st.divider()

positions = snap.get("positions", {})
st.subheader(f"Açık pozisyonlar ({len(positions)}/{CONFIG.max_concurrent_positions})")
if positions:
    st.dataframe(pd.DataFrame(list(positions.values())), use_container_width=True, hide_index=True)
else:
    st.caption("Açık pozisyon yok.")

st.divider()

trades = snap.get("trades", [])
st.subheader("İşlem geçmişi")
if trades:
    df = pd.DataFrame(list(reversed(trades)))
    st.dataframe(df, use_container_width=True, hide_index=True)
    wins = sum(1 for t in trades if t["pnl_usdt"] > 0)
    total_pnl = sum(t["pnl_usdt"] for t in trades)
    st.caption(
        f"Toplam {len(trades)} işlem · kazanma oranı %{100 * wins / len(trades):.1f} "
        f"· toplam PnL {total_pnl:.2f} USDT"
    )
else:
    st.caption("Henüz kapanmış işlem yok.")

with st.sidebar:
    st.header("Bot parametreleri")
    st.write(f"**Semboller:** {', '.join(CONFIG.symbols)}")
    st.write(f"**Zaman aralığı:** {CONFIG.kline_interval}")
    st.write(f"**Swing penceresi:** {CONFIG.swing_window}")
    st.write(f"**Min. rejection fitil:** %{CONFIG.wick_min_pct * 100:.0f}")
    st.write(f"**RR:** {CONFIG.rr}")
    st.write(f"**Stop buffer:** %{CONFIG.stop_buffer_pct * 100:.2f}")
    st.write(f"**Kaldıraç:** {CONFIG.leverage}x")
    st.write(f"**İşlem başına risk:** %{CONFIG.risk_pct_per_trade}")
    st.write(f"**Günlük zarar limiti:** %{CONFIG.daily_loss_limit_pct}")
    st.write(f"**Maks. eşzamanlı pozisyon:** {CONFIG.max_concurrent_positions}")
    st.write(f"**Test ağı (testnet):** {'Evet' if CONFIG.is_testnet else 'Hayır — GERÇEK HESAP'}")
    st.divider()
    auto_refresh = st.checkbox("Otomatik yenile (10sn)", value=True)

st.caption(f"Son güncelleme: {snap.get('updated_at')}")

if auto_refresh:
    time.sleep(10)
    st.rerun()
