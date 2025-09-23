"use client"

import { useEffect, useState } from 'react'
import axios from 'axios'

const API = process.env.NEXT_PUBLIC_API_BASE

export default function PauseToggle() {
  const [paused, setPaused] = useState<boolean>(false)
  const [loading, setLoading] = useState<boolean>(false)

  const fetchState = async () => {
    try {
      const res = await axios.get(`${API}/risk/limits`)
      setPaused(!!res.data.pause_all)
    } catch {}
  }
  useEffect(() => { fetchState() }, [])

  const toggle = async () => {
    setLoading(true)
    try {
      // Update in Supabase via backend (simple direct update route could be added; for now assume service role env allows temporary direct call or extend API later)
      await axios.post(`${API}/risk/pause`, { pause_all: !paused })
      setPaused(!paused)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <button onClick={toggle} disabled={loading} className={`px-3 py-2 rounded ${paused? 'bg-red-700':'bg-green-700'}`}>
      {paused? 'Resume Trading':'Pause All'}
    </button>
  )
}


