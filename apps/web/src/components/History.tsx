"use client"

import { useEffect, useState, useRef } from 'react'
import axios from 'axios'
import { createChart, IChartApi, ISeriesApi, LineData, ColorType } from 'lightweight-charts'

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
    const chartRef = useRef<HTMLDivElement>(null)
    const chartInstance = useRef<IChartApi | null>(null)
    const seriesInstance = useRef<ISeriesApi<'Line'> | null>(null)

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

  // Initialize chart when pnlData is available
  useEffect(() => {
    if (!pnlData.length || !chartRef.current) return

    let chart: IChartApi | null = null
    let lineSeries: ISeriesApi<'Line'> | null = null

    // Clean up previous chart
    if (chartInstance.current) {
      try {
        chartInstance.current.remove()
      } catch (e) {
        // Chart might already be disposed, ignore error
      }
      chartInstance.current = null
      seriesInstance.current = null
    }

    try {
      // Create new chart
      chart = createChart(chartRef.current, {
        layout: {
          background: { type: ColorType.Solid, color: 'transparent' },
          textColor: '#9CA3AF',
        },
        grid: {
          vertLines: { color: '#374151' },
          horzLines: { color: '#374151' },
      },
        width: chartRef.current.clientWidth,
        height: 250,
        timeScale: {
          timeVisible: true,
          secondsVisible: false,
        },
        rightPriceScale: {
          scaleMargins: {
            top: 0.1,
            bottom: 0.1,
          },
        },
        crosshair: {
          mode: 1, // CrosshairMode.Normal
        },
      })

      // Create line series
      lineSeries = chart.addLineSeries({
        color: '#10b981',
        lineWidth: 2,
        priceFormat: {
          type: 'price',
          precision: 0,
          minMove: 1,
        },
      })

      // Convert pnlData to chart format
      const chartData: LineData[] = pnlData.map((point: any, index: number) => ({
        time: (Date.now() - (pnlData.length - 1 - index) * 24 * 60 * 60 * 1000) / 1000 as any,
        value: point.equity,
      }))

      lineSeries.setData(chartData)

      // Fit content
      chart.timeScale().fitContent()

      chartInstance.current = chart
      seriesInstance.current = lineSeries
    } catch (error) {
      console.error('Failed to create chart:', error)
      return
    }

    // Handle resize
    const handleResize = () => {
      if (chartRef.current && chart && !chartInstance.current) {
        try {
          chart.applyOptions({ width: chartRef.current.clientWidth })
        } catch (e) {
          // Chart might be disposed, ignore
        }
      }
    }

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      if (chart) {
        try {
          chart.remove()
        } catch (e) {
          // Chart might already be disposed, ignore
        }
      }
      chartInstance.current = null
      seriesInstance.current = null
    }
  }, [pnlData])

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
               {/* Interactive Equity Curve Chart */}
               <div className="bg-slate-900/30 rounded-lg p-4">
                 <h3 className="text-lg font-semibold text-white mb-4">Portfolio Equity Curve</h3>
                 <div className="w-full">
                   <div ref={chartRef} className="w-full h-64" />
                 </div>
                 <div className="text-xs text-gray-400 mt-2 text-center">
                   Hover over the chart to see exact values • Equity curve showing portfolio value over time (90 days)
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


