"use client"

import useSWR from 'swr'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE
const fetcher = (url: string) => axios.get(url).then(r => r.data)

export default function Portfolio() {
  const { data: positions } = useSWR(`${API}/positions`, fetcher, { refreshInterval: 10000 })
  return (
    <div className="panel p-3">
      <div className="text-sm text-gray-400 mb-2">Portfolio</div>
      <table className="w-full text-sm">
        <thead className="text-gray-400">
          <tr>
            <th className="text-left">Symbol</th>
            <th className="text-right">Qty</th>
            <th className="text-right">Avg Price</th>
            <th className="text-right">Realized P&L</th>
          </tr>
        </thead>
        <tbody>
          {(positions||[]).map((p:any) => (
            <tr key={p.ticker} className="border-t border-gray-800">
              <td>{p.ticker}.{p.exchange==='NSE'?'NS':'BO'}</td>
              <td className="text-right">{p.qty}</td>
              <td className="text-right">{Number(p.avg_price).toFixed(2)}</td>
              <td className={`text-right ${p.realized_pnl>=0?'text-green-500':'text-red-500'}`}>{Number(p.realized_pnl).toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


