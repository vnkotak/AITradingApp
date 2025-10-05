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
    const [portfolioPerformance, setPortfolioPerformance] = useState<any>(null)
    const [pnlData, setPnlData] = useState<any[]>([])
    const portfolioRefreshTrigger = useTradingStore(s => s.portfolioRefreshTrigger)

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
            if (pos.ticker && pos.exchange && pos.qty !== 0) { // Only load non-zero positions
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
      const ad = await getMarketAdapter()
      const kv: Record<string, number> = {}
      for (const key of Object.keys(positions)) {
        const p = positions[key]
        kv[key] = await ad.getLastPrice(p.ticker, p.exchange)
      }
      if (mounted) setMarks(kv)
      timer = setTimeout(load, 10000)
    }
    load()
    return () => { mounted = false; if (timer) clearTimeout(timer) }
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
            <div className="space-y-4">
              {rows.map((p: any, index: number) => {
                 const key = `${p.ticker}.${p.exchange}`
                 const last = marks[key] ?? p.avgPrice
                 const unreal = (last - p.avgPrice) * (p.qty > 0 ? Math.abs(p.qty) : -Math.abs(p.qty))
                 const percentChange = p.avgPrice !== 0 ? ((last - p.avgPrice) / p.avgPrice) * 100 : 0

                 // Get performance data for this stock
                 const stockPerf = stockPerformanceMap[key]

                 return (
                   <div
                     key={key}
                     className="bg-white/5 rounded-lg sm:rounded-xl p-3 sm:p-6 border border-white/10 hover:border-white/20 transition-all duration-300 hover:scale-[1.02]"
                     style={{ animationDelay: `${index * 100}ms` }}
                   >
                     <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mb-3 sm:mb-4 gap-3 sm:gap-0">
                       <div className="flex items-center gap-3 sm:gap-4">
                         <div className="w-10 h-10 sm:w-12 sm:h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg sm:rounded-xl flex items-center justify-center flex-shrink-0">
                           <span className="text-white font-bold text-sm sm:text-base">{p.ticker.slice(0, 2)}</span>
                         </div>
                         <div className="min-w-0">
                           <div className="text-lg sm:text-xl font-bold text-white truncate">{p.ticker}</div>
                           <div className="text-xs sm:text-sm text-gray-400 truncate">{p.exchange === 'NSE' ? 'National Stock Exchange' : 'Bombay Stock Exchange'}</div>
                         </div>
                       </div>
                       <div className="text-center sm:text-right">
                         <div className={`text-xl sm:text-2xl font-bold ${unreal >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                           ₹{unreal.toFixed(2)}
                         </div>
                         <div className={`text-xs sm:text-sm ${unreal >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                           {percentChange >= 0 ? '+' : ''}{percentChange.toFixed(2)}%
                         </div>
                       </div>
                     </div>

                     <div className="grid grid-cols-2 md:grid-cols-7 gap-2 sm:gap-3 md:gap-4">
                       <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                         <div className="text-xs text-gray-400 mb-1">Quantity</div>
                         <div className="text-sm sm:text-lg font-semibold text-white">{p.qty}</div>
                       </div>
                       <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                         <div className="text-xs text-gray-400 mb-1">Avg Price</div>
                         <div className="text-sm sm:text-lg font-semibold text-blue-400">₹{Number(p.avgPrice).toFixed(2)}</div>
                       </div>
                       <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                         <div className="text-xs text-gray-400 mb-1">Current Price</div>
                         <div className="text-sm sm:text-lg font-semibold text-purple-400">₹{Number(last).toFixed(2)}</div>
                       </div>
                       <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                         <div className="text-xs text-gray-400 mb-1">Position Value</div>
                         <div className="text-sm sm:text-lg font-semibold text-white">₹{(Math.abs(p.qty) * last).toFixed(2)}</div>
                       </div>
                       <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                         <div className="text-xs text-gray-400 mb-1">Realized P&L</div>
                         <div className={`text-sm sm:text-lg font-semibold ${stockPerf?.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                           {stockPerf ? (stockPerf.realized_pnl >= 0 ? '+' : '') + '₹' + stockPerf.realized_pnl.toLocaleString('en-IN') : 'N/A'}
                         </div>
                       </div>
                       <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                         <div className="text-xs text-gray-400 mb-1">Trades</div>
                         <div className="text-sm sm:text-lg font-semibold text-orange-400">
                           {stockPerf ? stockPerf.total_orders : 'N/A'}
                         </div>
                         <div className="text-xs text-gray-500">
                           {stockPerf ? `${stockPerf.completed_trades}C/${stockPerf.total_orders}T` : ''}
                         </div>
                       </div>
                       <div className="bg-slate-900/30 rounded-lg p-2 sm:p-3">
                         <div className="text-xs text-gray-400 mb-1">Win Rate</div>
                         <div className="text-sm sm:text-lg font-semibold text-blue-400">
                           {stockPerf ? `${stockPerf.win_rate}%` : 'N/A'}
                         </div>
                         <div className="text-xs text-gray-500">
                           {stockPerf ? `${stockPerf.winning_trades}W/${stockPerf.completed_trades}T` : ''}
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


