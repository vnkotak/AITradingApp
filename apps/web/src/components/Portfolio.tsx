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
    <div className="panel p-3">
      <div className="text-sm text-gray-400 mb-2">Portfolio</div>
      <table className="w-full text-sm">
        <thead className="text-gray-400">
          <tr>
            <th className="text-left">Symbol</th>
            <th className="text-right">Qty</th>
            <th className="text-right">Avg Price</th>
            <th className="text-right">Last</th>
            <th className="text-right">Realized P&L</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p: any) => {
            const key = `${p.ticker}.${p.exchange}`
            const last = marks[key] ?? p.avgPrice
            const unreal = (last - p.avgPrice) * (p.qty > 0 ? Math.abs(p.qty) : -Math.abs(p.qty))
            return (
              <tr key={key} className="border-t border-gray-800">
                <td>{p.ticker}.{p.exchange==='NSE'?'NS':'BO'}</td>
                <td className="text-right">{p.qty}</td>
                <td className="text-right">{Number(p.avgPrice).toFixed(2)}</td>
                <td className="text-right">{Number(last).toFixed(2)}</td>
                <td className={`text-right ${unreal>=0?'text-green-500':'text-red-500'}`}>{unreal.toFixed(2)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}


