"use client"

import useSWR from 'swr'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE
const fetcher = (url: string) => axios.get(url).then(r => r.data)

export default function Analytics() {
  const { data } = useSWR(`${API}/pnl/summary?range_days=90`, fetcher, { refreshInterval: 30000 })
  const equity = data?.equity || []
  return (
    <div className="panel p-3 mt-3">
      <div className="text-sm text-gray-400 mb-2">P&L Analytics</div>
      <div className="grid grid-cols-4 gap-3 text-sm">
        <div>Sharpe: {data? Number(data.sharpe).toFixed(2): '-'}</div>
        <div>Max DD: {data? Number(data.max_drawdown_pct).toFixed(1): '-'}%</div>
        <div>Return: {data? Number(data.return_pct).toFixed(1): '-'}%</div>
        <div>Equity: {data? Number(data.end_equity).toFixed(0): '-'}</div>
      </div>
      <Sparkline points={equity} />
    </div>
  )
}

function Sparkline({ points }: { points: { date: string, equity: number }[] }) {
  const width = 600
  const height = 120
  const pad = 8
  if (!points || points.length < 2) {
    return <div className="mt-3 h-32 bg-[#0b0f15] rounded border border-gray-800 p-2 text-xs text-gray-400">No equity data</div>
  }
  const vals = points.map(p => p.equity)
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const x = (i: number) => pad + (i / (points.length - 1)) * (width - pad*2)
  const y = (v: number) => pad + (1 - (v - min) / (max - min || 1)) * (height - pad*2)
  const d = points.map((p, i) => `${i===0? 'M':'L'} ${x(i)} ${y(p.equity)}`).join(' ')
  return (
    <div className="mt-3 bg-[#0b0f15] rounded border border-gray-800 p-2 text-xs text-gray-400">
      <div className="mb-1">Equity curve (last {points.length} days)</div>
      <svg width={width} height={height}>
        <rect x="0" y="0" width={width} height={height} fill="#0b0f15" />
        <path d={d} fill="none" stroke="#10b981" strokeWidth="2" />
      </svg>
    </div>
  )
}


