"use client"

import { useEffect, useState } from 'react'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE

export default function Signals({ ticker = 'RELIANCE', exchange = 'NSE' }: { ticker?: string, exchange?: 'NSE' | 'BSE' }) {
  const [data, setData] = useState<any[]|null>(null)
  useEffect(() => {
    let mounted = true
    let id: any
    const run = async () => {
      if (API) {
        try {
          const res = await axios.get(`${API}/signals?ticker=${ticker}&exchange=${exchange}&limit=20`)
          if (mounted) setData(res.data || [])
        } catch {
          // fallback to mock
          const { getSignals } = await import('../lib/signals')
          const rows = await getSignals([{ ticker: ticker!, exchange: exchange! }])
          if (mounted) setData(rows)
        }
      } else {
        // fallback to mock
        const { getSignals } = await import('../lib/signals')
        const rows = await getSignals([{ ticker: ticker!, exchange: exchange! }])
        if (mounted) setData(rows)
      }
      id = setTimeout(run, 10000)
    }
    run()
    return () => { mounted = false; if (id) clearTimeout(id) }
  }, [ticker, exchange])
  return (
    <div className="panel p-3">
      <div className="text-sm text-gray-400 mb-2">Latest Signals</div>
      <div className="space-y-2 max-h-[400px] overflow-auto text-sm">
        {(data||[]).map((s: any, idx:number) => (
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
          </div>
        ))}
      </div>
    </div>
  )
}


