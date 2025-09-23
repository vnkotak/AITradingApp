"use client"

import useSWR from 'swr'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE
const fetcher = (url: string) => axios.get(url).then(r => r.data)

export default function Signals({ ticker = 'RELIANCE', exchange = 'NSE' }: { ticker?: string, exchange?: 'NSE' | 'BSE' }) {
  const { data } = useSWR(`${API}/signals?ticker=${ticker}&exchange=${exchange}&limit=20`, fetcher, { refreshInterval: 10000 })
  return (
    <div className="panel p-3">
      <div className="text-sm text-gray-400 mb-2">Latest Signals</div>
      <div className="space-y-2 max-h-[400px] overflow-auto text-sm">
        {(data||[]).map((s:any, idx:number) => (
          <div key={idx} className="bg-[#0b0f15] p-2 rounded border border-gray-800">
            <div className="flex justify-between">
              <div>
                <span className={`font-medium ${s.action==='BUY'?'text-green-500':'text-red-500'}`}>{s.action}</span>
                <span className="ml-2 text-gray-400">{s.strategy}</span>
              </div>
              <div className="text-gray-400">{new Date(s.ts).toLocaleTimeString()}</div>
            </div>
            <div className="mt-1 grid grid-cols-4 gap-2">
              <div>Entry: {Number(s.entry).toFixed(2)}</div>
              <div>Stop: {Number(s.stop).toFixed(2)}</div>
              <div>Target: {s.target? Number(s.target).toFixed(2): '-'}</div>
              <div>Conf: {(s.confidence*100).toFixed(0)}%</div>
            </div>
            {s.rationale?.scoring && (
              <div className="mt-2 text-gray-400">
                <div className="text-xs">Why: base {s.rationale.scoring.base}, features rsi_bias {Number(s.rationale.scoring.features?.rsi_bias||0).toFixed(2)}, macd {Number(s.rationale.scoring.features?.macd_momentum||0).toFixed(2)}, vwap {Number(s.rationale.scoring.features?.vwap_premium_atr||0).toFixed(2)}</div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}


