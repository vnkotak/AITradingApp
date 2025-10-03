"use client"

import { useState, useEffect } from 'react'
import Markets from '../components/Markets'
import Trading from '../components/Trading'
import Portfolio from '../components/Portfolio'
import History from '../components/History'
import Header from '../components/Header'
import Analytics from '../components/Analytics'
import SignalsTab from '../components/SignalsTab'

const tabs = ["Markets","Trading","Signals","Portfolio","History"] as const

export default function Home() {
  const [activeTab, setActiveTab] = useState<typeof tabs[number]>("Markets")
  const [tabVisibility, setTabVisibility] = useState<Record<string, boolean>>({
    Markets: true,
    Trading: false,
    Signals: false,
    Portfolio: false,
    History: false
  })

  // Update visibility when tab changes
  useEffect(() => {
    const newVisibility = {
      Markets: false,
      Trading: false,
      Signals: false,
      Portfolio: false,
      History: false
    }
    newVisibility[activeTab] = true
    setTabVisibility(newVisibility)
  }, [activeTab])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900">
      {/* Mobile-Responsive Header */}
      <div className="w-full px-2 sm:px-4 py-1 sm:py-1.5">
        <Header />
      </div>

      {/* Mobile-Responsive Navigation */}
      <div className="w-full">
        <div className="relative flex items-center">
          {/* Full-Width Background */}
          <div className="absolute left-0 right-0 h-full bg-slate-800/10 backdrop-blur-sm border-y border-slate-700/10"></div>

          {/* Mobile-First Navigation Content */}
          <div className="relative flex mx-auto w-full max-w-4xl p-1 sm:p-2">
            {/* Mobile: Compact layout, Desktop: Spaced layout */}
            <div className={`flex w-full ${tabs.length <= 3 ? 'justify-center' : 'justify-between md:justify-center'}`}>
              {/* Sliding Background Indicator - Hidden on mobile for simplicity */}
              <div
                className={`absolute top-1 sm:top-2 bottom-1 sm:bottom-2 bg-gradient-to-r from-blue-600/30 to-purple-600/30 rounded-lg border border-blue-500/40 transition-all duration-500 ease-out hidden md:block`}
                style={{
                  width: `${100 / tabs.length}%`,
                  transform: `translateX(${tabs.indexOf(activeTab) * 100}%)`
                }}
              />

              {/* Tab Buttons - Mobile Responsive */}
              {tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`relative z-10 flex-1 md:flex-none px-2 md:px-4 py-2 sm:py-3 text-xs sm:text-sm font-semibold transition-all duration-300 rounded-lg ${
                    activeTab === tab
                      ? 'text-white bg-blue-600/20 md:bg-transparent'
                      : 'text-gray-400 hover:text-white hover:bg-white/5'
                  }`}
                  style={{
                    minWidth: tabs.length > 3 ? '60px' : 'auto',
                    flex: tabs.length <= 3 ? '1' : 'none'
                  }}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Full-Width Pages - Keep all mounted for state persistence */}
      <div style={{ display: activeTab === 'Markets' ? 'block' : 'none' }}>
        <Markets isVisible={tabVisibility.Markets} />
      </div>
      <div style={{ display: activeTab === 'Trading' ? 'block' : 'none' }}>
        <Trading isVisible={tabVisibility.Trading} />
      </div>
      <div style={{ display: activeTab === 'Signals' ? 'block' : 'none' }}>
        <SignalsTab />
      </div>
      <div style={{ display: activeTab === 'Portfolio' ? 'block' : 'none' }}>
        <Portfolio />
      </div>
      <div style={{ display: activeTab === 'History' ? 'block' : 'none' }}>
        <History />
        <Analytics />
      </div>
    </div>
  )
}


