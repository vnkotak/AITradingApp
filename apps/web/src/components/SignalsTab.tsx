"use client"

import { useEffect, useState } from 'react'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE

export default function SignalsTab() {
  const [ticker, setTicker] = useState('')
  const [exchange, setExchange] = useState<'NSE'|'BSE'>('NSE')
  const [tf, setTf] = useState('1m')
  const [data, setData] = useState<any[]|null>(null)
  const [scanning, setScanning] = useState(false)
  
  // Debounce ticker input
  const [debouncedTicker, setDebouncedTicker] = useState(ticker)
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedTicker(ticker), 500)
    return () => clearTimeout(handler)
  }, [ticker])

  useEffect(() => {
    let mounted = true
    let id: any
    const run = async () => {
      if (API && debouncedTicker) {
        try {
          const res = await axios.get(`${API}/signals?ticker=${debouncedTicker}&exchange=${exchange}&tf=${tf}&limit=100`)
          if (mounted) setData(res.data || [])
        } catch {
          // fallback to mock
          const { getSignals } = await import('../lib/signals')
          const rows = await getSignals([{ ticker: debouncedTicker, exchange }])
          if (mounted) setData(rows)
        }
      } else if (API && !debouncedTicker) {
        setData([])
      } else {
        // fallback to mock
        if (debouncedTicker) {
          const { getSignals } = await import('../lib/signals')
          const rows = await getSignals([{ ticker: debouncedTicker, exchange }])
          if (mounted) setData(rows)
        } else {
          setData([])
        }
      }
      id = setTimeout(run, 10000)
    }
    run()
    return () => { mounted = false; if (id) clearTimeout(id) }
  }, [debouncedTicker, exchange, tf])

  const runScan = async () => {
    if (!API) return
    setScanning(true)
    try {
      await axios.post(`${API}/scanner/run?mode=${tf}&force=true`)
      // refresh signals after scan
      setTimeout(() => {
        const run = async () => {
          const res = await axios.get(`${API}/signals?ticker=${ticker}&exchange=${exchange}&tf=${tf}&limit=100`)
          setData(res.data || [])
        }
        run()
      }, 2000)
    } catch (e) {
      console.error('Scan failed:', e)
    } finally {
      setScanning(false)
    }
  }
  return (
    <div className="panel p-3">
      <div className="flex items-center gap-2 mb-3 text-sm">
        <input className="bg-[#0b0f15] border border-gray-800 rounded px-2 py-1" value={ticker} placeholder="Type symbol (e.g. TCS)" onChange={e=>setTicker(e.target.value.toUpperCase())} />
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
        {API && (
          <button onClick={runScan} disabled={scanning} className="bg-blue-600 px-3 py-1 rounded text-sm">
            {scanning ? 'Scanning...' : 'Scan Now'}
          </button>
        )}
      </div>
      <div className="space-y-2 max-h-[70vh] overflow-auto text-sm">
        {(data||[]).length === 0 && <div className="text-gray-500">No signals found.</div>}
        {(data||[]).map((s:any, i:number) => (
          <div key={i} className="bg-[#0b0f15] p-2 rounded border border-gray-800">
            <div className="flex justify-between">
              <div>
                <span className="font-bold text-blue-400">{s.ticker || '-'}</span>
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
            {/* Warn if entry is suspiciously low for NIFTY stocks */}
            {Number(s.entry) < 100 && <div className="text-xs text-yellow-400 mt-1">Warning: Entry price seems too low for this symbol. Check data source.</div>}
          </div>
        ))}
      </div>
    </div>
  )
}


