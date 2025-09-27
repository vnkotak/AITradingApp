"use client"

import { useEffect, useMemo, useState } from 'react'
import useSWR from 'swr'
import { getMarketAdapter, type SymbolInfo, type Candle } from '../lib/marketAdapter'

function Spark({ candles }: { candles: Candle[] }) {
  if (!candles || candles.length < 2) return <div className="h-8 bg-[#0b0f15] rounded" />
  const width = 120, height = 32, pad = 4
  const vals = candles.map(c => c.close)
  const min = Math.min(...vals), max = Math.max(...vals)
  const x = (i: number) => pad + (i/(candles.length-1)) * (width - pad*2)
  const y = (v: number) => pad + (1 - (v - min)/(max - min || 1)) * (height - pad*2)
  const d = candles.map((c, i) => `${i===0? 'M':'L'} ${x(i)} ${y(c.close)}`).join(' ')
  const up = candles[candles.length-1].close >= candles[0].close
  return (
    <svg width={width} height={height}>
      <path d={d} fill="none" stroke={up? '#10b981':'#ef4444'} strokeWidth="2" />
    </svg>
  )
}

export default function Markets() {
  const [adapter, setAdapter] = useState<any>(null)
  const [query, setQuery] = useState('')
  const [symbols, setSymbols] = useState<SymbolInfo[]>([])
  const [overview, setOverview] = useState<any>(null)

  useEffect(() => { getMarketAdapter().then(setAdapter) }, [])
  useEffect(() => {
    if (!adapter) return
    let mounted = true
    const load = async () => {
      try {
        const [syms, ov] = await Promise.all([adapter.getSymbols(), adapter.getOverview()])
        if (!mounted) return
        setSymbols(syms)
        setOverview(ov)
      } catch {}
    }
    load()
  }, [adapter])

  const filtered = useMemo(() => symbols.filter(s => s.ticker.includes(query.toUpperCase())), [symbols, query])

  return (
    <div className="binance-grid">
      <div className="panel p-3 col-span-3">
        <div className="flex items-center justify-between">
          <div className="text-sm">
            <span className="text-gray-400 mr-2">Market</span>
            <span className={`font-medium ${overview?.direction==='BULLISH'?'text-green-500': overview?.direction==='BEARISH'?'text-red-500':'text-gray-300'}`}>{overview?.direction||'...'}</span>
            <span className="ml-4 text-gray-400">Avg %: {overview? overview.avgChangePct.toFixed(2): '...'}</span>
            <span className="ml-4 text-gray-400">A/D: {overview? `${overview.advanceDecline.advancers}/${overview.advanceDecline.decliners}`:'...'}</span>
          </div>
          <input className="bg-[#0b0f15] border border-gray-800 rounded px-2 py-1 text-sm" placeholder="Search ticker" value={query} onChange={e=>setQuery(e.target.value)} />
        </div>
      </div>
      <div className="panel p-3 col-span-3">
        <div className="grid grid-cols-3 gap-2">
          {filtered.map((s) => (
            <SymbolCard key={`${s.ticker}.${s.exchange}`} sym={s} />
          ))}
        </div>
      </div>
    </div>
  )
}

function SymbolCard({ sym }: { sym: SymbolInfo }) {
  const [data, setData] = useState<{ candles: Candle[], chg: number, last: number }>({ candles: [], chg: 0, last: 0 })
  useEffect(() => {
    let mounted = true
    let timer: any
    const run = async () => {
      try {
        // Try API first
        if (process.env.NEXT_PUBLIC_API_BASE) {
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/candles/ticker/${sym.ticker}?exchange=${sym.exchange}&tf=1d&limit=5`)
          if (res.ok) {
            const cs = await res.json()
            const last = cs[cs.length-1]?.close || 0
            const prev = cs[cs.length-2]?.close || last
            const chg = prev? ((last - prev)/prev)*100 : 0
            if (mounted) setData({ candles: cs.slice(-60), chg, last })
            timer = setTimeout(run, 10000)
            return
          }
        }
        // Fallback to mock
        const ad = await getMarketAdapter()
        const cs = await ad.getCandles(sym.ticker, sym.exchange, '1d')
        const last = cs[cs.length-1]?.close || 0
        const prev = cs[cs.length-2]?.close || last
        const chg = prev? ((last - prev)/prev)*100 : 0
        if (mounted) setData({ candles: cs.slice(-60), chg, last })
      } catch (e) {
        console.error('Failed to load data for', sym.ticker, e)
      }
      timer = setTimeout(run, 10000)
    }
    run()
    return () => { mounted = false; if (timer) clearTimeout(timer) }
  }, [sym.ticker, sym.exchange])
  return (
    <div className="bg-[#0b0f15] p-3 rounded border border-gray-800">
      <div className="flex items-center justify-between text-sm">
        <div className="font-medium">{sym.ticker}.{sym.exchange==='NSE'?'NS':'BO'}</div>
        <div className={data.chg>=0? 'text-green-500':'text-red-500'}>{data.chg.toFixed(2)}%</div>
      </div>
      <div className="text-xs text-gray-400">{sym.sector||''}</div>
      <div className="mt-2"><Spark candles={data.candles} /></div>
    </div>
  )
}

