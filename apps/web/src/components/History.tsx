"use client"

import useSWR from 'swr'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE
const fetcher = (url: string) => axios.get(url).then(r => r.data)

export default function History() {
  const { data: orders } = useSWR(`${API}/orders`, fetcher, { refreshInterval: 10000 })
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
              <td className="text-right">{o.price?.toFixed?.(2) || o.price}</td>
              <td className="text-right">{o.qty}</td>
              <td>{o.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


