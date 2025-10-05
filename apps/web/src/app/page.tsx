"use client"

import { useState, useEffect } from 'react'
import Markets from '../components/Markets'
import Trading from '../components/Trading'
import Portfolio from '../components/Portfolio'
import History from '../components/History'
import Header from '../components/Header'
import SignalsTab from '../components/SignalsTab'
import { ThemeProvider } from '../components/ThemeProvider'

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
  }, [activeTab]);

  return (
    <ThemeProvider>
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 dark:from-gray-900 dark:via-blue-900 dark:to-indigo-900">
      {/* Mobile-Responsive Header */}
      <div className="w-full px-2 sm:px-4 py-1 sm:py-1.5">
        <Header />
      </div>

      {/* Mobile-Responsive Navigation */}
      <div className="w-full">
        <div className="relative flex items-center min-h-[48px] sm:min-h-[56px]">
          {/* Full-Width Background */}
          <div className="absolute left-0 right-0 h-full bg-slate-800/10 backdrop-blur-sm border-y border-slate-700/10"></div>

          {/* Navigation Content */}
          <div className="relative flex mx-auto w-full max-w-5xl px-2 sm:px-4">
            {/* Mobile: Compact Centered Layout */}
            <div className="flex w-full justify-center items-center gap-1 sm:gap-2 md:hidden">
              {tabs.map((tab, index) => {
                const isActive = activeTab === tab;
                return (
                  <div key={tab} className="relative">
                    <button
                      onClick={() => setActiveTab(tab)}
                      className={`relative z-10 px-1 sm:px-2 py-2 text-xs font-semibold transition-all duration-300 rounded-lg ${
                        isActive ? 'text-white' : 'text-gray-400 hover:text-white'
                      }`}
                      style={{ minWidth: '50px' }}
                    >
                      {tab}
                    </button>
                    {isActive && (
                      <div className="absolute inset-0 bg-gradient-to-r from-blue-600/30 to-purple-600/30 rounded-lg border border-blue-500/40"></div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Desktop: Spacious Centered Layout */}
            <div className="hidden md:flex w-full justify-center items-center gap-4 lg:gap-6">
              {tabs.map((tab, index) => {
                const isActive = activeTab === tab;
                return (
                  <div key={tab} className="relative">
                    <button
                      onClick={() => setActiveTab(tab)}
                      className={`relative z-10 px-4 lg:px-6 py-3 text-sm lg:text-base font-semibold transition-all duration-300 rounded-lg ${
                        isActive ? 'text-white' : 'text-gray-400 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      {tab}
                    </button>
                    {isActive && (
                      <div className="absolute inset-0 bg-gradient-to-r from-blue-600/30 to-purple-600/30 rounded-lg border border-blue-500/40"></div>
                    )}
                  </div>
                );
              })}
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
        <SignalsTab isVisible={tabVisibility.Signals} />
      </div>
      <div style={{ display: activeTab === 'Portfolio' ? 'block' : 'none' }}>
        <Portfolio isVisible={tabVisibility.Portfolio} />
      </div>
      <div style={{ display: activeTab === 'History' ? 'block' : 'none' }}>
        <History isVisible={tabVisibility.History} />
      </div>
    </div>
  </ThemeProvider>
  )
}


