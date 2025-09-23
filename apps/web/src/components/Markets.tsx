"use client"

import useSWR from 'swr'
import axios from 'axios'

const fetcher = (url: string) => axios.get(url).then(r => r.data)
const API = process.env.NEXT_PUBLIC_API_BASE

export default function Markets() {
  const { data: symbols } = useSWR(`${API}/symbols?active=true`, fetcher)
  return (
    <div className="binance-grid">
      <div className="panel p-3">
        <div className="text-sm text-gray-400 mb-2">Watchlist</div>
        <div className="space-y-2 max-h-[70vh] overflow-auto">
          {(symbols||[]).map((s:any) => (
            <div key={s.ticker} className="flex justify-between text-sm bg-[#0b0f15] p-2 rounded">
              <span>{s.ticker}.{s.exchange==='NSE'?'NS':'BO'}</span>
              <span className="text-gray-500">{s.sector||''}</span>
            </div>
          ))}
        </div>
      </div>
      <div className="panel p-3 col-span-1">
        <div className="text-sm text-gray-400">Gainers/Losers (placeholder)</div>
      </div>
      <div className="panel p-3">
        <div className="text-sm text-gray-400">Screener (placeholder)</div>
      </div>
      <div className="panel p-3 col-span-3">
        <div className="text-sm text-gray-400">Signals (latest) - connect to /signals (todo)</div>
      </div>
    </div>
  )
}


