"use client"

import { useEffect, useMemo, useState } from 'react'
import { useTradingStore } from '../store/trading'
import { getMarketAdapter } from '../lib/marketAdapter'

export default function Portfolio({ isVisible = true }: { isVisible?: boolean }) {
    // Temporarily bypass store, load directly from database
     const [positions, setPositions] = useState<Record<string, any>>({})
     const [marks, setMarks] = useState<Record<string, number>>({})
     const [loading, setLoading] = useState(true)
     const [refreshing, setRefreshing] = useState(false)
     const [pricesLoading, setPricesLoading] = useState(false)
     const [portfolioPerformance, setPortfolioPerformance] = useState<any>(null)
     const [pnlData, setPnlData] = useState<any[]>([])
     const portfolioRefreshTrigger = useTradingStore(s => s.portfolioRefreshTrigger)

     // Check if Indian markets are currently open
     const isMarketOpen = (): boolean => {
       const now = new Date()

       // Convert to IST (UTC+5:30) - get IST components
       const istOffset = 5.5 * 60 * 60 * 1000 // 5.5 hours in milliseconds
       const istTime = new Date(now.getTime() + istOffset)

       // Get IST date components
       const year = istTime.getUTCFullYear()
       const month = istTime.getUTCMonth()
       const day = istTime.getUTCDate()
       const hour = istTime.getUTCHours()
       const minute = istTime.getUTCMinutes()

       // Create IST date object to get correct day of week
       const istDate = new Date(year, month, day)
       const dayOfWeek = istDate.getDay() // 0=Sunday, 1=Monday, ..., 6=Saturday

       // Check if it's a weekday (Monday-Friday)
       const isWeekday = dayOfWeek >= 1 && dayOfWeek <= 5

       if (!isWeekday) return false

       // Check if within market hours (9:15 AM - 3:30 PM IST)
       const marketOpen = hour > 9 || (hour === 9 && minute >= 15)
       const marketClose = hour < 15 || (hour === 15 && minute <= 30)

       return marketOpen && marketClose
     }

  // Load positions from database on mount and when refresh is triggered (only when tab is visible)
  useEffect(() => {
    if (!isVisible) return

    const loadPositionsFromDB = async () => {
      try {
        // If this is a refresh (not initial load), show refreshing state
        if (!loading) {
          setRefreshing(true)
        }

        const API_BASE = process.env.NEXT_PUBLIC_API_BASE
        if (!API_BASE) {
          setLoading(false)
          setRefreshing(false)
          return
        }

        console.log('Fetching positions from database...')
        const response = await fetch(`${API_BASE}/positions`)
        console.log('Positions API response status:', response.status)

        if (response.ok) {
          const dbPositions = await response.json()
          console.log('Raw positions from database:', dbPositions)

          // Convert database positions to local store format
          // API already includes ticker and exchange
          const positionsMap: Record<string, any> = {}
          for (const pos of dbPositions) {
            if (pos.ticker && pos.exchange) { // Show all positions including zero quantity
              const key = `${pos.ticker}.${pos.exchange}`
              positionsMap[key] = {
                ticker: pos.ticker,
                exchange: pos.exchange,
                qty: pos.qty,
                avgPrice: pos.avg_price
              }
              console.log('Added position:', key, positionsMap[key])
            }
          }

          console.log('Final positions map:', positionsMap)

          // Update component state with positions from DB
          if (Object.keys(positionsMap).length > 0) {
            setPositions(positionsMap)
            console.log('✅ Successfully loaded positions from database:', positionsMap)
          } else {
            // Clear local positions if DB has no positions
            setPositions({})
            console.log('No positions found in database, clearing positions')
          }
        }

        // Also fetch portfolio performance data
        const performanceResponse = await fetch(`${API_BASE}/portfolio/performance`)
        if (performanceResponse.ok) {
          const performanceData = await performanceResponse.json()
          setPortfolioPerformance(performanceData)
          console.log('✅ Loaded portfolio performance:', performanceData)
        } else {
          console.log('⚠️ Could not fetch portfolio performance')
          setPortfolioPerformance(null)
        }

        // Load P&L data for chart
        const pnlResponse = await fetch(`${API_BASE}/pnl/summary?range_days=90`)
        if (pnlResponse.ok) {
          const pnlChartData = (await pnlResponse.json()).equity || []
          setPnlData(pnlChartData)
          console.log('✅ Loaded P&L data:', pnlChartData.length, 'points')
        } else {
          console.log('⚠️ Could not fetch P&L data')
          setPnlData([])
        }
      } catch (error) {
        console.error('Failed to load positions from database:', error)
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    }

    loadPositionsFromDB()
  }, [loading, setPositions, portfolioRefreshTrigger, isVisible])

  useEffect(() => {
    if (!isVisible || loading) return // Only fetch prices when Portfolio tab is visible and positions are loaded

    let mounted = true
    let timer: any

    const load = async () => {
      // Double-check visibility before making API calls
      if (!mounted || !isVisible) return

      try {
        // Only show loading for initial load, not for refreshes
        setPricesLoading(true)
        const ad = await getMarketAdapter()
        const kv: Record<string, number> = {}
        for (const key of Object.keys(positions)) {
          // Break if component unmounted or tab changed
          if (!mounted || !isVisible) return

          const p = positions[key]
          const price = await ad.getLastPrice(p.ticker, p.exchange)

          // Validate price - skip invalid prices (zero, negative, or extremely low)
          if (price > 0.01) {  // Minimum valid price threshold
            kv[key] = price
          } else {
            console.warn(`⚠️ No valid price available for ${key}: ${price} (real-time fetch failed, candle fallback unsuccessful)`)
            // Use avg price as fallback for display, but mark as invalid
            kv[key] = -1  // Special marker for invalid price
          }
        }
        if (mounted && isVisible) {
          setMarks(kv)
          setPricesLoading(false)
        }
      } catch (error) {
        console.error('Price refresh error:', error)
        setPricesLoading(false)
      }

      // Only schedule next refresh if still visible
      if (mounted && isVisible) {
        // Check market status to determine refresh frequency
        const marketOpen = isMarketOpen()
        const refreshInterval = marketOpen ? 30000 : 3600000 // 30s if market open, 1 hour if closed
        timer = setTimeout(load, refreshInterval)

        console.log(`📊 Price refresh scheduled in ${refreshInterval/1000} seconds (Market ${marketOpen ? 'OPEN' : 'CLOSED'})`)
      }
    }

    load()

    return () => {
      mounted = false
      if (timer) {
        clearTimeout(timer)
        timer = null
      }
    }
  }, [positions, isVisible, loading])

  // Create a map of stock performance data for quick lookup
  const stockPerformanceMap = useMemo(() => {
    if (!portfolioPerformance?.per_stock_performance) return {}
    return portfolioPerformance.per_stock_performance.reduce((acc: any, stock: any) => {
      acc[`${stock.ticker}.${stock.exchange}`] = stock
      return acc
    }, {})
  }, [portfolioPerformance])

  const rows = useMemo(() => Object.values(positions), [positions])

  return (
     <div className="min-h-screen bg-gradient-to-br from-slate-900 via-green-900 to-emerald-900 p-3 sm:p-6">
       <div className="max-w-7xl mx-auto">
         <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/30">
           <div className="flex items-center gap-2 mb-4 sm:mb-6">
             <div className="w-2 h-6 sm:h-8 bg-green-500 rounded-full"></div>
             <h2 className="text-lg sm:text-2xl font-bold text-white">Portfolio Positions</h2>
             {loading && (
               <div className="flex items-center gap-1 text-green-400 text-sm">
                 <div className="w-1 h-1 bg-green-400 rounded-full animate-pulse"></div>
                 <span>Loading positions...</span>
               </div>
             )}
             {refreshing && !loading && (
               <div className="flex items-center gap-1 text-blue-400 text-sm">
                 <div className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"></div>
                 <span>Refreshing positions...</span>
               </div>
             )}
             {pricesLoading && !loading && !refreshing && (
               <div className="flex items-center gap-1 text-purple-400 text-sm">
                 <div className="w-1 h-1 bg-purple-400 rounded-full animate-pulse"></div>
                 <span>Loading live prices...</span>
               </div>
             )}
           </div>

           {/* Portfolio Performance Summary */}
           {portfolioPerformance && (
             <div className="bg-gradient-to-r from-emerald-900/20 to-blue-900/20 backdrop-blur-sm rounded-xl sm:rounded-2xl p-4 sm:p-6 border border-emerald-700/30 mb-6">
               <h3 className="text-lg sm:text-xl font-bold text-white mb-4 flex items-center gap-2">
                 <div className="w-2 h-6 sm:h-8 bg-emerald-500 rounded-full"></div>
                 Portfolio Performance
               </h3>

               <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                 {/* Total Portfolio Value */}
                 <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-700/50">
                   <div className="text-xs sm:text-sm text-gray-400 mb-2">Total Portfolio Value</div>
                   <div className="text-xl sm:text-2xl font-bold text-white">
                     ₹{portfolioPerformance.total_portfolio_value?.toLocaleString('en-IN') || '0'}
                   </div>
                   <div className="text-xs text-emerald-400 mt-1">Current Market Value</div>
                 </div>

                 {/* Total P&L */}
                 <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-700/50">
                   <div className="text-xs sm:text-sm text-gray-400 mb-2">Total P&L</div>
                   <div className={`text-xl sm:text-2xl font-bold ${portfolioPerformance.total_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                     {portfolioPerformance.total_pnl >= 0 ? '+' : ''}₹{portfolioPerformance.total_pnl?.toLocaleString('en-IN') || '0'}
                   </div>
                   <div className="text-xs text-gray-400 mt-1">Realized + Unrealized</div>
                 </div>

                 {/* P&L Breakdown */}
                 <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-700/50">
                   <div className="text-xs sm:text-sm text-gray-400 mb-2">P&L Breakdown</div>
                   <div className="space-y-1">
                     <div className="flex justify-between items-center">
                       <span className="text-xs text-gray-400">Realized:</span>
                       <span className={`text-sm font-semibold ${portfolioPerformance.total_realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                         {portfolioPerformance.total_realized_pnl >= 0 ? '+' : ''}₹{(portfolioPerformance.total_realized_pnl || 0).toLocaleString('en-IN')}
                       </span>
                     </div>
                     <div className="flex justify-between items-center">
                       <span className="text-xs text-gray-400">Unrealized:</span>
                       <span className={`text-sm font-semibold ${portfolioPerformance.total_unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                         {portfolioPerformance.total_unrealized_pnl >= 0 ? '+' : ''}₹{(portfolioPerformance.total_unrealized_pnl || 0).toLocaleString('en-IN')}
                       </span>
                     </div>
                   </div>
                 </div>

                 {/* Trading Performance */}
                 <div className="bg-slate-900/30 rounded-lg p-4 border border-slate-700/50">
                   <div className="text-xs sm:text-sm text-gray-400 mb-2">Trading Performance</div>
                   <div className="space-y-1">
                     <div className="flex justify-between items-center">
                       <span className="text-xs text-gray-400">Orders:</span>
                       <span className="text-sm font-semibold text-purple-400">
                         {portfolioPerformance.total_orders || 0} ({portfolioPerformance.buy_orders || 0}B/{portfolioPerformance.sell_orders || 0}S)
                       </span>
                     </div>
                     <div className="flex justify-between items-center">
                       <span className="text-xs text-gray-400">Win Rate:</span>
                       <span className="text-sm font-semibold text-blue-400">
                         {portfolioPerformance.win_rate?.toFixed(1) || '0'}% ({portfolioPerformance.winning_trades || 0}W/{portfolioPerformance.losing_trades || 0}L)
                       </span>
                     </div>
                   </div>
                 </div>
               </div>

             </div>
           )}


          {loading ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">📊</div>
              <div className="text-xl text-gray-300 mb-2">Loading Portfolio</div>
              <div className="text-sm text-gray-400">Fetching positions from database...</div>
            </div>
          ) : rows.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">📊</div>
              <div className="text-xl text-gray-300 mb-2">No Active Positions</div>
              <div className="text-sm text-gray-400">Your portfolio is currently empty</div>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Desktop: Enhanced Table Header - STICKY */}
              <div className="hidden lg:block sticky top-0 z-10 bg-gradient-to-r from-slate-800/95 to-slate-700/95 backdrop-blur-md rounded-xl p-4 mb-6 border border-slate-600/30 shadow-lg">
                <div className="grid grid-cols-12 gap-4 text-sm font-semibold text-gray-300">
                  <div className="col-span-3">Stock</div>
                  <div className="text-center col-span-2">Position & Value</div>
                  <div className="text-center col-span-2">Price Analysis</div>
                  <div className="text-center col-span-2">P&L Performance</div>
                  <div className="text-center col-span-3">Trading Analytics</div>
                </div>
              </div>

              {rows.map((p: any, index: number) => {
                 const key = `${p.ticker}.${p.exchange}`
                 const priceData = marks[key]
                 const last = priceData === -1 ? p.avgPrice : (priceData ?? p.avgPrice)  // Use avg price as fallback for invalid data
                 const isPriceValid = priceData !== -1 && priceData !== undefined
                 const unreal = isPriceValid ? (last - p.avgPrice) * (p.qty > 0 ? Math.abs(p.qty) : -Math.abs(p.qty)) : 0
                 const percentChange = isPriceValid && p.avgPrice !== 0 ? ((last - p.avgPrice) / p.avgPrice) * 100 : 0

                 // Get performance data for this stock
                 const stockPerf = stockPerformanceMap[key]

                 return (
                   <div
                     key={key}
                     className="bg-white/5 rounded-lg border border-white/10 hover:border-white/20 transition-all duration-300"
                     style={{ animationDelay: `${index * 50}ms` }}
                   >
                     {/* Mobile/Tablet: Card Layout */}
                     <div className="block lg:hidden p-4">
                       <div className="flex items-center justify-between mb-3">
                         <div className="flex items-center gap-3">
                           <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                             <span className="text-white font-bold text-sm">{p.ticker.slice(0, 2)}</span>
                           </div>
                           <div>
                             <div className="font-bold text-white">{p.ticker}</div>
                             <div className="text-xs text-gray-400">{p.exchange === 'NSE' ? 'NSE' : 'BSE'}</div>
                           </div>
                         </div>
                         <div className="text-right">
                           {pricesLoading && !marks[key] ? (
                             <div className="flex flex-col items-end gap-1">
                               <div className="flex items-center gap-2">
                                 <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                                 <span className="text-sm text-gray-400">Loading...</span>
                               </div>
                             </div>
                           ) : !isPriceValid ? (
                             <div className="flex flex-col items-end gap-1">
                               <div className="text-sm text-orange-400">⚠️ Price unavailable</div>
                               <div className="text-xs text-gray-400">Using avg. price</div>
                             </div>
                           ) : (
                             <>
                               <div className={`text-lg font-bold ${unreal >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                 ₹{unreal.toFixed(2)}
                               </div>
                               <div className={`text-xs ${unreal >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                 {percentChange >= 0 ? '+' : ''}{percentChange.toFixed(2)}%
                               </div>
                             </>
                           )}
                         </div>
                       </div>

                       <div className="grid grid-cols-4 gap-2 text-center">
                         <div className="bg-slate-900/30 rounded p-2">
                           <div className="text-xs text-gray-400 mb-1">Qty</div>
                           <div className="text-sm font-semibold text-white">{p.qty}</div>
                         </div>
                         <div className="bg-slate-900/30 rounded p-2">
                           <div className="text-xs text-gray-400 mb-1">Avg</div>
                           <div className="text-sm font-semibold text-blue-400">₹{Number(p.avgPrice).toFixed(0)}</div>
                         </div>
                         <div className="bg-slate-900/30 rounded p-2">
                           <div className="text-xs text-gray-400 mb-1">Current</div>
                           {pricesLoading && !marks[key] ? (
                             <div className="flex items-center justify-center py-1">
                               <div className="w-3 h-3 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
                             </div>
                           ) : (
                             <div className="text-sm font-semibold text-purple-400">₹{Number(last).toFixed(0)}</div>
                           )}
                         </div>
                         <div className="bg-slate-900/30 rounded p-2">
                           <div className="text-xs text-gray-400 mb-1">Value</div>
                           {pricesLoading && !marks[key] ? (
                             <div className="flex items-center justify-center py-1">
                               <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                             </div>
                           ) : (
                             <div className="text-sm font-semibold text-white">₹{(Math.abs(p.qty) * last).toFixed(0)}</div>
                           )}
                         </div>
                       </div>

                       {(stockPerf?.total_orders > 0) && (
                         <div className="mt-3 pt-3 border-t border-slate-700/30">
                           <div className="grid grid-cols-3 gap-2 text-center">
                             <div>
                               <div className="text-xs text-gray-400 mb-1">Realized P&L</div>
                               <div className={`text-sm font-semibold ${stockPerf?.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                 {stockPerf ? (stockPerf.realized_pnl >= 0 ? '+' : '') + '₹' + stockPerf.realized_pnl.toLocaleString('en-IN') : 'N/A'}
                               </div>
                             </div>
                             <div>
                               <div className="text-xs text-gray-400 mb-1">Trades</div>
                               <div className="text-sm font-semibold text-orange-400">
                                 {stockPerf ? stockPerf.total_orders : 'N/A'}
                               </div>
                             </div>
                             <div>
                               <div className="text-xs text-gray-400 mb-1">Win Rate</div>
                               <div className="text-sm font-semibold text-blue-400">
                                 {stockPerf ? `${stockPerf.win_rate}%` : 'N/A'}
                               </div>
                             </div>
                           </div>
                         </div>
                       )}
                     </div>

                     {/* Desktop: Enhanced Table Row Layout */}
                     <div className="hidden lg:block p-4 hover:bg-white/5 transition-colors duration-200 rounded-lg">
                       <div className="grid grid-cols-12 gap-4 items-center">
                         {/* Stock Info */}
                         <div className="col-span-3 flex items-center gap-4">
                           <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center flex-shrink-0 shadow-lg">
                             <span className="text-white font-bold text-base">{p.ticker.slice(0, 2)}</span>
                           </div>
                           <div className="min-w-0">
                             <div className="font-bold text-white text-lg">{p.ticker}</div>
                             <div className="text-sm text-gray-400">{p.exchange === 'NSE' ? 'NSE' : 'BSE'}</div>
                           </div>
                         </div>

                         {/* Position Details & Value */}
                         <div className="col-span-2 text-center space-y-2">
                           <div className="flex justify-center items-center gap-4">
                             <div className="text-center">
                               <div className="text-lg font-bold text-white">{p.qty}</div>
                               <div className="text-sm text-gray-400">shares</div>
                             </div>
                             <div className="w-px h-8 bg-slate-600"></div>
                             <div className="text-center">
                               {pricesLoading && !marks[key] ? (
                                 <div className="flex items-center justify-center py-1">
                                   <div className="w-4 h-4 border-2 border-orange-400 border-t-transparent rounded-full animate-spin"></div>
                                 </div>
                               ) : (
                                 <div className="text-lg font-bold text-orange-400">₹{(Math.abs(p.qty) * last).toFixed(0)}</div>
                               )}
                               <div className="text-sm text-gray-400">value</div>
                             </div>
                           </div>
                           <div className={`inline-flex items-center gap-1 text-xs font-medium px-3 py-1 rounded-full ${
                             p.qty > 0 ? 'bg-green-900/30 text-green-400' :
                             p.qty < 0 ? 'bg-red-900/30 text-red-400' :
                             'bg-gray-900/30 text-gray-400'
                           }`}>
                             {p.qty > 0 ? '📈 Long' : p.qty < 0 ? '📉 Short' : '➖ Closed'}
                           </div>
                         </div>

                         {/* Price Analysis */}
                         <div className="col-span-2 text-center space-y-3">
                           <div className="grid grid-cols-2 gap-3">
                             <div className="bg-slate-800/50 rounded-lg p-2">
                               <div className="text-xs text-gray-400 mb-1">Avg Price</div>
                               <div className="font-bold text-blue-400">₹{Number(p.avgPrice).toFixed(2)}</div>
                             </div>
                             <div className="bg-slate-800/50 rounded-lg p-2">
                               <div className="text-xs text-gray-400 mb-1">Current</div>
                               {pricesLoading && !marks[key] ? (
                                 <div className="flex items-center justify-center py-2">
                                   <div className="w-4 h-4 border-2 border-purple-400 border-t-transparent rounded-full animate-spin"></div>
                                 </div>
                               ) : (
                                 <div className="font-bold text-purple-400">₹{Number(last).toFixed(2)}</div>
                               )}
                             </div>
                           </div>
                           {(pricesLoading && !marks[key]) ? (
                             <div className="inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg bg-gray-900/20 text-gray-400 border border-gray-700/30">
                               <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin"></div>
                               <span>Loading...</span>
                             </div>
                           ) : !isPriceValid ? (
                             <div className="inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg bg-orange-900/20 text-orange-400 border border-orange-700/30">
                               <span className="text-lg">⚠️</span>
                               <span>Price unavailable</span>
                             </div>
                           ) : (
                             <div className={`inline-flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg ${
                               percentChange >= 0
                                 ? 'bg-green-900/20 text-green-400 border border-green-700/30'
                                 : 'bg-red-900/20 text-red-400 border border-red-700/30'
                             }`}>
                               <span className="text-lg">{percentChange >= 0 ? '↗' : '↘'}</span>
                               <span>{Math.abs(percentChange).toFixed(1)}%</span>
                             </div>
                           )}
                         </div>

                         {/* P&L Performance */}
                         <div className="col-span-2 text-center space-y-3">
                           <div className="space-y-2">
                             <div>
                               <div className="text-xs text-gray-400 mb-1">Unrealized P&L</div>
                               {pricesLoading && !marks[key] ? (
                                 <div className="flex items-center justify-center py-2">
                                   <div className="w-5 h-5 border-2 border-green-400 border-t-transparent rounded-full animate-spin"></div>
                                 </div>
                               ) : (
                                 <div className={`text-xl font-bold ${unreal >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                   {unreal >= 0 ? '+' : ''}₹{unreal.toFixed(2)}
                                 </div>
                               )}
                             </div>
                             {stockPerf && (
                               <div>
                                 <div className="text-xs text-gray-400 mb-1">Realized P&L</div>
                                 <div className={`text-lg font-semibold ${stockPerf.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                   {stockPerf.realized_pnl >= 0 ? '+' : ''}₹{stockPerf.realized_pnl.toLocaleString('en-IN')}
                                 </div>
                               </div>
                             )}
                           </div>
                           {pricesLoading && !marks[key] ? (
                             <div className="w-full bg-slate-700/30 rounded-full h-3 flex items-center justify-center">
                               <div className="w-3 h-3 border-2 border-green-400 border-t-transparent rounded-full animate-spin"></div>
                             </div>
                           ) : (
                             <div className="w-full bg-slate-700/50 rounded-full h-3">
                               <div
                                 className={`h-3 rounded-full transition-all duration-300 ${
                                   unreal >= 0 ? 'bg-gradient-to-r from-green-600 to-green-400' : 'bg-gradient-to-r from-red-600 to-red-400'
                                 }`}
                                 style={{ width: `${Math.min(100, Math.abs(unreal) / Math.max(1000, Math.abs(p.avgPrice * Math.abs(p.qty)) * 0.05) * 100)}%` }}
                               ></div>
                             </div>
                           )}
                         </div>

                         {/* Trading Analytics */}
                         <div className="col-span-3 text-center space-y-3">
                           {stockPerf ? (
                             <>
                               <div className="grid grid-cols-3 gap-3">
                                 <div className="bg-slate-800/50 rounded-lg p-3">
                                   <div className="text-lg font-bold text-orange-400">{stockPerf.total_orders}</div>
                                   <div className="text-xs text-gray-400">Total Trades</div>
                                 </div>
                                 <div className="bg-slate-800/50 rounded-lg p-3">
                                   <div className="text-lg font-bold text-blue-400">{stockPerf.win_rate}%</div>
                                   <div className="text-xs text-gray-400">Win Rate</div>
                                 </div>
                                 <div className="bg-slate-800/50 rounded-lg p-3">
                                   <div className="text-lg font-bold text-green-400">{stockPerf.winning_trades}</div>
                                   <div className="text-xs text-gray-400">Wins</div>
                                 </div>
                               </div>
                               <div className="space-y-1">
                                 <div className="flex justify-between text-xs text-gray-400">
                                   <span>Win Rate Progress</span>
                                   <span>{stockPerf.win_rate}%</span>
                                 </div>
                                 <div className="w-full bg-slate-700/50 rounded-full h-2">
                                   <div
                                     className="h-2 bg-gradient-to-r from-blue-500 via-cyan-400 to-green-500 rounded-full transition-all duration-300 shadow-sm"
                                     style={{ width: `${stockPerf.win_rate}%` }}
                                   ></div>
                                 </div>
                               </div>
                             </>
                           ) : (
                             <div className="bg-slate-800/30 rounded-lg p-4">
                               <div className="text-gray-500 text-sm">No trading history yet</div>
                               <div className="text-xs text-gray-600 mt-1">Analytics will appear after first trade</div>
                             </div>
                           )}
                         </div>
                       </div>
                     </div>
                   </div>
                 )
               })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


