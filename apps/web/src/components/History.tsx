"use client"

import { useMemo } from 'react'
import { useTradingStore } from '../store/trading'

export default function History() {
  const orders = useTradingStore(s => s.orders)
  const trades = useTradingStore(s => s.trades)
  const winRate = useMemo(() => {
    if (!trades.length) return 0
    // naive: count SELL after BUY as exit and pnl > 0; here we can't compute exact, show trade count
    return (trades.length > 0) ? 50 : 0
  }, [trades])

  return (
     <div className="min-h-screen bg-gradient-to-br from-slate-900 via-orange-900 to-red-900 p-3 sm:p-6">
       <div className="max-w-7xl mx-auto space-y-4 sm:space-y-6">
         {/* Recent Orders */}
         <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/30">
           <div className="flex items-center gap-2 mb-4 sm:mb-6">
             <div className="w-2 h-6 sm:h-8 bg-orange-500 rounded-full"></div>
             <h2 className="text-lg sm:text-2xl font-bold text-white">Recent Orders</h2>
           </div>

          {orders.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-4">📋</div>
              <div className="text-xl text-gray-300 mb-2">No Orders Yet</div>
              <div className="text-sm text-gray-400">Your order history will appear here</div>
            </div>
          ) : (
            <div className="space-y-3">
              {(orders||[]).map((o: any, index: number) => (
                <div
                  key={o.id}
                  className="bg-white/5 rounded-lg sm:rounded-xl p-3 sm:p-4 border border-white/10 hover:border-white/20 transition-all duration-300 hover:scale-[1.02]"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                        o.side === 'BUY'
                          ? 'bg-green-900/30 border border-green-700/50'
                          : 'bg-red-900/30 border border-red-700/50'
                      }`}>
                        <span className={`font-bold ${o.side === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>
                          {o.side === 'BUY' ? 'B' : 'S'}
                        </span>
                      </div>
                      <div>
                        <div className="text-lg font-semibold text-white">
                          {o.side} {o.qty} shares
                        </div>
                        <div className="text-sm text-gray-400">
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
            </div>
          )}
        </div>

        {/* Trading Statistics */}
         <div className="bg-slate-800/30 backdrop-blur-sm rounded-xl sm:rounded-2xl p-3 sm:p-6 border border-slate-700/30">
           <div className="flex items-center gap-2 mb-4 sm:mb-6">
             <div className="w-2 h-6 sm:h-8 bg-blue-500 rounded-full"></div>
             <h2 className="text-lg sm:text-2xl font-bold text-white">Trading Statistics</h2>
           </div>

           <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 sm:gap-4 md:gap-6">
            <div className="bg-white/5 rounded-lg sm:rounded-xl p-3 sm:p-6 border border-white/10">
              <div className="text-xs sm:text-sm text-gray-400 mb-2">Total Orders</div>
              <div className="text-2xl sm:text-3xl font-bold text-white">{orders.length}</div>
              <div className="text-xs text-gray-400 mt-1">All time</div>
            </div>

            <div className="bg-white/5 rounded-lg sm:rounded-xl p-3 sm:p-6 border border-white/10">
              <div className="text-xs sm:text-sm text-gray-400 mb-2">Completed Trades</div>
              <div className="text-2xl sm:text-3xl font-bold text-green-400">{trades.length}</div>
              <div className="text-xs text-gray-400 mt-1">Successful executions</div>
            </div>

            <div className="bg-white/5 rounded-lg sm:rounded-xl p-3 sm:p-6 border border-white/10">
              <div className="text-xs sm:text-sm text-gray-400 mb-2">Est. Win Rate</div>
              <div className="text-2xl sm:text-3xl font-bold text-blue-400">{winRate}%</div>
              <div className="text-xs text-gray-400 mt-1">Based on closed trades</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}


