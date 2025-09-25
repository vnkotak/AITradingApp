# AITradingApp (Web)

Run locally:

```bash
cd apps/web
npm install
npm run dev
```

Environment:
- NEXT_PUBLIC_API_BASE: optional. If set and reachable, the app reads data from the FastAPI backend. If missing/unreachable, a realistic mock adapter provides symbols, candles, and prices.

Key features implemented:
- Markets: market overview (bullish/bearish via average % change), searchable grid of stocks with price change and 1D sparkline.
- Trading: lightweight-charts candlesticks with timeframe selector; instant paper buy/sell via a zustand store; TP/SL auto-exit supported by store hooks.
- Signals: rule-based SMA crossover with RSI guard, polled every 10s. Replaceable via `src/lib/signals.ts`.
- Portfolio & History: positions, unrealized P/L (using last price), orders table, and basic stats.

Architecture notes:
- Market adapter: `src/lib/marketAdapter.ts` chooses API-first, falls back to mock.
- Signals engine: `src/lib/signals.ts` with `getSignals()` and `computeIndicators()`; plug an ML model by swapping in a remote scorer.
- Trading store: `src/store/trading.ts` persists to localStorage and simulates fills at last price. TP/SL handled via `markPrice()` calls from chart polling.

Manual verification checklist:
1. Markets tab shows direction, A/D, and cards with sparkline; search filters results.
2. Click Trading tab, chart renders and updates; switch timeframe; place Buy/Sell — orders appear in History, position in Portfolio, P/L updates.
3. Signals tab lists BUY/SELL rows for the chosen ticker.
4. Portfolio tab shows last price and unrealized P/L.
5. History tab shows recent orders; no console errors.

Deploy on Vercel:
- Set project root to `apps/web`.
- Add `NEXT_PUBLIC_API_BASE` to use your FastAPI service (optional).
