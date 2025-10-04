import { create } from 'zustand'

export type OrderSide = 'BUY'|'SELL'
export type OrderType = 'MARKET'|'LIMIT'

export type Position = {
	ticker: string
	exchange: 'NSE'|'BSE'
	qty: number
	avgPrice: number
}

export type Order = {
	id: string
	ts: number
	ticker: string
	exchange: 'NSE'|'BSE'
	side: OrderSide
	type: OrderType
	price?: number
	qty: number
	status: 'NEW'|'FILLED'|'REJECTED'
}

export type Trade = {
	id: string
	ts: number
	ticker: string
	exchange: 'NSE'|'BSE'
	side: OrderSide
	price: number
	qty: number
}

type TP_SL = {
	entry: number
	target?: number
	stop?: number
}

type TradingState = {
	cash: number
	positions: Record<string, Position>
	orders: Order[]
	trades: Trade[]
	getPositionKey: (ticker: string, exchange: 'NSE'|'BSE') => string
	placeOrder: (p: { ticker: string, exchange: 'NSE'|'BSE', side: OrderSide, type?: OrderType, qty: number, price?: number, tp_sl?: TP_SL }) => Promise<void>
	markPrice: (ticker: string, exchange: 'NSE'|'BSE', price: number) => void
	getPnL: (ticker: string, exchange: 'NSE'|'BSE', price: number) => { unrealized: number }
}

const persistKey = 'ai_trading_store_v1'

const load = () => {
	if (typeof window === 'undefined') return null
	try { return JSON.parse(localStorage.getItem(persistKey) || 'null') } catch { return null }
}

const save = (state: any) => {
	if (typeof window === 'undefined') return
	try { localStorage.setItem(persistKey, JSON.stringify(state)) } catch {}
}

export const useTradingStore = create<TradingState>((set, get) => ({
	cash: load()?.cash ?? 1_000_000,
	positions: load()?.positions ?? {},
	orders: load()?.orders ?? [],
	trades: load()?.trades ?? [],
	getPositionKey: (ticker, exchange) => `${ticker}.${exchange}`,
	async placeOrder({ ticker, exchange, side, type = 'MARKET', qty, price, tp_sl }) {
		try {
			// Call the backend API for proper paper trading execution
			const API_BASE = process.env.NEXT_PUBLIC_API_BASE
			if (!API_BASE) {
				throw new Error('API base URL not configured')
			}

			console.log(`📋 Placing ${side} order: ${qty} ${ticker}.${exchange}`)

			const orderRequest = {
				ticker,
				exchange,
				side,
				type,
				qty,
				...(price && { price })
			}

			const response = await fetch(`${API_BASE}/orders`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(orderRequest)
			})

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}))
				throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`)
			}

			const orderData = await response.json()
			console.log('✅ Order placed successfully:', orderData)

			// Update local state with backend order data
			const order: Order = {
				id: orderData.id || Math.random().toString(36).slice(2),
				ts: Date.now(),
				ticker,
				exchange,
				side,
				type,
				price: orderData.price,
				qty,
				status: orderData.status || 'FILLED'
			}

			// If order was filled, create trade record
			if (orderData.status === 'FILLED' && orderData.price) {
				const trade: Trade = {
					id: orderData.id || Math.random().toString(36).slice(2),
					ts: Date.now(),
					ticker,
					exchange,
					side,
					price: orderData.price,
					qty
				}

				// Update positions based on fill
				const s = get()
				const key = get().getPositionKey(ticker, exchange)
				const positions = { ...s.positions }
				const existing = positions[key]
				let newQty = (existing?.qty || 0) + (side === 'BUY' ? qty : -qty)
				let avgPrice = existing?.avgPrice || 0
				let cash = s.cash

				if (!existing) {
					avgPrice = orderData.price
				} else {
					if (existing.qty === 0 || (existing.qty > 0 && side === 'BUY') || (existing.qty < 0 && side === 'SELL')) {
						avgPrice = (existing.avgPrice * Math.abs(existing.qty) + orderData.price * qty) / Math.max(1, Math.abs(newQty))
					} else {
						const closed = Math.min(Math.abs(existing.qty), qty)
						const pnl = (orderData.price - existing.avgPrice) * (existing.qty > 0 ? closed : -closed)
						cash += pnl
					}
				}

				if (newQty === 0) {
					delete positions[key]
				} else {
					positions[key] = { ticker, exchange, qty: newQty, avgPrice }
				}

				const orders = [order, ...s.orders].slice(0, 200)
				const trades = [trade, ...s.trades].slice(0, 1000)

				set({ positions, cash, orders, trades })
				save({ positions: get().positions, cash: get().cash, orders: get().orders, trades: get().trades })
			}

			// Store TP/SL trackers
			if (tp_sl) {
				;(window as any).__tp_sl__ = (window as any).__tp_sl__ || {}
				const key = get().getPositionKey(ticker, exchange)
				;(window as any).__tp_sl__[key] = tp_sl
			}

		} catch (error) {
			console.error('❌ Order placement failed:', error)

			// Fallback to local simulation if API fails
			console.log('🔄 Falling back to local simulation...')

			const now = Date.now()
			const id = Math.random().toString(36).slice(2)
			const key = get().getPositionKey(ticker, exchange)
			const lastPx = price ?? (window as any).__last_mark__?.[key] ?? 1000 // Fallback price
			const fillPx = lastPx

			const order: Order = { id, ts: now, ticker, exchange, side, type, price: fillPx, qty, status: 'FILLED' }
			const trade: Trade = { id, ts: now, ticker, exchange, side, price: fillPx, qty }

			const s = get()
			const positions = { ...s.positions }
			const existing = positions[key]
			let newQty = (existing?.qty || 0) + (side === 'BUY' ? qty : -qty)
			let avgPrice = existing?.avgPrice || 0
			let cash = s.cash

			if (!existing) {
				avgPrice = fillPx
			} else {
				if (existing.qty === 0 || (existing.qty > 0 && side === 'BUY') || (existing.qty < 0 && side === 'SELL')) {
					avgPrice = (existing.avgPrice * Math.abs(existing.qty) + fillPx * qty) / Math.max(1, Math.abs(newQty))
				} else {
					const closed = Math.min(Math.abs(existing.qty), qty)
					const pnl = (fillPx - existing.avgPrice) * (existing.qty > 0 ? closed : -closed)
					cash += pnl
				}
			}

			if (newQty === 0) {
				delete positions[key]
			} else {
				positions[key] = { ticker, exchange, qty: newQty, avgPrice }
			}

			const orders = [order, ...s.orders].slice(0, 200)
			const trades = [trade, ...s.trades].slice(0, 1000)

			set({ positions, cash, orders, trades })
			save({ positions: get().positions, cash: get().cash, orders: get().orders, trades: get().trades })

			// Show error to user
			alert(`Order placement failed: ${error instanceof Error ? error.message : 'Unknown error'}. Using local simulation.`)
		}
	},
	markPrice(ticker, exchange, price) {
		;(window as any).__last_mark__ = (window as any).__last_mark__ || {}
		const key = get().getPositionKey(ticker, exchange)
		;(window as any).__last_mark__[key] = price
		// auto-exit on TP/SL
		const tracker = (window as any).__tp_sl__?.[key]
		const pos = get().positions[key]
		if (!tracker || !pos) return
		if (pos.qty > 0) {
			if (tracker.stop && price <= tracker.stop) {
				get().placeOrder({ ticker, exchange, side: 'SELL', qty: Math.abs(pos.qty) })
				delete (window as any).__tp_sl__?.[key]
			} else if (tracker.target && price >= tracker.target) {
				get().placeOrder({ ticker, exchange, side: 'SELL', qty: Math.abs(pos.qty) })
				delete (window as any).__tp_sl__?.[key]
			}
		} else if (pos.qty < 0) {
			if (tracker.stop && price >= tracker.stop) {
				get().placeOrder({ ticker, exchange, side: 'BUY', qty: Math.abs(pos.qty) })
				delete (window as any).__tp_sl__?.[key]
			} else if (tracker.target && price <= tracker.target) {
				get().placeOrder({ ticker, exchange, side: 'BUY', qty: Math.abs(pos.qty) })
				delete (window as any).__tp_sl__?.[key]
			}
		}
	},
	getPnL(ticker, exchange, price) {
		const key = get().getPositionKey(ticker, exchange)
		const pos = get().positions[key]
		if (!pos) return { unrealized: 0 }
		const pnl = (price - pos.avgPrice) * (pos.qty > 0 ? Math.abs(pos.qty) : -Math.abs(pos.qty))
		return { unrealized: pnl }
	}
}))


