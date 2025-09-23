"use client"

import { useEffect, useRef, useState } from 'react'
import { createChart, ISeriesApi } from 'lightweight-charts'
import Signals from './Signals'
import useSWR from 'swr'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE
const fetcher = (url: string) => axios.get(url).then(r => r.data)

export default function Trading() {
  const [symbol, setSymbol] = useState({ ticker: 'RELIANCE', exchange: 'NSE' })
  const { data: candles } = useSWR(`${API}/candles/${symbol.ticker}?exchange=${symbol.exchange}&tf=1m&limit=500`, fetcher)
  const containerRef = useRef<HTMLDivElement>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

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
    if (!candles || !seriesRef.current) return
    const data = candles.map((c:any) => ({ time: Math.floor(new Date(c.ts).getTime()/1000), open: c.open, high: c.high, low: c.low, close: c.close }))
    seriesRef.current.setData(data)
  }, [candles])

  return (
    <div className="grid grid-cols-3 gap-2">
      <div className="panel p-3">
        <div className="text-sm mb-2">Trade Panel</div>
        <div className="space-y-2 text-sm">
          <div>Symbol: {symbol.ticker}.{symbol.exchange==='NSE'?'NS':'BO'}</div>
          <button onClick={async () => { await axios.post(`${API}/orders`, { ticker: symbol.ticker, exchange: symbol.exchange, side: 'BUY', type: 'MARKET', qty: 10 }) }} className="bg-green-600 px-3 py-2 rounded">Buy MKT</button>
          <button onClick={async () => { await axios.post(`${API}/orders`, { ticker: symbol.ticker, exchange: symbol.exchange, side: 'SELL', type: 'MARKET', qty: 10 }) }} className="bg-red-600 px-3 py-2 rounded">Sell MKT</button>
        </div>
      </div>
      <div className="panel p-1 col-span-2">
        <div ref={containerRef} />
      </div>
      <Signals ticker={symbol.ticker} exchange={symbol.exchange as any} />
    </div>
  )
}


