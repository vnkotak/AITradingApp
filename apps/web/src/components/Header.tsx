"use client"

import { useEffect, useState } from 'react'
import axios from 'axios'
import PauseToggle from './PauseToggle'

const API = process.env.NEXT_PUBLIC_API_BASE

export default function Header() {
  const [apiStatus, setApiStatus] = useState<boolean | null>(null)
  const [dbStatus, setDbStatus] = useState<boolean | null>(null)
  const [marketStatus, setMarketStatus] = useState<string>('CLOSED')
  const [refreshRate, setRefreshRate] = useState<string>('OFF')

  useEffect(() => {
    let mounted = true

    const pingAPI = async () => {
      try {
        const res = await axios.get(`${API}/health`)
        if (!mounted) return
        setApiStatus(res.data?.status === 'ok')
      } catch {
        if (!mounted) return
        setApiStatus(false)
      }
    }

    const fetchSystemStatus = async () => {
      if (!API) return
      try {
        const response = await axios.get(`${API}/home/system-status`)
        if (!mounted) return
        const status = response.data
        setDbStatus(status.database_status === 'Connected')
        setMarketStatus(status.market_status || 'CLOSED')
        setRefreshRate(status.market_status === 'CLOSED' ? 'OFF' : status.refresh_rate || '10s')
      } catch (error) {
        console.error('Failed to fetch system status:', error)
        setDbStatus(false)
        setRefreshRate('OFF')
      }
    }

    // Initial calls
    pingAPI()
    fetchSystemStatus()

    // Set up intervals
    const apiInterval = setInterval(pingAPI, 15000)
    const statusInterval = setInterval(fetchSystemStatus, 30000)

    return () => {
      mounted = false
      clearInterval(apiInterval)
      clearInterval(statusInterval)
    }
  }, [])

  const getStatusColor = (status: boolean | null) => {
    if (status === null) return 'bg-gray-500 animate-pulse'
    return status ? 'bg-green-400 animate-pulse' : 'bg-red-400'
  }

  const getRefreshStatusColor = () => {
    if (marketStatus === 'CLOSED') return 'bg-gray-500'
    return 'bg-purple-400 animate-pulse'
  }

  return (
    <div className="w-full flex items-center justify-between gap-2">
      {/* Logo and Title - Mobile Responsive */}
      <div className="flex items-center gap-2 sm:gap-4 min-w-0 flex-1">
        <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
          <div className="w-8 h-8 sm:w-10 sm:h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
            <span className="text-white font-bold text-sm sm:text-lg">AI</span>
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-lg sm:text-xl font-bold text-white truncate">AI Trading App</h1>
            <p className="text-xs text-gray-400 truncate hidden sm:block">Advanced Paper Trading Platform</p>
          </div>
        </div>
      </div>

      {/* System Status - Mobile Responsive */}
      <div className="flex items-center gap-1 sm:gap-3 flex-shrink-0">
        {/* Mobile: Compact Status Indicators */}
        <div className="hidden sm:flex items-center gap-3 md:gap-6">
          {/* API Status */}
          <div className="flex items-center gap-1 sm:gap-2">
            <div className={`w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full ${getStatusColor(apiStatus)}`}></div>
            <div className="text-xs sm:text-sm">
              <span className="text-gray-400">API:</span>
              <span className={`ml-1 font-medium ${apiStatus ? 'text-green-400' : apiStatus === false ? 'text-red-400' : 'text-gray-500'}`}>
                {apiStatus === null ? '...' : apiStatus ? 'OK' : 'ERR'}
              </span>
            </div>
          </div>

          {/* Database Status */}
          <div className="flex items-center gap-1 sm:gap-2">
            <div className={`w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full ${getStatusColor(dbStatus)}`}></div>
            <div className="text-xs sm:text-sm">
              <span className="text-gray-400">DB:</span>
              <span className={`ml-1 font-medium ${dbStatus ? 'text-blue-400' : dbStatus === false ? 'text-red-400' : 'text-gray-500'}`}>
                {dbStatus === null ? '...' : dbStatus ? 'OK' : 'ERR'}
              </span>
            </div>
          </div>

          {/* Market Status & Refresh */}
          <div className="flex items-center gap-1 sm:gap-2">
            <div className={`w-2 h-2 sm:w-2.5 sm:h-2.5 rounded-full ${getRefreshStatusColor()}`}></div>
            <div className="text-xs sm:text-sm">
              <span className="text-gray-400">Market:</span>
              <span className={`ml-1 font-medium ${marketStatus === 'CLOSED' ? 'text-gray-500' : 'text-purple-400'}`}>
                {marketStatus === 'CLOSED' ? 'Closed' : 'Open'}
              </span>
              <span className="text-gray-500 ml-1 sm:ml-2">•</span>
              <span className="text-gray-400 ml-1">Refresh:</span>
              <span className={`ml-1 font-medium ${marketStatus === 'CLOSED' ? 'text-gray-600' : 'text-purple-400'}`}>
                {refreshRate}
              </span>
            </div>
          </div>
        </div>

        {/* Mobile: Collapsed Status Indicators */}
        <div className="flex sm:hidden items-center gap-1">
          <div className={`w-2 h-2 rounded-full ${getStatusColor(apiStatus)}`} title="API Status"></div>
          <div className={`w-2 h-2 rounded-full ${getStatusColor(dbStatus)}`} title="Database Status"></div>
          <div className={`w-2 h-2 rounded-full ${getRefreshStatusColor()}`} title="Market Status"></div>
        </div>

        {/* Pause Toggle */}
        <div className="flex-shrink-0">
          <PauseToggle />
        </div>
      </div>
    </div>
  )
}


