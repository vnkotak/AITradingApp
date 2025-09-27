/*
Market data adapter with API-first, mock fallback.

Usage:
- Import getMarketAdapter() and call methods; it will choose API adapter if NEXT_PUBLIC_API_BASE is set and responsive, otherwise mock.
*/

import axios from 'axios'

export type Timeframe = '1m' | '5m' | '15m' | '1h' | '1d'

export type SymbolInfo = {
	ticker: string
	exchange: 'NSE' | 'BSE'
	name?: string
	sector?: string
}

export type Candle = { ts: string, open: number, high: number, low: number, close: number, volume?: number }

export type MarketOverview = {
	direction: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
	advanceDecline: { advancers: number, decliners: number }
	avgChangePct: number
}

export interface MarketAdapter {
	getSymbols(): Promise<SymbolInfo[]>
	getOverview(): Promise<MarketOverview>
	getCandles(ticker: string, exchange: 'NSE'|'BSE', tf: Timeframe, lookback?: number): Promise<Candle[]>
	getLastPrice(ticker: string, exchange: 'NSE'|'BSE'): Promise<number>
}

const API = process.env.NEXT_PUBLIC_API_BASE

class ApiAdapter implements MarketAdapter {
	async getSymbols(): Promise<SymbolInfo[]> {
		const url = `${API}/symbols?active=true`
		const res = await axios.get(url)
		return res.data || []
	}
	async getOverview(): Promise<MarketOverview> {
		// Approximate using latest close vs previous for first ~30 symbols
		const syms = (await this.getSymbols()).slice(0, 30)
		let up = 0, down = 0
		const changes: number[] = []
		for (const s of syms) {
			const candles = await this.getCandles(s.ticker, s.exchange, '1d', 3)
			if (candles.length < 2) continue
			const prev = candles[candles.length-2].close
			const last = candles[candles.length-1].close
			const ch = ((last - prev) / (prev || 1)) * 100
			changes.push(ch)
			if (ch >= 0) up++; else down++
		}
		const avg = changes.length? (changes.reduce((a,b)=>a+b,0)/changes.length) : 0
		const direction = avg > 0.2 ? 'BULLISH' : (avg < -0.2 ? 'BEARISH' : 'NEUTRAL')
		return { direction, advanceDecline: { advancers: up, decliners: down }, avgChangePct: avg }
	}
	async getCandles(ticker: string, exchange: 'NSE'|'BSE', tf: Timeframe, lookback: number = 5): Promise<Candle[]> {
		const url = `${API}/candles/ticker/${ticker}?exchange=${exchange}&tf=${tf}&limit=${tf==='1d'? 120 : 500}`
		const res = await axios.get(url)
		return res.data || []
	}
	async getLastPrice(ticker: string, exchange: 'NSE'|'BSE'): Promise<number> {
		const c = await this.getCandles(ticker, exchange, '1m', 1)
		if (!c.length) return 0
		return Number(c[c.length-1].close)
	}
}

// -------- Mock implementation ---------

const SEED: SymbolInfo[] = [
	{ ticker: 'RELIANCE', exchange: 'NSE', name: 'Reliance Industries', sector: 'Energy' },
	{ ticker: 'TCS', exchange: 'NSE', name: 'TCS', sector: 'IT' },
	{ ticker: 'HDFCBANK', exchange: 'NSE', name: 'HDFC Bank', sector: 'Financials' },
	{ ticker: 'INFY', exchange: 'NSE', name: 'Infosys', sector: 'IT' },
	{ ticker: 'ITC', exchange: 'NSE', name: 'ITC', sector: 'Consumer Staples' },
]

type PriceState = { last: number, candles: Record<Timeframe, Candle[]> }

const mockState: Record<string, PriceState> = {}

function initTicker(key: string, start: number) {
	if (mockState[key]) return
	const now = Date.now()
	const tfToMs: Record<Timeframe, number> = { '1m': 60_000, '5m': 300_000, '15m': 900_000, '1h': 3_600_000, '1d': 86_400_000 }
	const candlesByTf: Record<Timeframe, Candle[]> = { '1m': [], '5m': [], '15m': [], '1h': [], '1d': [] }
	for (const tf of Object.keys(tfToMs) as Timeframe[]) {
		const step = tfToMs[tf]
		let px = start
		const arr: Candle[] = []
		for (let i = 200; i > 0; i--) {
			const ts = new Date(now - i*step).toISOString()
			const change = (Math.random()-0.5) * (tf==='1d'? 10 : 1)
			const open = px
			px = Math.max(1, px + change)
			const close = px
			const high = Math.max(open, close) + Math.random()* (tf==='1d'? 5 : 0.5)
			const low = Math.min(open, close) - Math.random()* (tf==='1d'? 5 : 0.5)
			arr.push({ ts, open, high, low, close, volume: 100000 + Math.random()*50000 })
		}
		candlesByTf[tf] = arr
	}
	mockState[key] = { last: start, candles: candlesByTf }
}

// advance mock every 5 seconds for 1m; aggregate to higher TFs lazily when requested
if (typeof window !== 'undefined') {
	setInterval(() => {
		for (const s of SEED) {
			const key = `${s.ticker}.${s.exchange}`
			initTicker(key, 2000 + Math.random()*1000)
			const st = mockState[key]
			const arr = st.candles['1m']
			const last = arr[arr.length-1]
			const newClose = Math.max(1, last.close + (Math.random()-0.5)*2)
			const newHigh = Math.max(last.high, newClose)
			const newLow = Math.min(last.low, newClose)
			arr[arr.length-1] = { ...last, high: newHigh, low: newLow, close: newClose }
			// every tick, occasionally push new bar
			if (Math.random() > 0.7) {
				const ts = new Date().toISOString()
				arr.push({ ts, open: newClose, high: newClose, low: newClose, close: newClose, volume: 100000 })
				if (arr.length > 500) arr.shift()
			}
			st.last = newClose
		}
	}, 5000)
}

class MockAdapter implements MarketAdapter {
	async getSymbols(): Promise<SymbolInfo[]> {
		return SEED
	}
	async getOverview(): Promise<MarketOverview> {
		let up = 0, down = 0, changes: number[] = []
		for (const s of SEED) {
			const key = `${s.ticker}.${s.exchange}`
			initTicker(key, 2000 + Math.random()*1000)
			const arr = mockState[key].candles['1d']
			if (arr.length < 2) continue
			const prev = arr[arr.length-2].close
			const last = arr[arr.length-1].close
			const ch = ((last - prev) / (prev || 1)) * 100
			changes.push(ch)
			if (ch >= 0) up++; else down++
		}
		const avg = changes.length? (changes.reduce((a,b)=>a+b,0)/changes.length) : 0
		const direction = avg > 0.2 ? 'BULLISH' : (avg < -0.2 ? 'BEARISH' : 'NEUTRAL')
		return { direction, advanceDecline: { advancers: up, decliners: down }, avgChangePct: avg }
	}
	async getCandles(ticker: string, exchange: 'NSE'|'BSE', tf: Timeframe, _lookback: number = 5): Promise<Candle[]> {
		const key = `${ticker}.${exchange}`
		initTicker(key, 2000 + Math.random()*1000)
		return mockState[key].candles[tf]
	}
	async getLastPrice(ticker: string, exchange: 'NSE'|'BSE'): Promise<number> {
		const cs = await this.getCandles(ticker, exchange, '1m')
		return cs.length? cs[cs.length-1].close : 0
	}
}

let chosen: MarketAdapter | null = null

export async function getMarketAdapter(): Promise<MarketAdapter> {
	if (chosen) return chosen
	if (API) {
		try {
			await axios.get(`${API}/health`, { timeout: 2000 })
			chosen = new ApiAdapter()
			return chosen
		} catch {}
	}
	chosen = new MockAdapter()
	return chosen
}


