"use client"

import { useEffect, useState } from 'react'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE

export default function SignalsTab({ isVisible = true }: { isVisible?: boolean }) {
  const [ticker, setTicker] = useState('')
  const [exchange, setExchange] = useState<'NSE' | 'BSE'>('NSE')
  const [tf, setTf] = useState('1m')
  const [data, setData] = useState<any[] | null>(null)
  const [previousData, setPreviousData] = useState<any[] | null>(null)
  const [scanning, setScanning] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [isBackgroundUpdating, setIsBackgroundUpdating] = useState(false)
  const [newSignalsCount, setNewSignalsCount] = useState(0)
  const [dbConfigured, setDbConfigured] = useState(true)

  // Debounce ticker input
  const [debouncedTicker, setDebouncedTicker] = useState(ticker)
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedTicker(ticker), 500)
    return () => clearTimeout(handler)
  }, [ticker])

  // Smart signal comparison - only update if data actually changed
  const hasSignalsChanged = (oldData: any[] | null, newData: any[] | null): boolean => {
    if (!oldData && !newData) return false
    if (!oldData || !newData) return true
    if (oldData.length !== newData.length) return true

    // Compare key signal properties
    return oldData.some((oldSignal, index) => {
      const newSignal = newData[index]
      return (
        oldSignal.ticker !== newSignal.ticker ||
        oldSignal.action !== newSignal.action ||
        oldSignal.confidence !== newSignal.confidence ||
        oldSignal.entry !== newSignal.entry
      )
    })
  }

  // Smooth background update function
  const updateSignalsInBackground = async () => {
    if (!API) return

    try {
      setIsBackgroundUpdating(true)
      let url = `${API}/signals?exchange=${exchange}&tf=${tf}&limit=100`
      if (debouncedTicker) {
        url += `&ticker=${debouncedTicker}`
      }

      const res = await axios.get(url)
      const newSignals = res.data || []

      // Only update if data actually changed
      if (hasSignalsChanged(data, newSignals)) {
        setPreviousData(data)
        setData(newSignals)
        setNewSignalsCount(newSignals.length)
        setLastUpdate(new Date())

        // Reset new signals count after animation
        setTimeout(() => setNewSignalsCount(0), 3000)
      }
    } catch (error) {
      console.warn('Background update failed:', error)
    } finally {
      setIsBackgroundUpdating(false)
    }
  }

  // Initial load effect - only when visible
  useEffect(() => {
    if (!isVisible) return

    let mounted = true

    const loadInitialData = async () => {
      try {
        setLoading(true)
        setError(null)

        if (API) {
          try {
            let url = `${API}/signals?exchange=${exchange}&tf=${tf}&limit=100`
            if (debouncedTicker) {
              url += `&ticker=${debouncedTicker}`
            }

            const res = await axios.get(url)
            if (mounted) {
              setData(res.data || [])
              setLastUpdate(new Date())
            }
          } catch (apiError) {
            console.warn('API signals failed, using mock data:', apiError)
            const { getSignals } = await import('../lib/signals')
            const rows = await getSignals(
              debouncedTicker ? [{ ticker: debouncedTicker, exchange }] : []
            )
            if (mounted) {
              setData(rows)
              setLastUpdate(new Date())
            }
          }
        } else {
          const { getSignals } = await import('../lib/signals')
          const rows = await getSignals(
            debouncedTicker ? [{ ticker: debouncedTicker, exchange }] : []
          )
          if (mounted) {
            setData(rows)
            setLastUpdate(new Date())
          }
        }
      } catch (err: any) {
        console.error('Failed to load signals:', err)
        if (err.message.includes('Database not configured')) {
          setDbConfigured(false)
          setError('Database not configured. Please set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables.')
        } else if (err.message.includes('API server not available')) {
          setError('API server not running. Please start the FastAPI server on port 8000.')
        } else {
          setError(err.message || 'Failed to load signals.')
        }
        if (mounted) setData([])
      } finally {
        if (mounted) setLoading(false)
      }
    }

    loadInitialData()
    return () => { mounted = false }
  }, [debouncedTicker, exchange, tf, isVisible])

  // Background update effect - only when visible!
  useEffect(() => {
    if (!data || loading || !isVisible) return

    const interval = setInterval(() => {
      if (isVisible) { // Double-check visibility
        updateSignalsInBackground()
      }
    }, 60000) // Once per minute for signals updates

    return () => clearInterval(interval)
  }, [data, debouncedTicker, exchange, tf, isVisible])

  const runScan = async () => {
    if (!API) {
      setError('API not configured')
      return
    }
    setScanning(true)
    setError(null)
    try {
      await axios.post(`${API}/scanner/run?mode=${tf}&force=true`)
      // refresh signals after scan
      setTimeout(async () => {
        try {
          let url = `${API}/signals?exchange=${exchange}&tf=${tf}&limit=100`
          if (ticker) {
            url += `&ticker=${ticker}`
          }
          const res = await axios.get(url)
          setData(res.data || [])
        } catch (refreshError) {
          console.error('Failed to refresh signals after scan:', refreshError)
          setError('Scan completed but failed to refresh signals')
        }
      }, 2000)
    } catch (e) {
      console.error('Scan failed:', e)
      setError('Scan failed. Please check API connection.')
    } finally {
      setScanning(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-indigo-900 p-4 sm:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header with controls */}
        <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-4 sm:p-6 border border-slate-700/30 mb-4 sm:mb-6">
          <div className="flex items-center gap-2 mb-4 sm:mb-6">
            <div className="w-2 h-8 bg-purple-500 rounded-full"></div>
            <h2 className="text-xl sm:text-2xl font-bold text-white">AI Trading Signals</h2>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            {/* Controls */}
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="bg-white/5 rounded-xl p-3 sm:p-4 border border-white/10">
                  <label className="block text-sm text-gray-300 mb-2">Symbol</label>
                  <input
                    className="w-full bg-slate-900/50 border border-slate-600 rounded-lg px-3 py-2 text-white placeholder-gray-400 focus:border-purple-500 focus:outline-none text-sm sm:text-base"
                    value={ticker}
                    placeholder="e.g. TCS, RELIANCE"
                    onChange={e => setTicker(e.target.value.toUpperCase())}
                  />
                </div>

                <div className="bg-white/5 rounded-xl p-3 sm:p-4 border border-white/10">
                  <label className="block text-sm text-gray-300 mb-2">Exchange</label>
                  <select
                    className="w-full bg-slate-900/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:border-purple-500 focus:outline-none text-sm sm:text-base"
                    value={exchange}
                    onChange={e => setExchange(e.target.value as any)}
                  >
                    <option value="NSE">NSE</option>
                    <option value="BSE">BSE</option>
                  </select>
                </div>

                <div className="bg-white/5 rounded-xl p-3 sm:p-4 border border-white/10 sm:col-span-2 lg:col-span-1">
                  <label className="block text-sm text-gray-300 mb-2">Timeframe</label>
                  <select
                    className="w-full bg-slate-900/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:border-purple-500 focus:outline-none text-sm sm:text-base"
                    value={tf}
                    onChange={e => setTf(e.target.value)}
                  >
                    <option value="1m">1 Minute</option>
                    <option value="5m">5 Minutes</option>
                    <option value="15m">15 Minutes</option>
                    <option value="1h">1 Hour</option>
                    <option value="1d">1 Day</option>
                  </select>
                </div>
              </div>

              {API && (
                <button
                  onClick={runScan}
                  disabled={scanning}
                  className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 px-6 py-3 rounded-lg text-white font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-blue-500/25 disabled:opacity-50 disabled:hover:scale-100"
                >
                  {scanning ? (
                    <div className="flex items-center gap-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Scanning Markets...
                    </div>
                  ) : (
                    '🚀 Scan for Signals'
                  )}
                </button>
              )}
            </div>

            {/* Live Status */}
            <div className="bg-white/5 rounded-xl p-3 sm:p-4 border border-white/10">
              <div className="flex items-center justify-between mb-3 sm:mb-4">
                <h3 className="text-base sm:text-lg font-semibold text-white">Live Status</h3>
                <div className="flex items-center gap-2">
                  {isBackgroundUpdating && (
                    <div className="flex items-center gap-2 text-blue-400">
                      <div className="w-2 h-2 bg-blue-400 rounded-full live-indicator"></div>
                      <span className="text-xs sm:text-sm">Live Updates</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-2 sm:space-y-3 text-xs sm:text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-300">Last Update:</span>
                  <span className="text-white">
                    {lastUpdate ? lastUpdate.toLocaleTimeString() : 'Never'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Total Signals:</span>
                  <span className="text-purple-400">{data?.length || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-300">Exchange:</span>
                  <span className="text-blue-400">{exchange}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Error display */}
        {error && (
          <div className="mb-4 sm:mb-6">
            <div className="bg-red-900/20 border border-red-800/50 rounded-2xl p-4 sm:p-6 text-red-400">
              <div className="flex items-center gap-2 mb-3 sm:mb-4">
                <div className="w-2 h-6 bg-red-500 rounded-full"></div>
                <span className="text-base sm:text-lg font-semibold">Configuration Error</span>
              </div>
              <div className="text-sm mb-3 sm:mb-4">{error}</div>
              {!dbConfigured && (
                <div className="bg-slate-800/50 rounded-xl p-3 sm:p-4 border border-slate-700/50">
                  <div className="text-sm font-medium mb-3 text-gray-200">To fix this, configure your database:</div>
                  <div className="text-xs space-y-2 text-gray-300">
                    <div className="flex items-center gap-2">
                      <span className="text-blue-400">1.</span>
                      <span>Set up a Supabase project at <a href="https://supabase.com" className="text-blue-400 hover:underline">supabase.com</a></span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-blue-400">2.</span>
                      <span>Update <code className="bg-gray-700 px-1 rounded text-gray-300">apps/api/.env</code>:</span>
                    </div>
                    <div className="bg-gray-900 p-3 rounded text-xs font-mono mt-2 text-gray-300">
                      SUPABASE_URL=https://your-project.supabase.co<br/>
                      SUPABASE_SERVICE_KEY=your-service-key-here
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-blue-400">3.</span>
                      <span>Run database migrations to create tables</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-blue-400">4.</span>
                      <span>Refresh this page</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Signals display with smooth animations */}
        <div className="space-y-3 sm:space-y-4 max-h-[calc(100vh-50px)] overflow-auto">
          {loading ? (
            // Beautiful skeleton loading with shimmer effect
            <div className="space-y-3 sm:space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-4 sm:p-6 border border-slate-700/30">
                  <div className="skeleton-shimmer">
                    <div className="flex justify-between mb-3 sm:mb-4">
                      <div className="h-4 sm:h-5 bg-slate-700 rounded w-24 sm:w-32"></div>
                      <div className="h-3 sm:h-4 bg-slate-700 rounded w-16 sm:w-20"></div>
                    </div>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-3 sm:mb-4">
                      <div className="h-3 sm:h-4 bg-slate-700 rounded w-20 sm:w-24"></div>
                      <div className="h-3 sm:h-4 bg-slate-700 rounded w-20 sm:w-24"></div>
                      <div className="h-3 sm:h-4 bg-slate-700 rounded w-20 sm:w-24"></div>
                    </div>
                    <div className="flex justify-between">
                      <div className="h-3 sm:h-4 bg-slate-700 rounded w-24 sm:w-28"></div>
                      <div className="h-3 sm:h-4 bg-slate-700 rounded w-16 sm:w-20"></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (data || []).length === 0 ? (
            <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-8 sm:p-12 border border-slate-700/30 text-center">
              <div className="text-3xl sm:text-4xl mb-3 sm:mb-4">📊</div>
              <div className="text-lg sm:text-xl text-gray-300 mb-2">
                {ticker ? `No signals found for ${ticker}` : 'No signals available'}
              </div>
              <div className="text-sm text-gray-400">Try clicking "Scan for Signals" to generate new signals</div>
            </div>
          ) : (
           <>
             {/* New signals notification */}
             {newSignalsCount > 0 && (
               <div className="bg-green-900/20 border border-green-800/50 rounded-2xl p-4 text-green-400 text-center status-update">
                 <div className="flex items-center justify-center gap-2">
                   <span className="text-xl">✨</span>
                   <span className="font-semibold">
                     {newSignalsCount} new signal{newSignalsCount > 1 ? 's' : ''} detected!
                   </span>
                   <span className="text-xl">📈</span>
                 </div>
               </div>
             )}

             {/* Signals list with smooth animations */}
             {(data || []).map((s: any, i: number) => (
               <div
                 key={`${s.ticker}-${s.ts}-${i}`}
                 className={`bg-slate-800/30 backdrop-blur-sm rounded-2xl p-4 sm:p-6 border signal-card hover:border-slate-600/50 transition-all duration-300 hover:scale-[1.02] ${
                   newSignalsCount > 0 && i < newSignalsCount
                     ? 'border-green-500/50 bg-green-900/10'
                     : 'border-slate-700/30'
                 }`}
                 style={{
                   animationDelay: `${i * 100}ms`,
                   animation: newSignalsCount > 0 && i < newSignalsCount ? 'fade-in 0.5s ease-out forwards' : 'none'
                 }}
               >
                 <div className="flex flex-col sm:flex-row justify-between items-start mb-3 sm:mb-4 gap-4 sm:gap-0">
                   <div className="flex-1 min-w-0">
                     <div className="flex flex-wrap items-center gap-2 sm:gap-3 mb-2">
                       <span className="text-base sm:text-lg font-bold text-blue-400 truncate">{s.ticker || '-'}</span>
                       <span
                         className={`px-2 sm:px-3 py-1 rounded-lg text-xs sm:text-sm font-semibold whitespace-nowrap ${
                           s.action === 'BUY'
                             ? 'bg-green-900/30 text-green-400'
                             : 'bg-red-900/30 text-red-400'
                         }`}
                       >
                         {s.action}
                       </span>
                       <span className="text-xs text-gray-300 bg-slate-700/50 px-2 sm:px-3 py-1 rounded-lg truncate">
                         {s.strategy}
                       </span>
                     </div>
                     <div className="text-xs sm:text-sm text-gray-400">
                       Generated {s.ts ? new Date(s.ts).toLocaleString() : 'N/A'}
                     </div>
                   </div>
                   <div className="w-full sm:w-auto sm:text-right">
                     <div className="text-xs sm:text-sm text-gray-400 mb-2">Confidence</div>
                     <div className="flex items-center gap-2 sm:gap-3">
                       <div className="flex-1 bg-slate-700/50 rounded-full h-2 sm:h-3 min-w-[60px] sm:min-w-[80px]">
                         <div
                           className={`h-2 sm:h-3 rounded-full confidence-bar transition-all duration-500 ${
                             (s.confidence || 0) > 0.7 ? 'bg-green-400' :
                             (s.confidence || 0) > 0.5 ? 'bg-yellow-400' : 'bg-red-400'
                           }`}
                           style={{ width: `${(s.confidence || 0) * 100}%` }}
                         ></div>
                       </div>
                       <div className={`text-sm sm:text-lg font-bold min-w-[35px] sm:min-w-[40px] ${
                         (s.confidence || 0) > 0.7 ? 'text-green-400' :
                         (s.confidence || 0) > 0.5 ? 'text-yellow-400' : 'text-red-400'
                       }`}>
                         {(s.confidence ? (s.confidence * 100).toFixed(0) : '0')}%
                       </div>
                     </div>
                   </div>
                 </div>

                 <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4 mb-3 sm:mb-4">
                   <div className="bg-white/5 rounded-xl p-3 sm:p-4 border border-white/10">
                     <div className="text-xs sm:text-sm text-gray-400 mb-1">Entry Price</div>
                     <div className="text-lg sm:text-xl font-bold text-white break-all">₹{Number(s.entry || 0).toFixed(2)}</div>
                   </div>
                   <div className="bg-white/5 rounded-xl p-3 sm:p-4 border border-white/10">
                     <div className="text-xs sm:text-sm text-gray-400 mb-1">Stop Loss</div>
                     <div className="text-lg sm:text-xl font-bold text-red-400 break-all">₹{Number(s.stop || 0).toFixed(2)}</div>
                   </div>
                   <div className="bg-white/5 rounded-xl p-3 sm:p-4 border border-white/10">
                     <div className="text-xs sm:text-sm text-gray-400 mb-1">Target</div>
                     <div className="text-lg sm:text-xl font-bold text-green-400 break-all">
                       {s.target ? `₹${Number(s.target).toFixed(2)}` : 'N/A'}
                     </div>
                   </div>
                 </div>

                 {/* Risk/Reward ratio */}
                 {s.target && s.stop && (
                   <div className="bg-slate-700/30 rounded-xl p-3 border border-slate-600/30">
                     <div className="text-xs sm:text-sm text-gray-300 break-words">
                       Risk/Reward Ratio: {((Number(s.target) - Number(s.entry || 0)) / (Number(s.entry || 0) - Number(s.stop))).toFixed(2)}:1
                     </div>
                   </div>
                 )}

                 {/* Warning for unusual prices */}
                 {Number(s.entry || 0) < 100 && (
                   <div className="text-xs sm:text-sm text-yellow-400 mt-3 flex items-center gap-2">
                     <span>⚠️</span>
                     <span className="break-words">Entry price seems unusual for this symbol</span>
                   </div>
                 )}
               </div>
             ))}
           </>
         )}
       </div>

       {/* Footer with real-time status - only show when updating */}
       {isBackgroundUpdating && (
         <div className="mt-4 sm:mt-6 bg-slate-800/30 backdrop-blur-sm rounded-2xl p-3 sm:p-4 border border-slate-700/30 flex items-center justify-center">
           <div className="flex items-center gap-2 text-blue-400">
             <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
             <span className="text-xs sm:text-sm">Live updates active</span>
           </div>
         </div>
       )}
     </div>
   </div>
 )
}
