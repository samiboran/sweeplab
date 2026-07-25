"""Bot yapılandırması. Tüm parametreler ortam değişkenlerinden (.env) okunur,
kodda sabit değer yoktur — bkz. .env.example.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - python-dotenv opsiyonel
    pass


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return val.strip().lower() in ("1", "true", "yes", "on", "evet")


def _env_float(name: str, default: float) -> float:
    val = os.getenv(name)
    return float(val) if val not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    val = os.getenv(name)
    return int(val) if val not in (None, "") else default


def _env_list(name: str, default: list[str]) -> list[str]:
    val = os.getenv(name)
    if not val:
        return list(default)
    return [s.strip().upper() for s in val.split(",") if s.strip()]


# --- Rollout fazları (open_question: fazlar arası geçiş bu değişkenle yapılır) ---
PHASE_TESTNET_AUTO = "testnet_auto"          # Faz 1: testnet + tam otomatik emir
PHASE_LIVE_NOTIFY_ONLY = "live_notify_only"  # Faz 2: gerçek hesap, sadece Telegram bildirimi
PHASE_LIVE_AUTO = "live_auto"                # Faz 3: gerçek hesap + tam otomatik, küçük sermaye

VALID_PHASES = (PHASE_TESTNET_AUTO, PHASE_LIVE_NOTIFY_ONLY, PHASE_LIVE_AUTO)


@dataclass
class Config:
    phase: str = field(default_factory=lambda: os.getenv("BOT_PHASE", PHASE_TESTNET_AUTO))

    # --- Binance API (SADECE "Futures Trading" izni; "Withdrawal" KESİNLİKLE kapalı olmalı) ---
    binance_api_key: str = field(default_factory=lambda: os.getenv("BINANCE_API_KEY", ""))
    binance_api_secret: str = field(default_factory=lambda: os.getenv("BINANCE_API_SECRET", ""))

    # --- Telegram ---
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))

    # --- Semboller / zaman aralığı ---
    symbols: list[str] = field(
        default_factory=lambda: _env_list("BOT_SYMBOLS", ["BTCUSDT", "ETHUSDT", "AVAXUSDT", "SOLUSDT"])
    )
    kline_interval: str = field(default_factory=lambda: os.getenv("BOT_INTERVAL", "5m"))
    ws_base_url: str = field(
        default_factory=lambda: os.getenv("BINANCE_WS_BASE", "wss://stream.binance.com:9443")
    )

    # --- Strateji parametreleri (params_to_expose ile birebir) ---
    swing_window: int = field(default_factory=lambda: _env_int("SWING_WINDOW", 5))
    wick_min_pct: float = field(default_factory=lambda: _env_float("WICK_MIN_PCT", 0.40))
    rr: float = field(default_factory=lambda: _env_float("RR", 2.0))
    stop_buffer_pct: float = field(default_factory=lambda: _env_float("STOP_BUFFER_PCT", 0.0005))

    # --- Risk / güvenlik ---
    leverage: int = field(default_factory=lambda: _env_int("LEVERAGE", 10))
    risk_pct_per_trade: float = field(default_factory=lambda: _env_float("RISK_PCT_PER_TRADE", 2.0))
    daily_loss_limit_pct: float = field(default_factory=lambda: _env_float("DAILY_LOSS_LIMIT_PCT", 20.0))
    max_concurrent_positions: int = field(default_factory=lambda: _env_int("MAX_CONCURRENT_POSITIONS", 1))

    # --- Durum / kill switch ---
    state_dir: Path = field(default_factory=lambda: Path(os.getenv("BOT_STATE_DIR", "bot_state")))
    kill_switch_filename: str = "DUR"

    # --- Telegram komut dinleyici ---
    telegram_poll_interval_sec: float = field(
        default_factory=lambda: _env_float("TELEGRAM_POLL_INTERVAL_SEC", 3.0)
    )

    def __post_init__(self) -> None:
        if self.phase not in VALID_PHASES:
            raise ValueError(f"Geçersiz BOT_PHASE: {self.phase!r} (geçerli değerler: {VALID_PHASES})")
        if self.max_concurrent_positions < 1:
            raise ValueError("MAX_CONCURRENT_POSITIONS en az 1 olmalı")
        self.state_dir.mkdir(parents=True, exist_ok=True)

    @property
    def is_testnet(self) -> bool:
        return self.phase == PHASE_TESTNET_AUTO

    @property
    def auto_execute(self) -> bool:
        """True ise sinyal geldiğinde emir otomatik açılır; False ise sadece bildirim gider (Faz 2)."""
        return self.phase in (PHASE_TESTNET_AUTO, PHASE_LIVE_AUTO)

    @property
    def kill_switch_path(self) -> Path:
        return self.state_dir / self.kill_switch_filename

    @property
    def state_file(self) -> Path:
        return self.state_dir / "state.json"


CONFIG = Config()
