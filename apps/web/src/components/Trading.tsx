"use client"

import { useEffect, useRef, useState } from 'react'
import { createChart, ISeriesApi } from 'lightweight-charts'
import Signals from './Signals'
import { getMarketAdapter, type Candle, type Timeframe } from '../lib/marketAdapter'
import { useTradingStore } from '../store/trading'

export default function Trading() {
  const [symbol, setSymbol] = useState({ ticker: 'RELIANCE', exchange: 'NSE' as 'NSE'|'BSE' })
  const [tf, setTf] = useState<Timeframe>('1m')
  const [candles, setCandles] = useState<Candle[]|null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const placeOrder = useTradingStore(s => s.placeOrder)
  const markPrice = useTradingStore(s => s.markPrice)

  useEffect(() => {
    if (!containerRef.current) return
    const chart = createChart(containerRef.current, { width: containerRef.current.clientWidth, height: 420, layout: { background: { color: '#0b0f15' }, textColor: '#9ca3af' }, grid: { vertLines: { color: '#111827' }, horzLines: { color: '#111827' } } })
    const series = chart.addCandlestickSeries()
    seriesRef.current = series
    const handleResize = () => chart.applyOptions({ width: containerRef.current!.clientWidth })
    window.addEventListener('resize', handleResize)
    return () => { window.removeEventListener('resize', handleResize); chart.remove() }
  }, [])

  useEffect(() => {
    let mounted = true
    let timer: any
    const load = async () => {
      const ad = await getMarketAdapter()
      const cs = await ad.getCandles(symbol.ticker, symbol.exchange, tf)
      if (!mounted) return
      setCandles(cs)
      if (cs && cs.length) {
        const last = cs[cs.length-1].close
        markPrice(symbol.ticker, symbol.exchange, last)
      }
      timer = setTimeout(load, 10000)
    }
    load()
    return () => { mounted = false; if (timer) clearTimeout(timer) }
  }, [symbol, tf, markPrice])

  useEffect(() => {
    if (!candles || !seriesRef.current) return
    const data = candles.map((c) => ({ time: Math.floor(new Date(c.ts).getTime()/1000), open: c.open, high: c.high, low: c.low, close: c.close }))
    seriesRef.current.setData(data)
  }, [candles])

  return (
    <div className="grid grid-cols-3 gap-2">
      <div className="panel p-3">
        <div className="text-sm mb-2">Trade Panel</div>
        <div className="space-y-2 text-sm">
          <div>Symbol: {symbol.ticker}.{symbol.exchange==='NSE'?'NS':'BO'}</div>
          <div className="flex items-center gap-2">
            <select className="bg-[#0b0f15] border border-gray-800 rounded px-2 py-1" value={tf} onChange={e=>setTf(e.target.value as Timeframe)}>
              <option value="1m">1m</option>
              <option value="5m">5m</option>
              <option value="15m">15m</option>
              <option value="1h">1h</option>
              <option value="1d">1d</option>
            </select>
          </div>
          <button onClick={async () => { await placeOrder({ ticker: symbol.ticker, exchange: symbol.exchange, side: 'BUY', qty: 10 }) }} className="bg-green-600 px-3 py-2 rounded">Buy MKT</button>
          <button onClick={async () => { await placeOrder({ ticker: symbol.ticker, exchange: symbol.exchange, side: 'SELL', qty: 10 }) }} className="bg-red-600 px-3 py-2 rounded">Sell MKT</button>
        </div>
      </div>
      <div className="panel p-1 col-span-2">
        <div ref={containerRef} />
      </div>
      <Signals ticker={symbol.ticker} exchange={symbol.exchange as any} />
    </div>
  )
}


