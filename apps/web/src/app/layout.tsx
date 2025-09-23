import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'AITradingApp',
  description: 'Paper trading app for NSE/BSE',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0b0f15] text-gray-100">{children}</body>
    </html>
  )
}


