"use client"

import { useEffect, useState } from 'react'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE

// ===== MODERN HERO SECTION =====
function HeroSection({ data, isUpdating, marketStatus, onManualRefresh, manualRefresh, clientMarketStatus }: {
  data: any;
  isUpdating: boolean;
  marketStatus?: string;
  onManualRefresh?: () => void;
  manualRefresh?: boolean;
  clientMarketStatus?: string;
}) {
  const [time, setTime] = useState(() => new Date())
  const [isClient, setIsClient] = useState(false)

  useEffect(() => {
    setIsClient(true)
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Show hero section immediately with available data (even if loading)

  return (
    <div className={`relative overflow-hidden bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 rounded-3xl p-8 mb-8 transition-all duration-500 ${isUpdating ? 'ring-2 ring-blue-500/30 shadow-lg shadow-blue-500/10' : ''}`}>
      {/* Animated background elements */}
      <div className="absolute inset-0">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute bottom-0 left-0 w-72 h-72 bg-purple-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>

      {/* Update indicator */}
      {isUpdating && (
        <div className="absolute top-4 right-4 flex items-center gap-2 text-blue-400 text-sm">
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-100"></div>
          <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-200"></div>
          <span className="ml-2">Updating...</span>
        </div>
      )}

      {/* Refresh rate indicator */}
      <div className="absolute top-4 left-4 text-xs text-gray-400">
        {clientMarketStatus === 'OPEN' ? 'Updates: 30s' :
         clientMarketStatus === 'PRE_OPEN' ? 'Updates: 2m' :
         'Loading...'}
      </div>

      <div className="relative z-10 grid lg:grid-cols-3 gap-8 items-center">
        {/* Market Status & Time */}
        <div className="text-center lg:text-left">
          <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full mb-4 ${
            clientMarketStatus === 'OPEN' ? 'bg-green-500/20 text-green-400' :
            clientMarketStatus === 'PRE_OPEN' ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-red-500/20 text-red-400'
          }`}>
            <div className={`w-2 h-2 rounded-full animate-pulse ${
              clientMarketStatus === 'OPEN' ? 'bg-green-400' :
              clientMarketStatus === 'PRE_OPEN' ? 'bg-yellow-400' :
              'bg-red-400'
            }`}></div>
            <span className="text-sm font-medium">
              {clientMarketStatus === 'OPEN' ? 'MARKET OPEN' :
               clientMarketStatus === 'PRE_OPEN' ? 'PRE-MARKET' :
               'MARKET CLOSED'}
            </span>
          </div>
          <div className="text-4xl font-bold text-white mb-2 transition-all duration-300">
            {data?.market_time || (isClient ? time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }) : '00:00')}
          </div>
          <div className="text-gray-300">
            IST • {isClient ? (() => {
              const date = time.toLocaleDateString('en-IN', {
                weekday: 'long',
                day: 'numeric',
                month: 'long',
                year: 'numeric'
              });
              // Convert "Monday 29 September 2025" to "Monday, 29 September 2025"
              return date.replace(/(\w+)\s+(\d+)\s+(\w+)\s+(\d+)/, '$1, $2 $3 $4');
            })() : 'Loading...'}
          </div>
          {clientMarketStatus !== 'OPEN' && (
            <div className="text-sm text-gray-400 mt-2">
              {clientMarketStatus === 'PRE_OPEN' ? 'Opens at 9:15 AM' : 'Closed • Mon-Fri 9:15 AM - 3:30 PM'}
            </div>
          )}
        </div>

        {/* Portfolio Overview */}
        <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-6 border border-white/20 transition-all duration-500 hover:bg-white/15">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-400 rounded-full animate-pulse"></div>
            Portfolio Overview
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-gray-300 mb-1">Total Value</div>
              <div className="text-2xl font-bold text-white">
                ₹<AnimatedNumber value={data?.portfolio_value || 0} />
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-300 mb-1">Today's P&L</div>
              <div className={`text-2xl font-bold transition-colors duration-500 ${
                (data?.portfolio_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                <AnimatedNumber value={data?.portfolio_pnl || 0} />
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-300 mb-1">Cash Available</div>
              <div className="text-xl font-semibold text-gray-200">
                ₹<AnimatedNumber value={data?.cash_balance || 0} />
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-300 mb-1">Active Positions</div>
              <div className="text-xl font-semibold text-gray-200 transition-all duration-300">
                {data?.active_positions || 0}
              </div>
            </div>
          </div>
        </div>

        {/* Market Sentiment */}
        <div className="text-center lg:text-right">
          <div className="inline-flex items-center gap-2 mb-4">
            <span className="text-sm text-gray-300">Market Sentiment:</span>
            <div className={`px-3 py-1 rounded-full text-sm font-medium transition-all duration-500 ${
              (data?.sentiment_score || 0) > 20 ? 'bg-green-500/20 text-green-400' :
              (data?.sentiment_score || 0) < -20 ? 'bg-red-500/20 text-red-400' :
              'bg-yellow-500/20 text-yellow-400'
            }`}>
              {(data?.sentiment_score || 0) > 20 ? 'BULLISH' : (data?.sentiment_score || 0) < -20 ? 'BEARISH' : 'NEUTRAL'}
            </div>
          </div>
          <div className="text-3xl font-bold text-white mb-2 transition-all duration-500">
            <AnimatedNumber value={data?.sentiment_score || 0} />%
          </div>
          <div className="text-gray-300 text-sm">
            AI + Market Analysis
            {data?.sentiment_components && (
              <div className="text-xs text-gray-400 mt-1">
                AI: {data.sentiment_components.ai_sentiment > 0 ? '+' : ''}{data.sentiment_components.ai_sentiment}% •
                Market: {data.sentiment_components.market_sentiment > 0 ? '+' : ''}{data.sentiment_components.market_sentiment}%
                <div className="text-xs text-gray-500 mt-1">
                  💡 60% Market Data + 40% AI Signals
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function HeroSkeleton() {
  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl p-8 mb-8 animate-pulse">
      <div className="grid lg:grid-cols-3 gap-8 items-center">
        <div className="space-y-4">
          <div className="h-8 bg-slate-700 rounded w-32"></div>
          <div className="h-12 bg-slate-700 rounded w-48"></div>
          <div className="h-4 bg-slate-700 rounded w-40"></div>
        </div>
        <div className="space-y-4">
          <div className="h-6 bg-slate-700 rounded w-40"></div>
          <div className="grid grid-cols-2 gap-4">
            <div className="h-16 bg-slate-700 rounded"></div>
            <div className="h-16 bg-slate-700 rounded"></div>
          </div>
        </div>
        <div className="space-y-4 text-right">
          <div className="h-6 bg-slate-700 rounded w-32 ml-auto"></div>
          <div className="h-10 bg-slate-700 rounded w-24 ml-auto"></div>
          <div className="h-4 bg-slate-700 rounded w-28 ml-auto"></div>
        </div>
      </div>
    </div>
  )
}

// ===== MARKET INDICES CARDS =====
function MarketIndices({ indices, lastUpdate, loading }: { indices: any[]; lastUpdate: Date | null; loading?: boolean }) {
   return (
     <div className="mb-8">
       <div className="flex items-center justify-between mb-6">
         <h2 className="text-2xl font-bold text-white flex items-center gap-3">
           <div className="w-2 h-8 bg-blue-500 rounded-full"></div>
           Market Indices
         </h2>
         {lastUpdate && (
           <div className="text-xs text-gray-400">
             Last updated: {lastUpdate.toLocaleTimeString()}
           </div>
         )}
       </div>
       <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
         {loading ? (
           // Loading state for indices
           [1, 2, 3, 4].map((i) => (
             <div key={i} className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
               <div className="animate-pulse space-y-4">
                 <div className="flex items-center justify-between">
                   <div className="h-4 bg-slate-700 rounded w-20"></div>
                   <div className="w-3 h-3 bg-slate-700 rounded-full"></div>
                 </div>
                 <div className="h-8 bg-slate-700 rounded w-24"></div>
                 <div className="flex items-center gap-2">
                   <div className="h-4 bg-slate-700 rounded w-16"></div>
                 </div>
               </div>
             </div>
           ))
         ) : indices?.map((index, idx) => (
          <div
            key={index.name}
            className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50 hover:border-slate-600/50 transition-all duration-500 hover:scale-105 hover:shadow-xl hover:shadow-blue-500/10 group"
            style={{ animationDelay: `${idx * 100}ms` }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-white group-hover:text-blue-300 transition-colors duration-300">{index.name}</h3>
              <div className={`w-3 h-3 rounded-full transition-all duration-500 ${index.changePercent >= 0 ? 'bg-green-400 shadow-lg shadow-green-400/30' : 'bg-red-400 shadow-lg shadow-red-400/30'} animate-pulse`}></div>
            </div>
            <div className="text-3xl font-bold text-white mb-3 group-hover:scale-105 transition-transform duration-300">
              ₹<AnimatedNumber value={index.value} />
            </div>
            <div className={`flex items-center gap-2 transition-all duration-500 ${index.changePercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              <span className="text-lg group-hover:scale-110 transition-transform duration-300">
                {index.changePercent >= 0 ? '↗' : '↘'}
              </span>
              <span className="font-semibold">
                {index.changePercent >= 0 ? '+' : ''}
                <AnimatedNumber value={index.change} />
              </span>
              <span className="group-hover:scale-105 transition-transform duration-300">
                ({index.changePercent.toFixed(2)}%)
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ===== TOP MOVERS SECTION =====
function TopMovers({ gainers, losers, loading }: { gainers: any[]; losers: any[]; loading?: boolean }) {
   return (
     <div className="grid lg:grid-cols-2 gap-8 mb-8">
      {/* Top Gainers */}
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <div className="w-2 h-6 bg-green-500 rounded-full"></div>
          Top Gainers
        </h3>
        <div className="space-y-3">
          {loading ? (
            // Loading state for gainers
            [1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-slate-700 rounded-full animate-pulse"></div>
                  <div className="space-y-2">
                    <div className="h-4 bg-slate-700 rounded w-16 animate-pulse"></div>
                    <div className="h-3 bg-slate-700 rounded w-12 animate-pulse"></div>
                  </div>
                </div>
                <div className="text-right space-y-2">
                  <div className="h-4 bg-slate-700 rounded w-12 animate-pulse"></div>
                  <div className="h-3 bg-slate-700 rounded w-16 animate-pulse"></div>
                </div>
              </div>
            ))
          ) : gainers?.slice(0, 5).map((stock, index) => (
            <div key={stock.ticker} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-xl hover:bg-slate-900/70 transition-all duration-200 hover:scale-[1.02]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-green-500/20 rounded-full flex items-center justify-center text-green-400 font-bold text-sm">
                  {index + 1}
                </div>
                <div>
                  <div className="font-semibold text-white">{stock.ticker}</div>
                  <div className="text-xs text-gray-400">{stock.name}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-bold text-green-400">+{stock.changePercent.toFixed(2)}%</div>
                <div className="text-sm text-gray-400">₹{stock.price.toFixed(2)}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Losers */}
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
        <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
          <div className="w-2 h-6 bg-red-500 rounded-full"></div>
          Top Losers
        </h3>
        <div className="space-y-3">
          {loading ? (
            // Loading state for losers (same structure as gainers)
            [1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-xl">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-slate-700 rounded-full animate-pulse"></div>
                  <div className="space-y-2">
                    <div className="h-4 bg-slate-700 rounded w-16 animate-pulse"></div>
                    <div className="h-3 bg-slate-700 rounded w-12 animate-pulse"></div>
                  </div>
                </div>
                <div className="text-right space-y-2">
                  <div className="h-4 bg-slate-700 rounded w-12 animate-pulse"></div>
                  <div className="h-3 bg-slate-700 rounded w-16 animate-pulse"></div>
                </div>
              </div>
            ))
          ) : losers?.slice(0, 5).map((stock, index) => (
            <div key={stock.ticker} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-xl hover:bg-slate-900/70 transition-all duration-200 hover:scale-[1.02]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-red-500/20 rounded-full flex items-center justify-center text-red-400 font-bold text-sm">
                  {index + 1}
                </div>
                <div>
                  <div className="font-semibold text-white">{stock.ticker}</div>
                  <div className="text-xs text-gray-400">{stock.name}</div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-bold text-red-400">{stock.changePercent.toFixed(2)}%</div>
                <div className="text-sm text-gray-400">₹{stock.price.toFixed(2)}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ===== AI SIGNALS SHOWCASE =====
function AISignalsShowcase({ signals }: { signals: any[] }) {
  return (
    <div className="mb-8">
      <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
        <div className="w-2 h-8 bg-purple-500 rounded-full"></div>
        AI Trading Signals
      </h2>
      <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 backdrop-blur-sm rounded-2xl p-6 border border-purple-700/30">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Recent Signals */}
          <div className="lg:col-span-2">
            <h3 className="text-lg font-semibold text-white mb-4">Recent Signals</h3>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {signals?.slice(0, 4).map((signal, index) => (
                <div key={index} className="bg-slate-900/50 rounded-xl p-4 hover:bg-slate-900/70 transition-all duration-200">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`px-3 py-1 rounded-full text-xs font-bold ${
                        signal.action === 'BUY'
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {signal.action}
                      </div>
                      <div>
                        <div className="font-semibold text-white">{signal.ticker}</div>
                        <div className="text-xs text-gray-400">{signal.strategy} • Entry: ₹{signal.entry}</div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className={`font-bold ${
                        (signal.confidence || 0) > 0.7 ? 'text-green-400' :
                        (signal.confidence || 0) > 0.5 ? 'text-yellow-400' : 'text-red-400'
                      }`}>
                        {(signal.confidence * 100).toFixed(0)}%
                      </div>
                      <div className="text-xs text-gray-400">
                        {new Date(signal.ts).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* AI Performance Stats */}
          <div>
            <h3 className="text-lg font-semibold text-white mb-4">AI Performance</h3>
            <div className="space-y-4">
              <div className="bg-slate-900/50 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-2">Win Rate</div>
                <div className="text-2xl font-bold text-green-400">87.3%</div>
                <div className="text-xs text-gray-400">Last 30 days</div>
              </div>
              <div className="bg-slate-900/50 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-2">Avg Return</div>
                <div className="text-2xl font-bold text-blue-400">+2.4%</div>
                <div className="text-xs text-gray-400">Per trade</div>
              </div>
              <div className="bg-slate-900/50 rounded-xl p-4">
                <div className="text-sm text-gray-400 mb-2">Active Strategies</div>
                <div className="text-2xl font-bold text-purple-400">5</div>
                <div className="text-xs text-gray-400">Running now</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ===== MARKET HEATMAP =====
function MarketHeatmap({ marketStatus, isVisible, shouldLoad }: { marketStatus?: string; isVisible?: boolean; shouldLoad?: boolean }) {
   const [heatmapData, setHeatmapData] = useState<any[]>([])
   const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

   useEffect(() => {
     // Only fetch data if tab is visible, we have API, and shouldLoad is true
     if (!isVisible || !API || !shouldLoad) return

     const fetchHeatmap = async () => {
       try {
         const response = await axios.get(`${API}/home/market-heatmap?limit=25`)
         setHeatmapData(response.data || [])
         setLastUpdate(new Date())
       } catch (error) {
         console.error('Failed to fetch heatmap:', error)
       }
     }

     fetchHeatmap()

     // Intelligent refresh based on market status and visibility
     const getHeatmapInterval = () => {
       if (!isVisible || !shouldLoad) return null
       switch (marketStatus) {
         case 'OPEN':
           return 300000 // 5 minutes when market is open (reduced from 1min)
         case 'PRE_OPEN':
           return 600000 // 10 minutes during pre-market (reduced from 5min)
         case 'CLOSED':
         default:
           return null // No auto-refresh when closed
       }
     }

     const interval = getHeatmapInterval()
     let heatmapInterval: any = null

     if (interval) {
       heatmapInterval = setInterval(() => {
         if (isVisible && shouldLoad) fetchHeatmap()
       }, interval)
     }

     return () => {
       if (heatmapInterval) clearInterval(heatmapInterval)
     }
   }, [marketStatus, isVisible, shouldLoad]) // Depend on market status, visibility, and shouldLoad

  // Group stocks by sector for better organization
  const groupedHeatmap = heatmapData.reduce((acc, stock) => {
    const sector = stock.sector_group || 'Others'
    if (!acc[sector]) acc[sector] = []
    acc[sector].push(stock)
    return acc
  }, {} as Record<string, any[]>)

  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
          <div className="w-2 h-8 bg-orange-500 rounded-full"></div>
          Market Heatmap
          <span className="text-sm text-gray-400 font-normal">
            ({Object.keys(groupedHeatmap).length} sectors • {heatmapData.length} stocks)
          </span>
        </h2>
        {lastUpdate && (
          <div className="text-xs text-gray-400">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        )}
      </div>

      <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
        {Object.keys(groupedHeatmap).length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            Loading market data...
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedHeatmap).map(([sector, stocks]) => (
              <div key={sector} className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-lg">{sector.split(' ')[0]}</span>
                  <span className="text-gray-400 text-xs">{sector.split(' ').slice(1).join(' ')}</span>
                  <span className="text-gray-500">•</span>
                  <span className="text-gray-400 text-xs">{(stocks as any[]).length} stocks</span>
                </div>

                <div className="grid grid-cols-5 md:grid-cols-8 lg:grid-cols-10 gap-2">
                  {(stocks as any[]).map((item: any, index: number) => (
                    <div
                      key={`${item.ticker}-${index}`}
                      className={`aspect-square rounded-lg flex flex-col items-center justify-center text-xs font-bold text-white cursor-pointer transition-all duration-300 hover:scale-110 hover:shadow-lg ${
                        item.performance >= 3 ? 'bg-green-500 hover:bg-green-400' :
                        item.performance >= 1 ? 'bg-green-600/80 hover:bg-green-500/80' :
                        item.performance >= 0 ? 'bg-green-700/60 hover:bg-green-600/60' :
                        item.performance >= -1 ? 'bg-red-700/60 hover:bg-red-600/60' :
                        item.performance >= -3 ? 'bg-red-600/80 hover:bg-red-500/80' :
                        'bg-red-500 hover:bg-red-400'
                      }`}
                      title={`${item.ticker} (${item.sector}): ${item.performance >= 0 ? '+' : ''}${item.performance}% • Price: ₹${item.price} • Vol: ${item.volume.toLocaleString()}`}
                    >
                      <div className="font-bold truncate w-full text-center">{item.ticker}</div>
                      <div className={`text-xs font-medium ${item.performance >= 0 ? 'text-green-100' : 'text-red-100'}`}>
                        {item.performance >= 0 ? '+' : ''}{item.performance}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ===== LIVE NEWS TICKER =====
function LiveNewsTicker({ news }: { news: any[] }) {
  return (
    <div className="mb-8">
      <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
        <div className="w-2 h-8 bg-yellow-500 rounded-full"></div>
        Market News
      </h2>
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
        <div className="space-y-4">
          {news?.map((item) => (
            <div key={item.id} className="flex items-start gap-4 p-4 bg-slate-900/50 rounded-xl hover:bg-slate-900/70 transition-all duration-200">
              <div className={`px-2 py-1 rounded text-xs font-bold ${
                item.sentiment === 'positive' ? 'bg-green-500/20 text-green-400' :
                item.sentiment === 'negative' ? 'bg-red-500/20 text-red-400' :
                'bg-gray-500/20 text-gray-400'
              }`}>
                {item.impact?.toUpperCase()}
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-white mb-1">{item.headline}</h4>
                <div className="flex items-center gap-4 text-sm text-gray-400">
                  <span>{item.source}</span>
                  <span>•</span>
                  <span>{new Date(item.timestamp).toLocaleTimeString()}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ===== QUICK ACTIONS PANEL =====
function QuickActionsPanel() {
  const [isScanning, setIsScanning] = useState(false)

  const runQuickScan = async () => {
    if (!API) return
    setIsScanning(true)
    try {
      await axios.post(`${API}/scanner/run?mode=5m&force=true`)
      // Show success feedback
      setTimeout(() => setIsScanning(false), 2000)
    } catch (error) {
      console.error('Quick scan failed:', error)
      setIsScanning(false)
    }
  }

  const actions = [
    { icon: '🚀', label: 'Quick Scan', color: 'blue', action: runQuickScan, loading: isScanning },
    { icon: '📊', label: 'Analytics', color: 'green', action: () => console.log('Analytics') },
    { icon: '⚙️', label: 'Settings', color: 'purple', action: () => console.log('Settings') },
    { icon: '📈', label: 'Portfolio', color: 'orange', action: () => console.log('Portfolio') },
    { icon: '🎯', label: 'Backtest', color: 'cyan', action: () => console.log('Backtest') },
    { icon: '🤖', label: 'AI Tuner', color: 'indigo', action: () => console.log('AI Tuner') }
  ]

  return (
    <div className="mb-8">
      <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
        <div className="w-2 h-8 bg-indigo-500 rounded-full"></div>
        Quick Actions
      </h2>
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {actions.map((action, index) => (
            <button
              key={index}
              onClick={action.action}
              disabled={action.loading}
              className={`group bg-gradient-to-br from-${action.color}-600 to-${action.color}-700 hover:from-${action.color}-500 hover:to-${action.color}-600 disabled:opacity-50 p-4 rounded-xl transition-all duration-300 hover:scale-105 hover:shadow-lg hover:shadow-${action.color}-500/25`}
            >
              <div className="text-2xl mb-2 group-hover:scale-110 transition-transform duration-200">
                {action.loading ? '⏳' : action.icon}
              </div>
              <div className="text-sm font-medium text-white">{action.label}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}


// ===== ANIMATED NUMBER COMPONENT =====
function AnimatedNumber({ value, duration = 1000, className = "" }: { value: number; duration?: number; className?: string }) {
  const [displayValue, setDisplayValue] = useState(value)
  const [prevValue, setPrevValue] = useState(value)
  const [isAnimating, setIsAnimating] = useState(false)

  useEffect(() => {
    if (value !== prevValue) {
      setIsAnimating(true)
      setPrevValue(value)

      const startValue = displayValue
      const startTime = Date.now()

      const animate = () => {
        const elapsed = Date.now() - startTime
        const progress = Math.min(elapsed / duration, 1)

        // Easing function for smooth animation
        const easeOutQuart = 1 - Math.pow(1 - progress, 4)
        const currentValue = startValue + (value - startValue) * easeOutQuart

        setDisplayValue(currentValue)

        if (progress < 1) {
          requestAnimationFrame(animate)
        } else {
          setIsAnimating(false)
          setDisplayValue(value)
        }
      }

      requestAnimationFrame(animate)
    }
  }, [value, duration, displayValue, prevValue])

  return (
    <span className={`${className} ${isAnimating ? 'animate-pulse' : ''}`}>
      {typeof value === 'number' && value % 1 !== 0
        ? displayValue.toFixed(2)
        : Math.round(displayValue).toLocaleString('en-IN')
      }
    </span>
  )
}

// ===== MAIN MARKETS COMPONENT =====
// State cache for persistence
const marketsStateCache = {
  overviewData: null as any,
  recentSignals: [] as any[],
  lastUpdate: null as Date | null
}

export default function Markets({ isVisible = true }: { isVisible?: boolean }) {
  const [overviewData, setOverviewData] = useState<any>(marketsStateCache.overviewData)
  const [recentSignals, setRecentSignals] = useState<any[]>(marketsStateCache.recentSignals)
  const [news, setNews] = useState<any[]>([])
  const [loading, setLoading] = useState(!marketsStateCache.overviewData)
  const [error, setError] = useState<string | null>(null)
  const [isUpdating, setIsUpdating] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(marketsStateCache.lastUpdate)
  const [signalsLoading, setSignalsLoading] = useState(false)
  const [heatmapLoading, setHeatmapLoading] = useState(false)
  const [heatmapShouldLoad, setHeatmapShouldLoad] = useState(false)
  const [indicesLoaded, setIndicesLoaded] = useState(false)
  const [moversLoaded, setMoversLoaded] = useState(false)
  const [currentMarketStatus, setCurrentMarketStatus] = useState<string>('CLOSED')

  // Market status calculation effect
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date()
      // Calculate market status based on IST time
      const istTime = new Date(now.toLocaleString("en-US", {timeZone: "Asia/Kolkata"}))
      const hour = istTime.getHours()
      const minute = istTime.getMinutes()
      const currentTimeInMinutes = hour * 60 + minute

      // Market hours: 9:15 AM - 3:30 PM IST (Monday-Friday)
      const marketOpenTime = 9 * 60 + 15  // 9:15 AM
      const marketCloseTime = 15 * 60 + 30  // 3:30 PM
      const preMarketStartTime = 8 * 60     // 8:00 AM

      const isWeekday = istTime.getDay() >= 1 && istTime.getDay() <= 5

      let status = 'CLOSED'
      if (isWeekday) {
        if (currentTimeInMinutes >= marketOpenTime && currentTimeInMinutes <= marketCloseTime) {
          status = 'OPEN'
        } else if (currentTimeInMinutes >= preMarketStartTime && currentTimeInMinutes < marketOpenTime) {
          status = 'PRE_OPEN'
        }
      }

      setCurrentMarketStatus(status)
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  // Progressive loading - load essential data first
  useEffect(() => {
    let mounted = true

    const loadMarketStatus = async () => {
      if (!API || !mounted || !isVisible) return

      try {
        // Load market status FIRST (fastest, most critical)
        const overviewRes = await axios.get(`${API}/home/overview`)
        if (!mounted || !isVisible) return

        const data = overviewRes.data
        setOverviewData(data)
        setLastUpdate(new Date())

        // Cache the data for persistence
        marketsStateCache.overviewData = data
        marketsStateCache.lastUpdate = new Date()

        // Set indices as loaded (they come with overview data)
        if (data.indices) {
          setIndicesLoaded(true)
        }

        // Set top movers as loaded (they come with overview data)
        if (data.top_gainers || data.top_losers) {
          setMoversLoaded(true)
        }

        // Load signals SECOND (after market status and indices/movers)
        setSignalsLoading(true)
        const signalsRes = await axios.get(`${API}/home/recent-signals?limit=6`)
        if (mounted) {
          const signals = signalsRes.data || []
          setRecentSignals(signals)
          setSignalsLoading(false)
          marketsStateCache.recentSignals = signals
        }

        // Load heatmap LAST (least critical) - delay by 2 seconds to ensure proper sequence
        setTimeout(() => {
          if (mounted) {
            setHeatmapShouldLoad(true)
            setHeatmapLoading(true)
          }
        }, 2000)

      } catch (err: any) {
        console.error('Failed to load market data:', err)
        if (mounted) {
          setSignalsLoading(false)
          setHeatmapLoading(false)
          setHeatmapShouldLoad(false)
        }
      }
    }

    // Start loading market data immediately with optimized sequence
    loadMarketStatus()

    // Handle visibility changes - if we have cached data and become visible, use it
    if (!mounted) return
    if (isVisible && marketsStateCache.overviewData && !overviewData) {
      setOverviewData(marketsStateCache.overviewData)
      setLastUpdate(marketsStateCache.lastUpdate)
      setLoading(false)
    }

    return () => {
      mounted = false
    }
  }, [isVisible])

  // Separate effect for intelligent polling - only when we have data AND tab is visible
  useEffect(() => {
    if (!overviewData || loading || !isVisible) return

    let mounted = true
    let updateInterval: any = null

    const getRefreshInterval = (marketStatus: string) => {
      switch (marketStatus) {
        case 'OPEN':
          return 120000 // 2 minutes when market is open (reduced from 30s)
        case 'PRE_OPEN':
          return 300000 // 5 minutes during pre-market (reduced from 2min)
        case 'CLOSED':
        default:
          return null // No automatic refresh when closed
      }
    }

    const scheduleNextUpdate = () => {
      const marketStatus = overviewData?.market_status || 'CLOSED'
      const interval = getRefreshInterval(marketStatus)

      if (interval) {
        updateInterval = setTimeout(async () => {
          if (!mounted || !isVisible) return

          try {
            setIsUpdating(true)
            const overviewRes = await axios.get(`${API}/home/overview`)
            if (mounted && isVisible) {
              setOverviewData(overviewRes.data)
              setLastUpdate(new Date())
            }
          } catch (err) {
            console.error('Failed to update data:', err)
          } finally {
            if (mounted && isVisible) {
              setTimeout(() => setIsUpdating(false), 500)
            }
          }

          // Schedule next update only if still visible
          if (mounted && isVisible) {
            scheduleNextUpdate()
          }
        }, interval)
      }
    }

    // Start polling if market is open AND tab is visible
    scheduleNextUpdate()

    return () => {
      mounted = false
      if (updateInterval) clearTimeout(updateInterval)
    }
  }, [overviewData, loading, isVisible])

  // Show layout immediately - no waiting for data

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 text-6xl mb-4">⚠️</div>
          <div className="text-white text-xl mb-4">Unable to Load Trading Dashboard</div>
          <div className="text-gray-300 mb-6">{error}</div>
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg text-white font-medium transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    )
  }

  // Show only hero skeleton while essential data loads - other sections will show loading within their boxes

  return (
     <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 p-6">
       <div className="max-w-7xl mx-auto space-y-6">
         {/* Hero Section - Shows immediately when data is available */}
         <HeroSection
           data={overviewData}
           isUpdating={isUpdating}
           marketStatus={overviewData?.market_status}
           clientMarketStatus={currentMarketStatus}
         />

         {/* Market Indices - Shows with loading state in correct sequence */}
         {overviewData && indicesLoaded ? (
           <MarketIndices indices={overviewData.indices} lastUpdate={lastUpdate} loading={false} />
         ) : overviewData ? (
           <div className="mb-8">
             <div className="flex items-center gap-2 mb-6">
               <div className="w-2 h-8 bg-blue-500 rounded-full"></div>
               <h2 className="text-2xl font-bold text-white">Market Indices</h2>
               <div className="flex items-center gap-1 text-blue-400 text-sm">
                 <div className="w-1 h-1 bg-blue-400 rounded-full animate-pulse"></div>
                 <span>Loading indices...</span>
               </div>
             </div>
           </div>
         ) : null}

         {/* Top Movers - Shows with loading state in correct sequence */}
         {overviewData && moversLoaded ? (
           <TopMovers gainers={overviewData.top_gainers} losers={overviewData.top_losers} loading={false} />
         ) : overviewData && indicesLoaded ? (
           <div className="grid lg:grid-cols-2 gap-8 mb-8">
             <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
               <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                 <div className="w-2 h-6 bg-green-500 rounded-full"></div>
                 Top Gainers
                 <div className="flex items-center gap-1 text-green-400 text-sm">
                   <div className="w-1 h-1 bg-green-400 rounded-full animate-pulse"></div>
                   <span>Loading...</span>
                 </div>
               </h3>
             </div>
             <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
               <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                 <div className="w-2 h-6 bg-red-500 rounded-full"></div>
                 Top Losers
                 <div className="flex items-center gap-1 text-red-400 text-sm">
                   <div className="w-1 h-1 bg-red-400 rounded-full animate-pulse"></div>
                   <span>Loading...</span>
                 </div>
               </h3>
             </div>
           </div>
         ) : null}

         {/* AI Signals Showcase - Shows when signals are loaded */}
         {signalsLoading ? (
           <div className="mb-8">
             <div className="flex items-center gap-2 mb-6">
               <div className="w-2 h-8 bg-purple-500 rounded-full"></div>
               <h2 className="text-2xl font-bold text-white">AI Trading Signals</h2>
               <div className="flex items-center gap-1 text-purple-400 text-sm">
                 <div className="w-1 h-1 bg-purple-400 rounded-full animate-pulse"></div>
                 <span>Loading signals...</span>
               </div>
             </div>
           </div>
         ) : recentSignals.length > 0 && (overviewData && indicesLoaded && moversLoaded) ? (
           <AISignalsShowcase signals={recentSignals} />
         ) : null}

         {/* Market Heatmap - Loads last in sequence */}
         {heatmapShouldLoad ? (
           <MarketHeatmap
             marketStatus={currentMarketStatus}
             isVisible={isVisible}
             shouldLoad={heatmapShouldLoad}
           />
         ) : (overviewData && indicesLoaded && moversLoaded) ? (
           <div className="mb-8">
             <div className="flex items-center gap-2 mb-6">
               <div className="w-2 h-8 bg-orange-500 rounded-full"></div>
               <h2 className="text-2xl font-bold text-white">Market Heatmap</h2>
               <div className="flex items-center gap-1 text-orange-400 text-sm">
                 <div className="w-1 h-1 bg-orange-400 rounded-full animate-pulse"></div>
                 <span>Waiting to load...</span>
               </div>
             </div>
           </div>
         ) : null}

         {/* Quick Actions */}
         <QuickActionsPanel />

         {/* Debug Information */}
         {overviewData?.debug_info && (
           <div className="bg-yellow-900/20 border border-yellow-600/30 rounded-2xl p-4">
             <h3 className="text-yellow-400 font-semibold mb-2">🔧 Debug Information</h3>
             <div className="text-sm text-gray-300 space-y-1">
               <div><strong>Market Status:</strong> <span className={
                 overviewData.market_status === 'OPEN' ? 'text-green-400' :
                 overviewData.market_status === 'PRE_OPEN' ? 'text-yellow-400' :
                 'text-red-400'
               }>{overviewData.market_status}</span></div>
               <div><strong>Refresh Rate:</strong> <span className="text-blue-400">
                 {overviewData.market_status === 'OPEN' ? '30 seconds' :
                  overviewData.market_status === 'PRE_OPEN' ? '2 minutes' :
                  'No auto-refresh'}
               </span></div>
               <div><strong>Data Source:</strong> <span className={overviewData.data_source === 'mock' ? 'text-orange-400' : 'text-green-400'}>{overviewData.data_source}</span></div>
               <div><strong>Market Data:</strong> {overviewData.debug_info}</div>
               {overviewData.sentiment_components && (
                 <div className="mt-2 p-2 bg-slate-800/50 rounded">
                   <div className="text-xs text-gray-300 mb-1"><strong>Sentiment Breakdown:</strong></div>
                   <div className="text-xs space-y-1">
                     <div>🤖 AI Signals: <span className={overviewData.sentiment_components.ai_sentiment > 0 ? 'text-green-400' : 'text-red-400'}>
                       {overviewData.sentiment_components.ai_sentiment > 0 ? '+' : ''}{overviewData.sentiment_components.ai_sentiment}%
                     </span></div>
                     <div>📊 Market Data: <span className={overviewData.sentiment_components.market_sentiment > 0 ? 'text-green-400' : 'text-red-400'}>
                       {overviewData.sentiment_components.market_sentiment > 0 ? '+' : ''}{overviewData.sentiment_components.market_sentiment}%
                     </span></div>
                     <div>🎯 Combined: <span className={(overviewData.sentiment_components.combined_sentiment || 0) > 0 ? 'text-green-400' : 'text-red-400'}>
                       {(overviewData.sentiment_components.combined_sentiment || 0) > 0 ? '+' : ''}{overviewData.sentiment_components.combined_sentiment}%
                     </span></div>
                   </div>
                 </div>
               )}
               {overviewData.data_source === 'mock' && (
                 <div className="mt-2 p-2 bg-orange-900/30 rounded border border-orange-600/30">
                   <div className="text-orange-300 text-xs">
                     💡 <strong>To get real data:</strong><br/>
                     1. Ensure your Supabase database is running<br/>
                     2. Run the database migrations from <code className="bg-black/30 px-1 rounded">db/schema.sql</code><br/>
                     3. Populate the symbols, positions, and signals tables with real data
                   </div>
                 </div>
               )}
             </div>
           </div>
         )}
       </div>
     </div>
   )
}

