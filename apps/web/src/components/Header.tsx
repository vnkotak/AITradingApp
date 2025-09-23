"use client"

import { useEffect, useState } from 'react'
import axios from 'axios'
import PauseToggle from './PauseToggle'

const API = process.env.NEXT_PUBLIC_API_BASE

export default function Header() {
  const [healthy, setHealthy] = useState<boolean | null>(null)

  useEffect(() => {
    let mounted = true
    const ping = async () => {
      try {
        const res = await axios.get(`${API}/health`)
        if (!mounted) return
        setHealthy(res.data?.status === 'ok')
      } catch {
        if (!mounted) return
        setHealthy(false)
      }
    }
    ping()
    const id = setInterval(ping, 15000)
    return () => { mounted = false; clearInterval(id) }
  }, [])

  return (
    <div className="w-full flex items-center justify-between px-4 h-12 bg-surface border-b border-gray-800 rounded-md mb-3">
      <div className="flex items-center gap-2 text-sm">
        <span className="font-semibold">AITradingApp</span>
        <span className="text-gray-500">Paper Trading</span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <span className={`inline-block w-2.5 h-2.5 rounded-full ${healthy===null? 'bg-gray-500 animate-pulse' : healthy? 'bg-green-500' : 'bg-red-500'}`}></span>
          <span>{healthy===null? 'Checking...' : healthy? 'API Online' : 'API Down'}</span>
        </div>
        <PauseToggle />
      </div>
    </div>
  )
}


