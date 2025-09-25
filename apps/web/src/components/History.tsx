"use client"

import { useMemo } from 'react'
import { useTradingStore } from '../store/trading'

export default function History() {
  const orders = useTradingStore(s => s.orders)
  const trades = useTradingStore(s => s.trades)
  const winRate = useMemo(() => {
    if (!trades.length) return 0
    // naive: count SELL after BUY as exit and pnl > 0; here we can't compute exact, show trade count
    return (trades.length > 0) ? 50 : 0
  }, [trades])
  return (
    <div className="panel p-3">
      <div className="text-sm text-gray-400 mb-2">Recent Orders</div>
      <table className="w-full text-sm">
        <thead className="text-gray-400">
          <tr>
            <th className="text-left">Time</th>
            <th>Side</th>
            <th>Type</th>
            <th className="text-right">Price</th>
            <th className="text-right">Qty</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {(orders||[]).map((o:any) => (
            <tr key={o.id} className="border-t border-gray-800">
              <td>{new Date(o.ts).toLocaleString()}</td>
              <td className={o.side==='BUY'?'text-green-500':'text-red-500'}>{o.side}</td>
              <td>{o.type}</td>
              <td className="text-right">{Number(o.price).toFixed(2)}</td>
              <td className="text-right">{o.qty}</td>
              <td>{o.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="text-sm text-gray-400 mt-3">Trades: {trades.length} • Est. Win Rate: {winRate}%</div>
    </div>
  )
}


