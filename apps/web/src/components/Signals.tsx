"use client"

import { useEffect, useState } from 'react'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE

export default function Signals({ ticker = 'RELIANCE', exchange = 'NSE', isVisible = true }: { ticker?: string, exchange?: 'NSE' | 'BSE', isVisible?: boolean }) {
  const [data, setData] = useState<any[]|null>(null)
  useEffect(() => {
    // Only run if component is visible
    if (!isVisible) return

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

      // Only schedule next run if still visible and mounted
      if (mounted && isVisible) {
        id = setTimeout(run, 10000)
      }
    }

    run()
    return () => { mounted = false; if (id) clearTimeout(id) }
  }, [ticker, exchange, isVisible])
  return (
    <div className="panel p-2 sm:p-3">
      <div className="text-xs sm:text-sm text-gray-400 mb-2">Latest Signals</div>
      <div className="space-y-2 max-h-[400px] overflow-auto">
        {(data||[]).map((s: any, idx:number) => (
          <div key={idx} className="bg-[#0b0f15] p-2 sm:p-3 rounded border border-gray-800">
            {/* Mobile-first: Stack everything vertically on mobile */}
            <div className="space-y-2">
              {/* Header row */}
              <div className="flex justify-between items-start">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <span className={`font-medium text-sm ${s.action==='BUY'?'text-green-500':'text-red-500'}`}>
                    {s.action}
                  </span>
                  <span className="text-gray-400 text-xs truncate max-w-[100px] sm:max-w-none">
                    {s.strategy}
                  </span>
                </div>
                <div className="text-gray-400 text-xs whitespace-nowrap ml-2">
                  {new Date(s.ts).toLocaleTimeString('en-IN', {
                    hour: '2-digit',
                    minute: '2-digit',
                    hour12: false
                  })}
                </div>
              </div>

              {/* Mobile-first: Single column on mobile, two columns on larger screens */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                {/* Left column */}
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Entry:</span>
                    <span className="font-mono text-white">{Number(s.entry).toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Stop:</span>
                    <span className="font-mono text-white">{Number(s.stop).toFixed(2)}</span>
                  </div>
                </div>

                {/* Right column */}
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Target:</span>
                    <span className="font-mono text-white">{s.target ? Number(s.target).toFixed(2) : '-'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Conf:</span>
                    <span className="font-mono text-white">{(s.confidence*100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}


