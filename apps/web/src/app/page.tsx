"use client"

import { useState } from 'react'
import Markets from '../components/Markets'
import Trading from '../components/Trading'
import Portfolio from '../components/Portfolio'
import History from '../components/History'
import Header from '../components/Header'
import Analytics from '../components/Analytics'
import SignalsTab from '../components/SignalsTab'

const tabs = ["Markets","Trading","Signals","Portfolio","History"] as const

export default function Home() {
  const [tab, setTab] = useState<typeof tabs[number]>("Markets")
  return (
    <div className="p-3">
      <Header />
      <div className="flex items-center gap-2 mb-3">
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)} className={`px-3 py-2 rounded-md ${tab===t? 'bg-accent text-white':'bg-surface text-gray-400'}`}>{t}</button>
        ))}
      </div>
      {tab === 'Markets' && <Markets />}
      {tab === 'Trading' && <Trading />}
      {tab === 'Signals' && <SignalsTab />}
      {tab === 'Portfolio' && <Portfolio />}
      {tab === 'History' && <><History /><Analytics /></>}
    </div>
  )
}


