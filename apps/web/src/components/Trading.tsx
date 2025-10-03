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
         <div className="grid grid-cols-3 gap-3 sm:gap-6">
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
    const [symbolsLoading, setSymbolsLoading] = useState(false)
    const [apiConnected, setApiConnected] = useState<boolean>(false)
    const [tf, setTf] = useState<Timeframe>('1m')
    const [candles, setCandles] = useState<Candle[]|null>(null)
  
      // Check API connectivity on component mount (reduced frequency)
      useEffect(() => {
        const checkApiConnection = async () => {
          if (!API) return
  
          try {
            // Use the cached connection check instead of direct API call
            await getMarketAdapter()
            setApiConnected(true)
            console.log('✅ API server is running')
          } catch (error) {
            setApiConnected(false)
            console.error('❌ API server not running at', API)
          }
        }
  
        checkApiConnection()
  
        // Check connection every 60 seconds instead of continuously
        const interval = setInterval(checkApiConnection, 60000)
  
        return () => clearInterval(interval)
      }, [API])
  
      // Load available symbols on component mount
      useEffect(() => {
        if (!API || !apiConnected) return
  
        const loadSymbols = async () => {
          setSymbolsLoading(true)
          try {
            const response = await axios.get(`${API}/symbols?active=true`)
            const symbols = response.data || []
  
            console.log('Available symbols:', symbols)
            setAvailableSymbols(symbols)
  
            // If current symbol is not in the available symbols, switch to first available
            if (symbols.length > 0 && !symbols.find((s: any) => s.ticker === symbol.ticker && s.exchange === symbol.exchange)) {
              setSymbol({ ticker: symbols[0].ticker, exchange: symbols[0].exchange })
            }
          } catch (error) {
            console.error('Failed to load symbols:', error)
            setApiConnected(false)
          } finally {
            setSymbolsLoading(false)
          }
        }
  
        loadSymbols()
      }, [API, apiConnected])
   const [autoTrading, setAutoTrading] = useState(false)
   const [lastSignal, setLastSignal] = useState<any>(null)
   const containerRef = useRef<HTMLDivElement>(null)
   const chartRef = useRef<any>(null)
   const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
   const placeOrder = useTradingStore(s => s.placeOrder)
   const markPrice = useTradingStore(s => s.markPrice)

  useEffect(() => {
    if (!containerRef.current) {
      console.log('Chart container not available')
      return
    }

    console.log('🎯 Initializing chart...')
    const width = containerRef.current.clientWidth || 800
    const height = 300 // Will be updated by handleResize

    console.log('📊 Chart dimensions:', { width, height })

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
        textColor: '#9ca3af'
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

    console.log('✅ Chart and series created successfully')

    const handleResize = () => {
      const newWidth = containerRef.current?.clientWidth || 800
      console.log('🔄 Resizing chart to:', newWidth)
      chart.applyOptions({ width: newWidth })
    }

    window.addEventListener('resize', handleResize)

    return () => {
      console.log('🧹 Cleaning up chart')
      window.removeEventListener('resize', handleResize)
      chart.remove()
      seriesRef.current = null
      chartRef.current = null
    }
  }, [])

  // Monitor container dimensions
  useEffect(() => {
    const checkDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        console.log('Container dimensions:', {
          width: rect.width,
          height: rect.height,
          clientWidth: containerRef.current.clientWidth,
          clientHeight: containerRef.current.clientHeight
        })
      }
    }

    const interval = setInterval(checkDimensions, 1000)
    checkDimensions() // Check immediately

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    let mounted = true
    let timer: any

    const loadCandles = async () => {
      try {
        console.log(`🔄 Loading ${tf} candles for ${symbol.ticker}.${symbol.exchange}`)

        // Clear previous candles immediately
        setCandles(null)

        // Show loading state with indication that it might fetch fresh data
        console.log(`📊 Checking database for ${tf} data...`)

        const ad = await getMarketAdapter()
        console.log('📡 Market adapter obtained, fetching candles...')

        const cs = await ad.getCandles(symbol.ticker, symbol.exchange, tf, 100)
        if (!mounted) return

        console.log(`✅ Loaded ${cs?.length || 0} ${tf} candles`)

        if (cs && cs.length > 0) {
          // Validate candle data
          const validCandles = cs.filter(c =>
            c &&
            c.ts &&
            typeof c.open === 'number' &&
            typeof c.high === 'number' &&
            typeof c.low === 'number' &&
            typeof c.close === 'number' &&
            !isNaN(c.open) && !isNaN(c.close)
          )

          console.log(`🔍 ${validCandles.length}/${cs.length} candles are valid`)

          if (validCandles.length > 0) {
            setCandles(validCandles)
            const last = validCandles[validCandles.length - 1].close
            console.log(`💰 Last candle price: ₹${last}`)
            markPrice(symbol.ticker, symbol.exchange, last)
          } else {
            console.warn('⚠️ No valid candles after validation')
            setCandles([])
          }
        } else {
          console.warn('⚠️ No candles received from API')
          setCandles([])
        }

        // Auto-refresh based on timeframe (reduced frequency to reduce DB load)
        const refreshInterval = tf === '1m' ? 60000 : tf === '5m' ? 120000 : 300000 // 1m=1min, 5m=2min, others=5min
        timer = setTimeout(loadCandles, refreshInterval)

      } catch (error) {
        console.error(`❌ Error loading ${tf} candles:`, error)
        if (mounted) {
          // Show error message when API is not available
          const errorMessage = error instanceof Error ? error.message : 'Unknown error'
          console.error('💥 API Error:', errorMessage)
          setCandles([])
        }
      }
    }

    loadCandles()

    return () => {
      mounted = false
      if (timer) clearTimeout(timer)
    }
  }, [symbol, tf, markPrice])

  useEffect(() => {
    if (!candles || !seriesRef.current || !chartRef.current) {
      console.log('❌ Chart not ready:', {
        candles: !!candles,
        candlesLength: candles?.length || 0,
        series: !!seriesRef.current,
        chart: !!chartRef.current
      })
      return
    }

    if (candles.length === 0) {
      console.log('⚠️ No candles to display')
      return
    }

    console.log(`📈 Setting chart data with ${candles.length} candles`)

    try {
      // Process candle data with proper time formatting
      const data = candles
        .filter(c => c && c.ts && !isNaN(c.open) && !isNaN(c.close)) // Filter out invalid candles
        .map((c, index) => {
          const timestamp = Math.floor(new Date(c.ts).getTime() / 1000) as UTCTimestamp

          // Debug first and last candles
          if (index === 0 || index === candles.length - 1) {
            console.log(`Candle ${index}:`, {
              time: c.ts,
              timestamp,
              open: c.open,
              high: c.high,
              low: c.low,
              close: c.close,
              date: new Date(c.ts).toLocaleString()
            })
          }

          return {
            time: timestamp,
            open: Number(c.open),
            high: Number(c.high),
            low: Number(c.low),
            close: Number(c.close)
          }
        })

      console.log(`✅ Processed ${data.length} valid candles`)
      console.log('Sample candles:', data.slice(0, 3), '...', data.slice(-3))

      if (data.length === 0) {
        console.warn('⚠️ No valid candles after filtering')
        return
      }

      // Set data on the series
      seriesRef.current.setData(data)

      // Configure time scale for proper display
      chartRef.current.timeScale().applyOptions({
        timeVisible: true,
        secondsVisible: false,
        borderVisible: true,
      })

      // Fit content to show all data
      chartRef.current.timeScale().fitContent()

      console.log('✅ Chart data set successfully')

    } catch (error) {
      console.error('❌ Error setting chart data:', error)
    }
  }, [candles])

  // Auto-trading effect - only when tab is visible
  useEffect(() => {
    if (!autoTrading || !API || !isVisible) return

    let interval: any
    const checkSignals = async () => {
      try {
        const res = await axios.get(`${API}/signals?ticker=${symbol.ticker}&exchange=${symbol.exchange}&tf=${tf}&limit=1`)
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
        console.error('Auto-trading error:', error)
      }
    }

    checkSignals()
    interval = setInterval(checkSignals, 30000) // Check every 30 seconds (reduced from 5 seconds)

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoTrading, symbol, tf, API, lastSignal, placeOrder, isVisible])

  return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 p-3 sm:p-6">
        <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
         <TradingStatus />

         <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-5 lg:gap-6">
           {/* Trade Panel */}
           <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/30">
             <div className="flex items-center gap-2 mb-4 sm:mb-6">
               <div className="w-2 h-6 sm:h-8 bg-green-500 rounded-full"></div>
               <h3 className="text-lg sm:text-xl font-bold text-white">Trading Panel</h3>
               <div className={`px-2 py-1 rounded text-xs ${apiConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                 {apiConnected ? 'API Connected' : 'API Disconnected'}
               </div>
             </div>

             <div className="space-y-4">
               <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                 <div className="text-sm text-gray-300 mb-2">Symbol Selection</div>
                 <select
                   className="w-full bg-slate-900/50 border border-slate-600 rounded-lg px-3 py-2 text-white focus:border-blue-500 focus:outline-none"
                   value={`${symbol.ticker}-${symbol.exchange}`}
                   onChange={(e) => {
                     const [ticker, exchange] = e.target.value.split('-')
                     setSymbol({ ticker, exchange: exchange as 'NSE'|'BSE' })
                   }}
                   disabled={symbolsLoading}
                 >
                   {symbolsLoading ? (
                     <option>Loading symbols...</option>
                   ) : (
                     availableSymbols.map((s) => (
                       <option key={`${s.ticker}-${s.exchange}`} value={`${s.ticker}-${s.exchange}`}>
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
                   onClick={async () => { await placeOrder({ ticker: symbol.ticker, exchange: symbol.exchange, side: 'BUY', qty: 10 }) }}
                   className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-500 hover:to-green-600 px-4 py-3 rounded-lg text-white font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-green-500/25"
                 >
                   Buy Market
                 </button>
                 <button
                   onClick={async () => { await placeOrder({ ticker: symbol.ticker, exchange: symbol.exchange, side: 'SELL', qty: 10 }) }}
                   className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 px-4 py-3 rounded-lg text-white font-semibold transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-red-500/25"
                 >
                   Sell Market
                 </button>
               </div>

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
           <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/30">
             <div className="flex items-center gap-2 mb-3 sm:mb-4">
               <div className="w-2 h-6 sm:h-8 bg-purple-500 rounded-full"></div>
               <h3 className="text-lg sm:text-xl font-bold text-white">Price Chart</h3>
               {candles === null && (
                 <div className="flex items-center gap-1 text-purple-400 text-sm">
                   <div className="w-1 h-1 bg-purple-400 rounded-full animate-pulse"></div>
                   <span>Loading {tf} data{apiConnected ? ' (auto-fetching if needed)...' : '...'}</span>
                 </div>
               )}
             </div>
             <div className="rounded-xl overflow-hidden border border-slate-600/50 relative bg-slate-900">
               <div
                 ref={containerRef}
                 className="w-full h-[300px] sm:h-[420px] min-h-[300px] sm:min-h-[420px] relative"
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


