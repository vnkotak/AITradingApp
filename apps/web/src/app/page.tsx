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
      {/* Full-Width Header - Compact */}
      <div className="w-full px-4 py-1.5">
        <Header />
      </div>

      {/* Full-Width Navigation - End to End */}
      <div className="w-full">
        <div className="relative flex items-center">
          {/* Full-Width Background */}
          <div className="absolute left-0 right-0 h-full bg-slate-800/10 backdrop-blur-sm border-y border-slate-700/10"></div>

          {/* Centered Navigation Content */}
          <div className="relative flex mx-auto max-w-4xl w-full p-2">
            {/* Sliding Background Indicator */}
            <div
              className="absolute top-2 bottom-2 bg-gradient-to-r from-blue-600/30 to-purple-600/30 rounded-lg border border-blue-500/40 transition-all duration-500 ease-out"
              style={{
                width: `${100 / tabs.length}%`,
                transform: `translateX(${tabs.indexOf(activeTab) * 100}%)`
              }}
            />

            {/* Tab Buttons */}
            {tabs.map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`relative z-10 flex-1 px-4 py-3 text-sm font-semibold transition-all duration-300 rounded-lg ${
                  activeTab === tab
                    ? 'text-white'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                {tab}
              </button>
            ))}
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


