"use client"

import { useEffect, useMemo, useState } from 'react'
import { useTradingStore } from '../store/trading'
import { getMarketAdapter } from '../lib/marketAdapter'

export default function Portfolio() {
  const positions = useTradingStore(s => s.positions)
  const [marks, setMarks] = useState<Record<string, number>>({})

  useEffect(() => {
    let mounted = true
    let timer: any
    const load = async () => {
      const ad = await getMarketAdapter()
      const kv: Record<string, number> = {}
      for (const key of Object.keys(positions)) {
        const p = positions[key]
        kv[key] = await ad.getLastPrice(p.ticker, p.exchange)
      }
      if (mounted) setMarks(kv)
      timer = setTimeout(load, 10000)
    }
    load()
    return () => { mounted = false; if (timer) clearTimeout(timer) }
  }, [positions])

  const rows = useMemo(() => Object.values(positions), [positions])

  return (
     <div className="min-h-screen bg-gradient-to-br from-slate-900 via-green-900 to-emerald-900 p-3 sm:p-6">
       <div className="max-w-7xl mx-auto">
         <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/30">
           <div className="flex items-center gap-2 mb-4 sm:mb-6">
             <div className="w-2 h-6 sm:h-8 bg-green-500 rounded-full"></div>
             <h2 className="text-lg sm:text-2xl font-bold text-white">Portfolio Positions</h2>
           </div>

          {rows.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">📊</div>
              <div className="text-xl text-gray-300 mb-2">No Active Positions</div>
              <div className="text-sm text-gray-400">Your portfolio is currently empty</div>
            </div>
          ) : (
            <div className="space-y-4">
              {rows.map((p: any, index: number) => {
                const key = `${p.ticker}.${p.exchange}`
                const last = marks[key] ?? p.avgPrice
                const unreal = (last - p.avgPrice) * (p.qty > 0 ? Math.abs(p.qty) : -Math.abs(p.qty))
                const percentChange = p.avgPrice !== 0 ? ((last - p.avgPrice) / p.avgPrice) * 100 : 0

                return (
                  <div
                    key={key}
                    className="bg-white/5 rounded-lg sm:rounded-xl p-3 sm:p-6 border border-white/10 hover:border-white/20 transition-all duration-300 hover:scale-[1.02]"
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-3 sm:mb-4 gap-3 sm:gap-0">
                      <div className="flex items-center gap-3 sm:gap-4">
                        <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg sm:rounded-xl flex items-center justify-center flex-shrink-0">
                          <span className="text-white font-bold text-sm sm:text-base">{p.ticker.slice(0, 2)}</span>
                        </div>
                        <div className="min-w-0">
                          <div className="text-lg sm:text-xl font-bold text-white truncate">{p.ticker}</div>
                          <div className="text-xs sm:text-sm text-gray-400 truncate">{p.exchange === 'NSE' ? 'National Stock Exchange' : 'Bombay Stock Exchange'}</div>
                        </div>
                      </div>
                      <div className="text-center sm:text-right">
                        <div className={`text-xl sm:text-2xl font-bold ${unreal >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          ₹{unreal.toFixed(2)}
                        </div>
                        <div className={`text-xs sm:text-sm ${unreal >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {percentChange >= 0 ? '+' : ''}{percentChange.toFixed(2)}%
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3 md:gap-4">
                      <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                        <div className="text-xs text-gray-400 mb-1">Quantity</div>
                        <div className="text-sm sm:text-lg font-semibold text-white">{p.qty}</div>
                      </div>
                      <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                        <div className="text-xs text-gray-400 mb-1">Avg Price</div>
                        <div className="text-sm sm:text-lg font-semibold text-blue-400">₹{Number(p.avgPrice).toFixed(2)}</div>
                      </div>
                      <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                        <div className="text-xs text-gray-400 mb-1">Current Price</div>
                        <div className="text-sm sm:text-lg font-semibold text-purple-400">₹{Number(last).toFixed(2)}</div>
                      </div>
                      <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                        <div className="text-xs text-gray-400 mb-1">Position Value</div>
                        <div className="text-sm sm:text-lg font-semibold text-white">₹{(Math.abs(p.qty) * last).toFixed(2)}</div>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


