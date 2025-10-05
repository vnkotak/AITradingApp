"use client"

import { useEffect, useState } from 'react'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE

export default function History({ isVisible = true }: { isVisible?: boolean }) {
   const [dbOrders, setDbOrders] = useState<any[]>([])
   const [symbols, setSymbols] = useState<Record<string, any>>({})
   const [portfolioPerformance, setPortfolioPerformance] = useState<any>(null)
   const [pnlData, setPnlData] = useState<any[]>([])
   const [loading, setLoading] = useState(true)
   const [loadingMore, setLoadingMore] = useState(false)
   const [hasMoreOrders, setHasMoreOrders] = useState(true)
   const [ordersOffset, setOrdersOffset] = useState(0)

  // Load initial data from database (only when tab is visible)
  useEffect(() => {
    if (!isVisible) return

    const loadInitialData = async () => {
      try {
        if (!API) return

        console.log('History: Loading initial data from database...')

        // Load symbols for ticker information
        const symbolsResponse = await axios.get(`${API}/symbols`)
        const symbolsData = symbolsResponse.data || []
        const symbolsMap = symbolsData.reduce((acc: any, symbol: any) => {
          acc[symbol.id] = symbol
          return acc
        }, {})
        setSymbols(symbolsMap)

        // Load portfolio performance data
        const performanceResponse = await axios.get(`${API}/portfolio/performance`)
        const performanceData = performanceResponse.data || null
        setPortfolioPerformance(performanceData)

        // Load P&L data for chart
        const pnlResponse = await axios.get(`${API}/pnl/summary?range_days=90`)
        const pnlChartData = pnlResponse.data?.equity || []
        setPnlData(pnlChartData)

        console.log(`History: Loaded symbols and analytics data`)
      } catch (error) {
        console.error('History: Failed to load initial data from database:', error)
      }
    }

    loadInitialData()
  }, [API, isVisible])

  // Load initial orders (only when tab is visible and symbols are loaded)
  useEffect(() => {
    if (!isVisible || Object.keys(symbols).length === 0) return

    const loadInitialOrders = async () => {
      try {
        if (!API) return

        console.log('History: Loading initial 10 orders...')
        const ordersResponse = await axios.get(`${API}/orders?limit=10&offset=0`)
        const ordersData = ordersResponse.data || []

        // Transform database format to component format
        const transformedOrders = ordersData.map((order: any) => ({
          ...order,
          ts: new Date(order.ts).getTime(), // Convert to timestamp
          status: order.status || 'FILLED'
        }))

        setDbOrders(transformedOrders)
        setOrdersOffset(10)
        setHasMoreOrders(ordersData.length === 10) // If we got 10, there might be more
        console.log(`History: Loaded ${transformedOrders.length} initial orders`)
      } catch (error) {
        console.error('History: Failed to load initial orders:', error)
        setDbOrders([])
      } finally {
        setLoading(false)
      }
    }

    loadInitialOrders()
  }, [API, symbols, isVisible])

  // Function to load more orders
  const loadMoreOrders = async () => {
    if (loadingMore || !hasMoreOrders) return

    setLoadingMore(true)
    try {
      console.log(`History: Loading more orders from offset ${ordersOffset}...`)
      const ordersResponse = await axios.get(`${API}/orders?limit=10&offset=${ordersOffset}`)
      const ordersData = ordersResponse.data || []

      // Transform database format to component format
      const transformedOrders = ordersData.map((order: any) => ({
        ...order,
        ts: new Date(order.ts).getTime(), // Convert to timestamp
        status: order.status || 'FILLED'
      }))

      setDbOrders(prev => [...prev, ...transformedOrders])
      setOrdersOffset(prev => prev + 10)
      setHasMoreOrders(ordersData.length === 10) // If we got 10, there might be more
      console.log(`History: Loaded ${transformedOrders.length} more orders`)
    } catch (error) {
      console.error('History: Failed to load more orders:', error)
    } finally {
      setLoadingMore(false)
    }
  }

  // Use database orders
  const orders = dbOrders

  // Calculate statistics from real data
  const totalOrdersCount = loading ? 0 : orders.length
  const realWinRate = portfolioPerformance?.win_rate || 0
  const completedTrades = portfolioPerformance?.completed_trades || 0
  const winningTrades = portfolioPerformance?.winning_trades || 0
  const losingTrades = portfolioPerformance?.losing_trades || 0

  return (
     <div className="min-h-screen bg-gradient-to-br from-slate-900 via-orange-900 to-red-900 p-3 sm:p-6">
       <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
         {/* P&L Analytics */}
         {pnlData.length > 0 && (
           <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/30">
             <div className="flex items-center gap-2 mb-4 sm:mb-6">
               <div className="w-2 h-6 sm:h-8 bg-emerald-500 rounded-full"></div>
               <h2 className="text-lg sm:text-2xl font-bold text-white">P&L Analytics</h2>
             </div>

             <div className="space-y-4">
               {/* Simple Equity Curve Chart */}
               <div className="bg-slate-900/30 rounded-lg p-4">
                 <h3 className="text-lg font-semibold text-white mb-4">Portfolio Equity Curve</h3>
                 <div className="h-64 w-full">
                   <svg viewBox="0 0 400 200" className="w-full h-full">
                     {/* Grid lines */}
                     <defs>
                       <pattern id="grid" width="40" height="20" patternUnits="userSpaceOnUse">
                         <path d="M 40 0 L 0 0 0 20" fill="none" stroke="#374151" strokeWidth="0.5"/>
                       </pattern>
                     </defs>
                     <rect width="100%" height="100%" fill="url(#grid)" />

                     {/* Equity curve line */}
                     {pnlData.length > 1 && (
                       <path
                         fill="none"
                         stroke="#10b981"
                         strokeWidth="2"
                         d={
                           (() => {
                             const vals = pnlData.map((p: any) => p.equity)
                             const min = Math.min(...vals)
                             const max = Math.max(...vals)
                             const pad = 10
                             const x = (i: number) => pad + (i / (pnlData.length - 1)) * (380 - pad*2)
                             const y = (v: number) => pad + (1 - (v - min) / (max - min || 1)) * (180 - pad*2)
                             return pnlData.map((p, i) => `${i===0? 'M':'L'} ${x(i)} ${y(p.equity)}`).join(' ')
                           })()
                         }
                       />
                     )}

                     {/* X and Y axis labels with actual values */}
                     {pnlData.length > 1 && (() => {
                       const vals = pnlData.map((p: any) => p.equity)
                       const min = Math.min(...vals)
                       const max = Math.max(...vals)
                       const range = max - min
                       const interval = Math.max(5000, Math.round(range / 5 / 1000) * 1000) // Round to nearest 1000

                       // Generate Y-axis labels
                       const yLabels = []
                       for (let val = Math.ceil(min / interval) * interval; val <= max; val += interval) {
                         yLabels.push(val)
                       }

                       // Generate X-axis date labels (assuming 90 days back)
                       const now = new Date()
                       const startDate = new Date(now.getTime() - (pnlData.length - 1) * 24 * 60 * 60 * 1000)
                       const dateLabels = []

                       // Only show 1st of each month and last date
                       for (let i = 0; i < pnlData.length; i++) {
                         const currentDate = new Date(startDate.getTime() + i * 24 * 60 * 60 * 1000)
                         const day = currentDate.getDate()
                         const month = currentDate.getMonth()

                         if (day === 1 || i === pnlData.length - 1) {
                           const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                           dateLabels.push({
                             index: i,
                             label: day === 1 ? `${monthNames[month]}` : `${day} ${monthNames[month]}`
                           })
                         }
                       }

                       return (
                         <>
                           {/* Y-axis labels (Equity values) */}
                           {yLabels.map((val, idx) => {
                             const yPos = 185 - ((val - min) / (max - min)) * 170
                             return (
                               <text key={idx} x="8" y={yPos + 3} textAnchor="end" className="text-[9px] fill-gray-400 font-medium" transform={`rotate(-90, 8, ${yPos + 3})`}>
                                 ₹{val.toLocaleString('en-IN')}
                               </text>
                             )
                           })}

                           {/* X-axis labels (Dates) */}
                           {dateLabels.map((dateLabel, idx) => {
                             const xPos = 10 + (dateLabel.index / (pnlData.length - 1)) * 380
                             return (
                               <text key={idx} x={xPos} y="193" textAnchor="middle" className="text-[9px] fill-gray-400 font-medium">
                                 {dateLabel.label}
                               </text>
                             )
                           })}
                         </>
                       )
                     })()}
                   </svg>
                 </div>
                 <div className="text-xs text-gray-400 mt-2 text-center">
                   Equity curve showing portfolio value over time (90 days)
                 </div>
               </div>

               {/* P&L Statistics */}
               <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                 <div className="bg-slate-900/30 rounded-lg p-4">
                   <div className="text-sm text-gray-400 mb-1">Starting Equity</div>
                   <div className="text-xl font-bold text-white">
                     ₹{pnlData[0]?.equity?.toLocaleString('en-IN') || '0'}
                   </div>
                 </div>
                 <div className="bg-slate-900/30 rounded-lg p-4">
                   <div className="text-sm text-gray-400 mb-1">Current Equity</div>
                   <div className="text-xl font-bold text-white">
                     ₹{pnlData[pnlData.length - 1]?.equity?.toLocaleString('en-IN') || '0'}
                   </div>
                 </div>
                 <div className="bg-slate-900/30 rounded-lg p-4">
                   <div className="text-sm text-gray-400 mb-1">Total Return</div>
                   <div className={`text-xl font-bold ${
                     pnlData.length > 1 && pnlData[pnlData.length - 1]?.equity > pnlData[0]?.equity
                       ? 'text-green-400' : 'text-red-400'
                   }`}>
                     {pnlData.length > 1 ?
                       (((pnlData[pnlData.length - 1].equity - pnlData[0].equity) / pnlData[0].equity) * 100).toFixed(2) + '%'
                       : '0.00%'
                     }
                   </div>
                 </div>
               </div>
             </div>
           </div>
         )}

         {/* Recent Orders */}
         <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/30">
           <div className="flex items-center gap-2 mb-4 sm:mb-6">
             <div className="w-2 h-6 sm:h-8 bg-orange-500 rounded-full"></div>
             <h2 className="text-lg sm:text-2xl font-bold text-white">Recent Orders</h2>
           </div>

          {loading ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">⏳</div>
              <div className="text-xl text-gray-300 mb-2">Loading Orders...</div>
              <div className="text-sm text-gray-400">Fetching order history from database</div>
            </div>
          ) : orders.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">📋</div>
              <div className="text-xl text-gray-300 mb-2">No Orders Yet</div>
              <div className="text-sm text-gray-400">Your order history will appear here</div>
            </div>
          ) : (
            <div
              className="space-y-3 max-h-96 overflow-y-auto"
              onScroll={(e) => {
                const target = e.target as HTMLDivElement;
                const bottom = target.scrollHeight - target.scrollTop === target.clientHeight;
                if (bottom && hasMoreOrders && !loadingMore) {
                  loadMoreOrders();
                }
              }}
            >
              {(orders||[]).map((o: any, index: number) => (
                <div
                  key={o.id}
                  className={`${
                    o.side === 'BUY'
                      ? 'bg-green-900/20 border-green-700/30'
                      : 'bg-red-900/20 border-red-700/30'
                  } rounded-lg sm:rounded-xl p-3 sm:p-4 border hover:border-white/20 transition-all duration-300 hover:scale-[1.02]`}
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-4 h-12 rounded-full ${
                        o.side === 'BUY' ? 'bg-green-500' : 'bg-red-500'
                      }`}></div>
                      <div>
                        <div className="text-xl font-bold text-white">
                          {o.ticker && o.exchange ? `${o.ticker}.${o.exchange}` : 'Unknown Stock'}
                        </div>
                        <div className="text-sm text-gray-400">
                          {o.qty} shares @ ₹{Number(o.price).toFixed(2)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {new Date(o.ts).toLocaleString()}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xl font-bold text-white">₹{Number(o.price).toFixed(2)}</div>
                      <div className={`text-sm px-3 py-1 rounded-lg inline-block ${
                        o.status === 'COMPLETE'
                          ? 'bg-green-900/30 text-green-400'
                          : o.status === 'PENDING'
                          ? 'bg-yellow-900/30 text-yellow-400'
                          : 'bg-red-900/30 text-red-400'
                      }`}>
                        {o.status}
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Loading more indicator */}
              {loadingMore && (
                <div className="text-center py-4">
                  <div className="inline-flex items-center gap-2 text-blue-400">
                    <div className="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
                    <span>Loading more orders...</span>
                  </div>
                </div>
              )}

              {/* Load more button as fallback */}
              {hasMoreOrders && !loadingMore && (
                <div className="text-center pt-4">
                  <button
                    onClick={loadMoreOrders}
                    className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
                  >
                    Load More Orders
                  </button>
                </div>
              )}
            </div>
          )}
        </div>


     </div>
   </div>
 )
}


