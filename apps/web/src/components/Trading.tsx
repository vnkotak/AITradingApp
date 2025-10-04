"use client"

import { useEffect, useRef, useState } from 'react'
import { createChart, ISeriesApi } from 'lightweight-charts'
import Signals from './Signals'
import { getMarketAdapter, type Candle, type Timeframe } from '../lib/marketAdapter'
import { useTradingStore } from '../store/trading'
import { UTCTimestamp } from 'lightweight-charts'
import axios from 'axios'

function TradingStatus() {
   const positions = useTradingStore(s => s.positions)
   const orders = useTradingStore(s => s.orders)
   const cash = useTradingStore(s => s.cash)

   // Calculate total exposure and positions value
   const totalExposure = Object.values(positions).reduce((sum, pos) => {
     return sum + (Math.abs(pos.qty) * pos.avgPrice)
   }, 0)

   return (
       <div className="bg-gradient-to-r from-slate-800/50 to-blue-900/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/50 mb-4 sm:mb-6">
         <div className="flex items-center gap-2 mb-3 sm:mb-4">
           <div className="w-2 h-6 sm:h-8 bg-blue-500 rounded-full"></div>
           <h3 className="text-lg sm:text-xl font-bold text-white">Portfolio Status</h3>
         </div>
         <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-6">
         <div className="bg-white/5 rounded-xl p-4 border border-white/10">
           <div className="text-sm text-gray-300 mb-1">Available Cash</div>
           <div className="text-2xl font-bold text-white">₹{cash.toLocaleString('en-IN')}</div>
         </div>
         <div className="bg-white/5 rounded-xl p-4 border border-white/10">
           <div className="text-sm text-gray-300 mb-1">Active Positions</div>
           <div className="text-2xl font-bold text-blue-400">{Object.keys(positions).length}</div>
         </div>
         <div className="bg-white/5 rounded-xl p-4 border border-white/10">
           <div className="text-sm text-gray-300 mb-1">Total Exposure</div>
           <div className="text-2xl font-bold text-purple-400">₹{totalExposure.toLocaleString('en-IN')}</div>
         </div>
       </div>
     </div>
   )
 }

const API = process.env.NEXT_PUBLIC_API_BASE


export default function Trading({ isVisible = true }: { isVisible?: boolean }) {
      const [symbol, setSymbol] = useState({ ticker: 'HDFCBANK', exchange: 'NSE' as 'NSE'|'BSE' })
      const [availableSymbols, setAvailableSymbols] = useState<any[]>([])
      const [symbolsLoading, setSymbolsLoading] = useState(true) // Start as loading
      const [apiConnected, setApiConnected] = useState<boolean>(false)
      const [tf, setTf] = useState<Timeframe>('1m')
      const [candles, setCandles] = useState<Candle[]|null>(null)
  
      // Load cached symbols immediately on mount
      useEffect(() => {
        const cachedSymbols = (window as any).__trading_symbols__
        const cacheTime = (window as any).__trading_symbols_time__
        const now = Date.now()

        if (cachedSymbols && cacheTime && (now - cacheTime) < 600000) { // 10 minutes
          setAvailableSymbols(cachedSymbols)
          setSymbolsLoading(false)

          // If we have cached symbols and current symbol is default, switch to first cached symbol
          if (cachedSymbols.length > 0 && symbol.ticker === 'HDFCBANK') {
            const firstSymbol = cachedSymbols[0]
            setSymbol({ ticker: firstSymbol.ticker, exchange: firstSymbol.exchange })
          }
        } else {
          setSymbolsLoading(false) // No cache, but not loading yet
        }
      }, []) // Run only once on mount

      // Check API connectivity only when component is visible
      useEffect(() => {
        if (!isVisible) return

        const checkApiConnection = async () => {
          if (!API) {
            setApiConnected(false)
            return
          }

          try {
            const response = await axios.get(`${API}/health`, {
              timeout: 3000,
              headers: { 'Content-Type': 'application/json' }
            })

            setApiConnected(response.data?.status === 'ok')
          } catch (error) {
            setApiConnected(false)
          }
        }

        checkApiConnection()

        // Check connection every 2 minutes (less frequent)
        const interval = setInterval(checkApiConnection, 120000)

        return () => clearInterval(interval)
      }, [API, isVisible])
  
      // Load available symbols only when component is visible and we don't have them cached
      useEffect(() => {
        if (!isVisible || !API) return

        // Check if we have recent symbols cached (within 10 minutes)
        const cachedSymbols = (window as any).__trading_symbols__
        const cacheTime = (window as any).__trading_symbols_time__
        const now = Date.now()

        if (cachedSymbols && cacheTime && (now - cacheTime) < 600000) { // 10 minutes
          setAvailableSymbols(cachedSymbols)
          setSymbolsLoading(false)
          return
        }

        const loadSymbols = async () => {
          if (symbolsLoading) return // Prevent concurrent loads

          setSymbolsLoading(true)

          try {
            const response = await apiCallWithRetry(() =>
              axios.get(`${API}/symbols?active=true`, {
                timeout: 5000,
                headers: { 'Content-Type': 'application/json' }
              })
            )

            const symbols = response.data || []
            setAvailableSymbols(symbols)

            // Cache the symbols globally for this session
            ;(window as any).__trading_symbols__ = symbols
            ;(window as any).__trading_symbols_time__ = now

            // If we have symbols and current symbol is the default, switch to first available
            if (symbols.length > 0 && symbol.ticker === 'HDFCBANK') {
              const firstSymbol = symbols[0]
              setSymbol({ ticker: firstSymbol.ticker, exchange: firstSymbol.exchange })
            }

          } catch (error) {
            console.error('Failed to load symbols:', error instanceof Error ? error.message : String(error))
          } finally {
            setSymbolsLoading(false)
          }
        }

        loadSymbols()

        // Only retry once after 30 seconds if we still have no symbols
        let retryTimeout: any = null
        if (availableSymbols.length === 0) {
          retryTimeout = setTimeout(() => {
            if (availableSymbols.length === 0 && isVisible && !symbolsLoading) {
              loadSymbols()
            }
          }, 30000)
        }

        return () => {
          if (retryTimeout) clearTimeout(retryTimeout)
        }
      }, [isVisible, API]) // Minimal dependencies to prevent unnecessary reloads
   const [autoTrading, setAutoTrading] = useState(false)
   const [lastSignal, setLastSignal] = useState<any>(null)
   const [forceRefresh, setForceRefresh] = useState(0) // Force refresh trigger
   const [quantity, setQuantity] = useState<number>(10)
   const [suggestedQty, setSuggestedQty] = useState<number>(10)
   const containerRef = useRef<HTMLDivElement>(null)
   const chartRef = useRef<any>(null)
   const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
   const placeOrder = useTradingStore(s => s.placeOrder)
   const markPrice = useTradingStore(s => s.markPrice)

   // Calculate suggested quantity locally when candles are available
   useEffect(() => {
       if (!isVisible || !candles || candles.length === 0) return

       const currentPrice = candles[candles.length - 1].close
       if (!currentPrice || currentPrice <= 0) return

       // Simple calculation: target ₹10,000 trade value
       const targetValue = 10000
       let suggestedQty = targetValue / currentPrice

       // Round to reasonable precision
       if (suggestedQty >= 100) {
           suggestedQty = Math.round(suggestedQty)
       } else if (suggestedQty >= 10) {
           suggestedQty = Math.round(suggestedQty * 10) / 10
       } else if (suggestedQty >= 1) {
           suggestedQty = Math.round(suggestedQty * 100) / 100
       } else {
           suggestedQty = Math.round(suggestedQty * 10000) / 10000
       }

       const finalQty = Math.max(1, Math.floor(suggestedQty))
       setSuggestedQty(finalQty)
       setQuantity(finalQty)
   }, [candles, isVisible])

  useEffect(() => {
    if (!containerRef.current || !isVisible) return

    // Get container dimensions
    const rect = containerRef.current.getBoundingClientRect()
    const width = Math.max(100, rect.width)
    const height = Math.max(100, rect.height)

    const chart = createChart(containerRef.current, {
      width: width,
      height: height,
      layout: {
        background: { color: '#0b0f15' },
        textColor: '#9ca3af',
        fontSize: 12
      },
      grid: {
        vertLines: { color: '#111827' },
        horzLines: { color: '#111827' }
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: '#485158',
      },
      rightPriceScale: {
        borderColor: '#485158',
        textColor: '#9ca3af',
        autoScale: true,
        mode: 0,
        entireTextOnly: false,
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#6A5ACD',
          width: 1,
          style: 2,
        },
        horzLine: {
          color: '#6A5ACD',
          width: 1,
          style: 2,
        },
      }
    })

    chartRef.current = chart
    const series = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    })
    seriesRef.current = series

    const handleResize = () => {
      if (!containerRef.current || !chart) return

      const rect = containerRef.current.getBoundingClientRect()
      const newWidth = Math.max(100, rect.width)
      const newHeight = Math.max(100, rect.height)

      chart.applyOptions({
        width: newWidth,
        height: newHeight
      })
    }

    // Use ResizeObserver for more reliable resizing
    const resizeObserver = new ResizeObserver(() => {
      handleResize()
    })

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current)
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      resizeObserver.disconnect()
      chart.remove()
      seriesRef.current = null
      chartRef.current = null
    }
  }, [isVisible])


  // API retry utility with exponential backoff
  const apiCallWithRetry = async (apiCall: () => Promise<any>, maxRetries = 3) => {
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await apiCall()
      } catch (error) {
        if (i === maxRetries - 1) throw error
        // Exponential backoff: 1s, 2s, 4s
        await new Promise(resolve => setTimeout(resolve, Math.pow(2, i) * 1000))
      }
    }
  }

  useEffect(() => {
    if (!isVisible) return // Only load candles when component is visible

    let mounted = true
    let timer: any

    const loadCandles = async () => {
      if (!API) return

      try {
        setCandles(null) // Clear previous data

        const API_BASE = process.env.NEXT_PUBLIC_API_BASE
        if (!API_BASE) throw new Error('API base URL not configured')

        // Single consolidated API call with smart auto-fetch
        const candlesUrl = `${API_BASE}/candles/ticker/${symbol.ticker}?exchange=${symbol.exchange}&tf=${tf}&limit=100&auto_fetch=true`

        const candlesRes = await apiCallWithRetry(() =>
          axios.get(candlesUrl, {
            timeout: 10000, // 10 second timeout
            headers: { 'Content-Type': 'application/json' }
          })
        )

        if (!mounted) return

        let cs: Candle[] = candlesRes.data || []

        // Fallback to marketAdapter if no data
        if (cs.length === 0) {
          const ad = await getMarketAdapter()
          cs = await ad.getCandles(symbol.ticker, symbol.exchange, tf, 100)
        }

        if (cs && cs.length > 0) {
          // Filter out invalid candles
          const validCandles = cs.filter(c =>
            c && c.ts &&
            typeof c.open === 'number' && typeof c.close === 'number' &&
            !isNaN(c.open) && !isNaN(c.close) &&
            c.open > 0 && c.close > 0
          )

          if (validCandles.length > 0) {
            setCandles(validCandles)
            const lastPrice = validCandles[validCandles.length - 1].close
            markPrice(symbol.ticker, symbol.exchange, lastPrice)
          } else {
            setCandles([])
          }
        } else {
          setCandles([])
        }

        // Auto-refresh based on timeframe
        const refreshInterval = tf === '1m' ? 30000 : tf === '5m' ? 60000 : 300000
        timer = setTimeout(loadCandles, refreshInterval)

      } catch (error) {
        if (mounted) {
          console.error('Failed to load candles:', error instanceof Error ? error.message : String(error))
          setCandles([])
        }
      }
    }

    loadCandles()

    return () => {
      mounted = false
      if (timer) clearTimeout(timer)
    }
  }, [symbol, tf, markPrice, forceRefresh, API, isVisible])

  // Handle timeframe changes and price scale updates
  useEffect(() => {
    if (candles && candles.length > 0 && chartRef.current) {
      // Reset price scale when candles data changes
      chartRef.current.priceScale('right').applyOptions({
        autoScale: true,
      })
    }
  }, [tf, candles])

  useEffect(() => {
    if (!candles || !seriesRef.current || !chartRef.current) return
    if (candles.length === 0) return

    try {
      // Process candle data with proper time formatting
      const data = candles
        .filter(c => c && c.ts && !isNaN(c.open) && !isNaN(c.close) && c.open > 0 && c.close > 0)
        .map((c) => {
          // Convert to IST timestamp for proper Indian market hours display
          const utcTime = new Date(c.ts).getTime()
          const istOffset = 5.5 * 60 * 60 * 1000 // IST is UTC + 5:30
          const istTime = utcTime + istOffset
          const timestamp = Math.floor(istTime / 1000) as UTCTimestamp

          return {
            time: timestamp,
            open: Number(c.open),
            high: Number(c.high),
            low: Number(c.low),
            close: Number(c.close)
          }
        })

      if (data.length === 0) return

      // Set data on the series
      seriesRef.current.setData(data)

      // Configure time scale for IST display
      chartRef.current.timeScale().applyOptions({
        timeVisible: true,
        secondsVisible: false,
        borderVisible: true,
      })

      // Apply IST formatting to time scale after chart is created
      // Note: LightweightCharts displays time in the user's local timezone by default
      // The timestamp conversion to IST should handle the timezone display

      // Configure price scale for better auto-scaling
      chartRef.current.priceScale('right').applyOptions({
        autoScale: true,
        mode: 0,
        entireTextOnly: false,
        visible: true,
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      })

      // Fit content to show all data
      chartRef.current.timeScale().fitContent()

      // Force price scale to fit the data range
      setTimeout(() => {
        chartRef.current.priceScale('right').applyOptions({
          autoScale: true,
        })
      }, 100)

    } catch (error) {
      console.error('❌ Error setting chart data:', error)
    }
  }, [candles])

  // Auto-trading effect - only when tab is visible (more resilient)
  useEffect(() => {
    if (!autoTrading || !API || !isVisible) return

    let interval: any
    const checkSignals = async () => {
      try {
        const res = await axios.get(
          `${API}/signals?ticker=${symbol.ticker}&exchange=${symbol.exchange}&tf=${tf}&limit=1`,
          { timeout: 5000 }
        )
        const signals = res.data || []

        if (signals.length > 0) {
          const signal = signals[0]
          if (lastSignal?.id !== signal.id) {
            setLastSignal(signal)
            // Auto-execute signal
            if (signal.action === 'BUY') {
              await placeOrder({
                ticker: symbol.ticker,
                exchange: symbol.exchange,
                side: 'BUY',
                qty: 10
              })
            } else if (signal.action === 'SELL') {
              await placeOrder({
                ticker: symbol.ticker,
                exchange: symbol.exchange,
                side: 'SELL',
                qty: 10
              })
            }
          }
        }
      } catch (error) {
        console.warn('⚠️ Auto-trading signal check failed:', error instanceof Error ? error.message : String(error))
      }
    }

    checkSignals()
    interval = setInterval(checkSignals, 60000) // Check once per minute
  
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoTrading, symbol, tf, API, lastSignal, placeOrder, isVisible])

  return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 p-3 sm:p-6">
        <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
         <TradingStatus />

         <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 sm:gap-5 xl:gap-6">
           {/* Trade Panel */}
           <div className="xl:col-span-1 bg-slate-800/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/30">
             <div className="flex items-center gap-2 mb-4 sm:mb-6">
               <div className="w-2 h-6 sm:h-8 bg-green-500 rounded-full"></div>
               <h3 className="text-lg sm:text-xl font-bold text-white">Trading Panel</h3>
             </div>

             <div className="space-y-4">
               <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                 <div className="text-sm text-gray-300 mb-2">Symbol Selection</div>
                 <select
                   className="w-full bg-slate-900/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
                   value={`${symbol.ticker}-${symbol.exchange}`}
                   onChange={(e) => {
                     const [ticker, exchange] = e.target.value.split('-')
                     const newSymbol = { ticker, exchange: exchange as 'NSE'|'BSE' }
                     setSymbol(newSymbol)
                   }}
                   disabled={symbolsLoading && availableSymbols.length === 0}
                 >
                   {availableSymbols.length === 0 ? (
                     symbolsLoading ? (
                       <option>Loading symbols...</option>
                     ) : (
                       <option>No symbols available</option>
                     )
                   ) : (
                     availableSymbols.map((s, index) => (
                       <option key={`${s.ticker}-${s.exchange}-${index}`} value={`${s.ticker}-${s.exchange}`}>
                         {s.ticker}.{s.exchange==='NSE'?'NS':'BO'} - {s.name || 'N/A'}
                       </option>
                     ))
                   )}
                 </select>
               </div>

               <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                 <div className="text-sm text-gray-300 mb-3">Timeframe</div>
                 <select
                   className="w-full bg-slate-900/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
                   value={tf}
                   onChange={e=>setTf(e.target.value as Timeframe)}
                 >
                   <option value="1m">1 Minute</option>
                   <option value="5m">5 Minutes</option>
                   <option value="15m">15 Minutes</option>
                   <option value="1h">1 Hour</option>
                   <option value="1d">1 Day</option>
                 </select>
               </div>

               <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                 <div className="text-sm text-gray-300 mb-2">Quantity</div>
                 <div className="flex items-center gap-2">
                   <input
                     type="number"
                     min="1"
                     max="10000"
                     value={quantity}
                     onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
                     className="flex-1 bg-slate-900/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
                     placeholder="Enter quantity"
                   />
                   <button
                     onClick={() => setQuantity(suggestedQty)}
                     className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition-colors"
                     title={`Use suggested quantity: ${suggestedQty}`}
                   >
                     {suggestedQty}
                   </button>
                 </div>
                 <div className="text-xs text-gray-400 mt-1">
                   Suggested: {suggestedQty} shares
                 </div>
               </div>

               {API && (
                 <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                   <label className="flex items-center gap-3 mb-2">
                     <input
                       type="checkbox"
                       checked={autoTrading}
                       onChange={(e) => setAutoTrading(e.target.checked)}
                       className="w-4 h-4 rounded border-slate-600 text-blue-500 focus:ring-blue-500"
                     />
                     <span className="text-white font-medium">Auto Trading</span>
                   </label>
                   {autoTrading && (
                     <div className="text-xs text-gray-400 bg-blue-900/20 rounded-lg p-2 border border-blue-800/30">
                       Automatically executing AI signals
                     </div>
                   )}
                 </div>
               )}

               <div className="grid grid-cols-2 gap-3">
                 <button
                   onClick={async () => {
                     if (quantity > 0) {
                       await placeOrder({
                         ticker: symbol.ticker,
                         exchange: symbol.exchange,
                         side: 'BUY',
                         qty: quantity
                       })
                     }
                   }}
                   disabled={quantity <= 0}
                   className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 disabled:from-gray-600 disabled:to-gray-700 px-4 py-3 rounded-lg text-white font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-green-500/25 disabled:hover:scale-100 disabled:opacity-50"
                 >
                   Buy {quantity > 0 ? `${quantity}` : ''}
                 </button>
                 <button
                   onClick={async () => {
                     if (quantity > 0) {
                       await placeOrder({
                         ticker: symbol.ticker,
                         exchange: symbol.exchange,
                         side: 'SELL',
                         qty: quantity
                       })
                     }
                   }}
                   disabled={quantity <= 0}
                   className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 disabled:from-gray-600 disabled:to-gray-700 px-4 py-3 rounded-lg text-white font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-red-500/25 disabled:hover:scale-100 disabled:opacity-50"
                 >
                   Sell {quantity > 0 ? `${quantity}` : ''}
                 </button>
               </div>

               {/* Connection Diagnostic Panel - shows when API is disconnected or no symbols */}
               {(!apiConnected || availableSymbols.length === 0) && (
                 <div className="bg-gradient-to-r from-red-900/20 to-orange-900/20 backdrop-blur-sm rounded-xl p-4 border border-red-700/30">
                   <div className="flex items-center gap-2 mb-2">
                     <div className="w-2 h-6 bg-red-500 rounded-full"></div>
                     <span className="text-white font-semibold">
                       {availableSymbols.length === 0 ? 'No Symbols Loaded' : 'Connection Issue'}
                     </span>
                   </div>
                   <div className="text-sm text-gray-300 mb-3">
                     {availableSymbols.length === 0
                       ? 'Unable to load trading symbols. This may be due to:'
                       : 'API server is not responding. This may be due to:'
                     }
                   </div>
                   <div className="text-xs text-gray-400 space-y-1 mb-3">
                     <div>• API server not running on localhost:8000</div>
                     <div>• Database not configured or empty</div>
                     <div>• Network connectivity issues</div>
                     <div>• CORS configuration problems</div>
                   </div>
                   <div className="text-xs text-gray-500 font-mono bg-black/20 p-2 rounded mb-3">
                     Try: cd apps/api && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
                   </div>
                   <div className="flex gap-2">
                     <button
                       onClick={() => window.location.reload()}
                       className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition-colors"
                     >
                       🔄 Refresh Page
                     </button>
                     <button
                       onClick={async () => {
                         try {
                           console.log('🔍 Testing API endpoints...')
                           const response = await fetch(`${API}/symbols?active=true`)
                           console.log('📊 Symbols endpoint status:', response.status)
                           if (response.ok) {
                             const data = await response.json()
                             console.log('📊 Symbols data:', data)
                             alert(`Found ${data.length} symbols! Check console for details.`)
                           } else {
                             console.error('❌ Symbols endpoint failed:', response.statusText)
                             alert(`Symbols endpoint failed: ${response.statusText}`)
                           }
                         } catch (error) {
                           console.error('❌ API test failed:', error)
                           alert(`API test failed: ${error instanceof Error ? error.message : String(error)}`)
                         }
                       }}
                       className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded transition-colors"
                     >
                       🧪 Test API
                     </button>
                   </div>
                 </div>
               )}

               {lastSignal && (
                 <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 backdrop-blur-sm rounded-xl p-4 border border-blue-700/30">
                   <div className="flex items-center gap-2 mb-2">
                     <div className="w-2 h-6 bg-blue-500 rounded-full"></div>
                     <span className="text-white font-semibold">Last AI Signal</span>
                   </div>
                   <div className="grid grid-cols-2 gap-4 text-sm">
                     <div>
                       <span className="text-gray-300">Action:</span>
                       <span className={`ml-2 font-bold ${lastSignal.action === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                         {lastSignal.action}
                       </span>
                     </div>
                     <div>
                       <span className="text-gray-300">Entry:</span>
                       <span className="ml-2 text-white">₹{Number(lastSignal.entry).toFixed(2)}</span>
                     </div>
                     <div>
                       <span className="text-gray-300">Confidence:</span>
                       <span className="ml-2 text-blue-400">{(lastSignal.confidence * 100).toFixed(0)}%</span>
                     </div>
                     <div>
                       <span className="text-gray-300">Strategy:</span>
                       <span className="ml-2 text-purple-400">{lastSignal.strategy}</span>
                     </div>
                   </div>
                 </div>
               )}
             </div>
           </div>

           {/* Chart Panel */}
           <div className="xl:col-span-2 bg-slate-800/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/30">
             <div className="flex items-center justify-between mb-3 sm:mb-4">
               <div className="flex items-center gap-2">
                 <div className="w-2 h-6 sm:h-8 bg-purple-500 rounded-full"></div>
                 <h3 className="text-lg sm:text-xl font-bold text-white">Price Chart</h3>
                 {candles === null && (
                   <div className="flex items-center gap-1 text-purple-400 text-sm">
                     <div className="w-1 h-1 bg-purple-400 rounded-full animate-pulse"></div>
                     <span>Loading {tf} data{apiConnected ? ' (auto-fetching if needed)...' : '...'}</span>
                   </div>
                 )}
               </div>

               {/* Manual Refresh Button */}
               <button
                 onClick={() => setForceRefresh(prev => prev + 1)}
                 className="px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded-lg transition-colors flex items-center gap-1"
                 title="Refresh chart data"
               >
                 <span>🔄</span>
                 <span className="hidden sm:inline">Refresh</span>
               </button>
             </div>
             <div className="rounded-xl overflow-hidden border border-slate-600/50 relative bg-slate-900 h-[320px] sm:h-[480px] lg:h-[520px] chart-container">
               <div
                 ref={containerRef}
                 className="w-full h-full"
                 style={{
                   backgroundColor: '#0b0f15'
                 }}
               />
               {candles !== null && candles.length === 0 && (
                 <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 backdrop-blur-sm">
                   <div className="text-center text-gray-400">
                     <div className="text-4xl mb-2">{apiConnected ? '📊' : '🔌'}</div>
                     <div className="mb-2">
                       {apiConnected ? 'No Chart Data Available' : 'API Server Not Connected'}
                     </div>
                     <div className="text-sm mb-2">
                       {apiConnected
                         ? 'Database needs candle data population'
                         : 'Start the API server to load real data'
                       }
                     </div>
                     <div className="text-xs text-gray-500">
                       {apiConnected
                         ? `Auto-fetching ${tf} data from Yahoo Finance...`
                         : 'Run: cd apps/api && python -m uvicorn main:app --host 0.0.0.0 --port 8000'
                       }
                     </div>
                   </div>
                 </div>
               )}
             </div>
           </div>
         </div>

         <Signals ticker={symbol.ticker} exchange={symbol.exchange as any} isVisible={isVisible} />
       </div>
     </div>
   )
}


