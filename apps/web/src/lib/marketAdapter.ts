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
		try {
			const url = `${API}/symbols?active=true`
			const res = await axios.get(url)
			return res.data || []
		} catch (error: any) {
			console.error('Failed to fetch symbols from API:', error)
			if (error.response?.status === 503) {
				throw new Error('Database not configured. Please set up SUPABASE_URL and SUPABASE_SERVICE_KEY.')
			}
			throw new Error(`API Error: ${error.response?.data?.detail || error.message}`)
		}
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
	async getCandles(ticker: string, exchange: 'NSE'|'BSE', tf: Timeframe, lookback: number = 5, fresh: boolean = false): Promise<Candle[]> {
		try {
			// Fetch from database (with fresh data if requested)
			const url = `${API}/candles/ticker/${ticker}?exchange=${exchange}&tf=${tf}&limit=${tf==='1d'? 120 : 500}&fresh=${fresh}`
			const res = await axios.get(url)
			const candles = res.data || []

			// If we got data from database, return it
			if (candles.length > 0) {
				console.log(`✅ Found ${candles.length} ${tf} candles in database for ${ticker}${fresh ? ' (fresh data)' : ''}`)
				return candles
			}

			// If no data in database, fetch fresh data from Yahoo Finance
			console.log(`📊 No ${tf} data in database for ${ticker}, fetching from Yahoo Finance...`)

			try {
				const fetchUrl = `${API}/candles/fetch?ticker=${ticker}&exchange=${exchange}&tf=${tf}&lookback_days=${lookback}`
				await axios.post(fetchUrl)
				console.log(`✅ Successfully fetched and stored ${tf} data from Yahoo Finance`)

				// Try to fetch from database again after population
				const retryRes = await axios.get(url)
				const freshCandles = retryRes.data || []

				if (freshCandles.length > 0) {
					console.log(`✅ Retrieved ${freshCandles.length} fresh ${tf} candles for ${ticker}`)
					return freshCandles
				} else {
					console.warn(`⚠️ Still no ${tf} data after fetching from Yahoo`)
					return []
				}

			} catch (fetchError: any) {
				console.error(`❌ Failed to fetch ${tf} data from Yahoo Finance:`, fetchError.response?.data || fetchError.message)
				return []
			}

		} catch (error: any) {
			console.error(`Failed to fetch candles for ${ticker} from API:`, error)
			if (error.response?.status === 503) {
				throw new Error('Database not configured. Please set up SUPABASE_URL and SUPABASE_SERVICE_KEY.')
			}
			if (error.response?.status === 404) {
				throw new Error(`Symbol ${ticker} not found in ${exchange} exchange.`)
			}
			throw new Error(`API Error: ${error.response?.data?.detail || error.message}`)
		}
	}
	async getLastPrice(ticker: string, exchange: 'NSE'|'BSE'): Promise<number> {
		try {
			// First try to get real-time price from Yahoo Finance
			const realTimeUrl = `${API}/prices/realtime?ticker=${ticker}&exchange=${exchange}`
			const realTimeResponse = await axios.get(realTimeUrl, { timeout: 3000 })

			if (realTimeResponse.data && realTimeResponse.data.price && realTimeResponse.data.price > 0) {
				console.log(`✅ Real-time price for ${ticker}: ₹${realTimeResponse.data.price}`)
				return Number(realTimeResponse.data.price)
			} else {
				console.warn(`⚠️ Real-time price returned 0 for ${ticker}, trying fallback`)
			}
		} catch (error: any) {
			console.warn(`⚠️ Real-time price fetch failed for ${ticker}, falling back to candles:`, error?.message || 'Unknown error')
		}

		// Enhanced fallback to candles - try multiple timeframes
		try {
			// First try 1m candles for most recent price
			let c = await this.getCandles(ticker, exchange, '1m', 1)
			if (c.length > 0) {
				const price = Number(c[c.length-1].close)
				if (price > 0) {
					console.log(`✅ Fallback price from 1m candles for ${ticker}: ₹${price}`)
					return price
				}
			}

			// If 1m fails, try 5m candles
			c = await this.getCandles(ticker, exchange, '5m', 1)
			if (c.length > 0) {
				const price = Number(c[c.length-1].close)
				if (price > 0) {
					console.log(`✅ Fallback price from 5m candles for ${ticker}: ₹${price}`)
					return price
				}
			}

			// Final fallback to daily candles
			c = await this.getCandles(ticker, exchange, '1d', 1)
			if (c.length > 0) {
				const price = Number(c[c.length-1].close)
				if (price > 0) {
					console.log(`✅ Fallback price from daily candles for ${ticker}: ₹${price}`)
					return price
				}
			}

			console.warn(`❌ No valid price found in candles for ${ticker}`)
			return 0

		} catch (candleError: any) {
			console.error(`❌ Error fetching fallback candle data for ${ticker}:`, candleError?.message || 'Unknown error')
			return 0
		}
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
		// Use 1m timeframe to get the latest price
		const cs = await this.getCandles(ticker, exchange, '1m', 1)
		return cs.length ? cs[cs.length-1].close : 0
	}
}

// Cache API adapter and connection status
let chosen: MarketAdapter | null = null
let apiConnectionStatus: 'connected' | 'disconnected' | 'unknown' = 'unknown'
let lastHealthCheck = 0
const HEALTH_CHECK_INTERVAL = 30000 // Check every 30 seconds instead of every call

export async function getMarketAdapter(): Promise<MarketAdapter> {
	if (chosen) return chosen
	if (API) {
		// Only check health if we haven't checked recently
		const now = Date.now()
		try {
			if (apiConnectionStatus === 'unknown' || (now - lastHealthCheck) > HEALTH_CHECK_INTERVAL) {
				console.log(`Checking API connection at ${API}`)
				await axios.get(`${API}/health`, { timeout: 3000 })
				console.log('✅ API connection successful')
				apiConnectionStatus = 'connected'
				lastHealthCheck = now
			}

			chosen = new ApiAdapter()
			return chosen
		} catch (error: any) {
			console.error('❌ API connection failed:', error)
			apiConnectionStatus = 'disconnected'
			lastHealthCheck = now
			throw new Error(`API server not available at ${API}. Please ensure the API server is running on http://localhost:8000`)
		}
	} else {
		console.error('No NEXT_PUBLIC_API_BASE configured')
		throw new Error('API base URL not configured. Please set NEXT_PUBLIC_API_BASE environment variable.')
	}
}

export function getApiConnectionStatus(): 'connected' | 'disconnected' | 'unknown' {
	return apiConnectionStatus
}


