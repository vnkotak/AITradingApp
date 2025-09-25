/*
Rule-based signals engine for MVP with a clear ML hook.

Exports:
- getSignals(tickers): computes BUY/SELL signals using SMA crossover and RSI-like proxy.
- computeIndicators(candles): helper to compute SMA(20/50) and RSI14 approximation.

To plug a model: replace score computation with async call to a model server,
or mix model score into confidence. Keep the Signal type stable.
*/

import type { Candle } from './marketAdapter'
import { getMarketAdapter } from './marketAdapter'

export type Signal = {
	ticker: string
	exchange: 'NSE'|'BSE'
	strategy: string
	action: 'BUY'|'SELL'
	entry: number
	stop: number
	target?: number
	confidence: number // 0..1
	ts: string
}

function sma(values: number[], length: number): number[] {
	const out: number[] = []
	let sum = 0
	for (let i = 0; i < values.length; i++) {
		sum += values[i]
		if (i >= length) sum -= values[i - length]
		out.push(i >= length-1 ? sum / length : NaN)
	}
	return out
}

function rsi(close: number[], length = 14): number[] {
	const gains: number[] = []
	const losses: number[] = []
	for (let i = 1; i < close.length; i++) {
		const ch = close[i] - close[i-1]
		gains.push(Math.max(0, ch))
		losses.push(Math.max(0, -ch))
	}
	const avgGain: number[] = []
	const avgLoss: number[] = []
	let g = 0, l = 0
	for (let i = 0; i < gains.length; i++) {
		g = (g * (length-1) + gains[i]) / length
		l = (l * (length-1) + losses[i]) / length
		avgGain.push(g)
		avgLoss.push(l)
	}
	const rs: number[] = avgGain.map((ag, i) => (avgLoss[i] === 0 ? 100 : ag / (avgLoss[i] || 1e-9)))
	const rsiVals: number[] = rs.map(r => 100 - (100 / (1 + r)))
	return [NaN, ...rsiVals]
}

export function computeIndicators(candles: Candle[]) {
	const close = candles.map(c => c.close)
	const sma20 = sma(close, 20)
	const sma50 = sma(close, 50)
	const rsi14 = rsi(close, 14)
	return { sma20, sma50, rsi14 }
}

export async function getSignals(tickers: { ticker: string, exchange: 'NSE'|'BSE' }[]): Promise<Signal[]> {
	const adapter = await getMarketAdapter()
	const out: Signal[] = []
	for (const t of tickers) {
		const candles = await adapter.getCandles(t.ticker, t.exchange, '1m')
		if (!candles || candles.length < 60) continue
		const { sma20, sma50, rsi14 } = computeIndicators(candles)
		const n = candles.length
		const last = candles[n-1]
		const prev = candles[n-2]
		const cSMA20 = sma20[n-1]
		const pSMA20 = sma20[n-2]
		const cSMA50 = sma50[n-1]
		const pSMA50 = sma50[n-2]
		const cRSI = rsi14[n-1]
		const crossedUp = pSMA20 <= pSMA50 && cSMA20 > cSMA50
		const crossedDn = pSMA20 >= pSMA50 && cSMA20 < cSMA50
		if (crossedUp && cRSI < 80) {
			const entry = last.close
			const stop = Math.min(prev.low, entry * 0.99)
			const target = entry + 2 * (entry - stop)
			out.push({ ticker: t.ticker, exchange: t.exchange, strategy: 'sma_cross', action: 'BUY', entry, stop, target, confidence: 0.6, ts: last.ts })
		} else if (crossedDn && cRSI > 20) {
			const entry = last.close
			const stop = Math.max(prev.high, entry * 1.01)
			const target = entry - 2 * (stop - entry)
			out.push({ ticker: t.ticker, exchange: t.exchange, strategy: 'sma_cross', action: 'SELL', entry, stop, target, confidence: 0.6, ts: last.ts })
		}
	}
	return out
}


