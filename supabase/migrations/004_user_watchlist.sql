-- Migration 004: user watchlist for TradingView alert subscriptions
-- Applied: 2026-03-23

CREATE TABLE IF NOT EXISTS user_watchlist (
  id          BIGSERIAL PRIMARY KEY,
  telegram_id BIGINT NOT NULL,
  symbol      TEXT NOT NULL,
  timeframe   TEXT NOT NULL DEFAULT '4h',
  active      BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(telegram_id, symbol)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_telegram_id ON user_watchlist(telegram_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_symbol_active ON user_watchlist(symbol, active);

-- RPC: atomic message counter increment (avoids SELECT + UPDATE race)
CREATE OR REPLACE FUNCTION increment_messages(uid BIGINT)
RETURNS void LANGUAGE sql AS $$
  UPDATE bot_users
  SET messages_count = COALESCE(messages_count, 0) + 1,
      updated_at = NOW()
  WHERE telegram_id = uid;
$$;
