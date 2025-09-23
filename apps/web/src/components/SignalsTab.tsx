"use client"

import { useState } from 'react'
import useSWR from 'swr'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE
const fetcher = (url: string) => axios.get(url).then(r => r.data)

export default function SignalsTab() {
  const [ticker, setTicker] = useState('RELIANCE')
  const [exchange, setExchange] = useState<'NSE'|'BSE'>('NSE')
  const [tf, setTf] = useState('1m')
  const { data } = useSWR(`${API}/signals?ticker=${ticker}&exchange=${exchange}&tf=${tf}&limit=100`, fetcher, { refreshInterval: 10000 })
  return (
    <div className="panel p-3">
      <div className="flex items-center gap-2 mb-3 text-sm">
        <input className="bg-[#0b0f15] border border-gray-800 rounded px-2 py-1" value={ticker} onChange={e=>setTicker(e.target.value.toUpperCase())} />
        <select className="bg-[#0b0f15] border border-gray-800 rounded px-2 py-1" value={exchange} onChange={e=>setExchange(e.target.value as any)}>
          <option value="NSE">NSE</option>
          <option value="BSE">BSE</option>
        </select>
        <select className="bg-[#0b0f15] border border-gray-800 rounded px-2 py-1" value={tf} onChange={e=>setTf(e.target.value)}>
          <option value="1m">1m</option>
          <option value="5m">5m</option>
          <option value="15m">15m</option>
          <option value="1h">1h</option>
          <option value="1d">1d</option>
        </select>
      </div>
      <div className="space-y-2 max-h-[70vh] overflow-auto text-sm">
        {(data||[]).map((s:any, i:number) => (
          <div key={i} className="bg-[#0b0f15] p-2 rounded border border-gray-800">
            <div className="flex justify-between">
              <div>
                <span className={`font-medium ${s.action==='BUY'?'text-green-500':'text-red-500'}`}>{s.action}</span>
                <span className="ml-2 text-gray-400">{s.strategy}</span>
              </div>
              <div className="text-gray-400">{new Date(s.ts).toLocaleString()}</div>
            </div>
            <div className="mt-1 grid grid-cols-4 gap-2">
              <div>Entry: {Number(s.entry).toFixed(2)}</div>
              <div>Stop: {Number(s.stop).toFixed(2)}</div>
              <div>Target: {s.target? Number(s.target).toFixed(2): '-'}</div>
              <div>Conf: {(s.confidence*100).toFixed(0)}%</div>
            </div>
            {s.rationale?.scoring && (
              <div className="mt-2 text-gray-400 text-xs">
                <div>rsi_bias {Number(s.rationale.scoring.features?.rsi_bias||0).toFixed(2)} | macd {Number(s.rationale.scoring.features?.macd_momentum||0).toFixed(2)} | vwap {Number(s.rationale.scoring.features?.vwap_premium_atr||0).toFixed(2)}</div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}


