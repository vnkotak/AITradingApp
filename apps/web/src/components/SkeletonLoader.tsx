import React from 'react'

interface SkeletonProps {
  className?: string
  animate?: boolean
}

export function Skeleton({ className = "", animate = true }: SkeletonProps) {
  return (
    <div
      className={`bg-gradient-to-r from-slate-700 via-slate-600 to-slate-700 rounded-md ${
        animate ? 'animate-pulse' : ''
      } ${className}`}
    />
  )
}

export function ShimmerSkeleton({ className = "" }: SkeletonProps) {
  return (
    <div className={`relative overflow-hidden bg-slate-700 rounded-md ${className}`}>
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer" />
    </div>
  )
}

// Section-specific skeleton loaders
export function HeroSkeleton() {
  return (
    <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-3xl p-8 mb-8 animate-pulse">
      <div className="grid lg:grid-cols-3 gap-8 items-center">
        <div className="space-y-4">
          <ShimmerSkeleton className="h-8 w-32 rounded-full" />
          <ShimmerSkeleton className="h-12 w-48" />
          <ShimmerSkeleton className="h-4 w-40" />
        </div>
        <div className="space-y-4">
          <ShimmerSkeleton className="h-6 w-40" />
          <div className="grid grid-cols-2 gap-4">
            <ShimmerSkeleton className="h-16 rounded-xl" />
            <ShimmerSkeleton className="h-16 rounded-xl" />
          </div>
        </div>
        <div className="space-y-4 text-right">
          <ShimmerSkeleton className="h-6 w-32 ml-auto" />
          <ShimmerSkeleton className="h-10 w-24 ml-auto" />
          <ShimmerSkeleton className="h-4 w-28 ml-auto" />
        </div>
      </div>
    </div>
  )
}

export function IndicesSkeleton() {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-6">
        <ShimmerSkeleton className="w-2 h-8 rounded-full" />
        <ShimmerSkeleton className="h-6 w-40" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-slate-800/50 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/50">
            <div className="animate-pulse space-y-4">
              <div className="flex items-center justify-between">
                <ShimmerSkeleton className="h-4 w-20" />
                <ShimmerSkeleton className="w-3 h-3 rounded-full" />
              </div>
              <ShimmerSkeleton className="h-8 w-24" />
              <div className="flex items-center gap-2">
                <ShimmerSkeleton className="h-4 w-16" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function TopMoversSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
      {/* Top Gainers */}
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
        <div className="flex items-center gap-2 mb-4">
          <ShimmerSkeleton className="w-2 h-6 rounded-full" />
          <ShimmerSkeleton className="h-6 w-32" />
        </div>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-xl">
              <div className="flex items-center gap-3">
                <ShimmerSkeleton className="w-8 h-8 rounded-full" />
                <div className="space-y-2">
                  <ShimmerSkeleton className="h-4 w-16" />
                  <ShimmerSkeleton className="h-3 w-12" />
                </div>
              </div>
              <div className="text-right space-y-2">
                <ShimmerSkeleton className="h-4 w-12" />
                <ShimmerSkeleton className="h-3 w-16" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Losers */}
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
        <div className="flex items-center gap-2 mb-4">
          <ShimmerSkeleton className="w-2 h-6 rounded-full" />
          <ShimmerSkeleton className="h-6 w-32" />
        </div>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center justify-between p-3 bg-slate-900/50 rounded-xl">
              <div className="flex items-center gap-3">
                <ShimmerSkeleton className="w-8 h-8 rounded-full" />
                <div className="space-y-2">
                  <ShimmerSkeleton className="h-4 w-16" />
                  <ShimmerSkeleton className="h-3 w-12" />
                </div>
              </div>
              <div className="text-right space-y-2">
                <ShimmerSkeleton className="h-4 w-12" />
                <ShimmerSkeleton className="h-3 w-16" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function SignalsSkeleton() {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-6">
        <ShimmerSkeleton className="w-2 h-8 rounded-full" />
        <ShimmerSkeleton className="h-6 w-48" />
      </div>
      <div className="bg-gradient-to-r from-purple-900/20 to-blue-900/20 backdrop-blur-sm rounded-2xl p-6 border border-purple-700/30">
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <ShimmerSkeleton className="h-6 w-32 mb-4" />
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="bg-slate-900/50 rounded-xl p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <ShimmerSkeleton className="h-6 w-12 rounded-full" />
                      <div>
                        <ShimmerSkeleton className="h-4 w-16 mb-1" />
                        <ShimmerSkeleton className="h-3 w-24" />
                      </div>
                    </div>
                    <div className="text-right">
                      <ShimmerSkeleton className="h-4 w-12 mb-1" />
                      <ShimmerSkeleton className="h-3 w-16" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div>
            <ShimmerSkeleton className="h-6 w-32 mb-4" />
            <div className="space-y-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <ShimmerSkeleton key={i} className="h-16 rounded-xl" />
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function HeatmapSkeleton() {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-6">
        <ShimmerSkeleton className="w-2 h-8 rounded-full" />
        <ShimmerSkeleton className="h-6 w-40" />
      </div>
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
        <div className="text-center py-12">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <ShimmerSkeleton className="h-4 w-48 mx-auto" />
        </div>
      </div>
    </div>
  )
}

export function ActionsSkeleton() {
  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-6">
        <ShimmerSkeleton className="w-2 h-8 rounded-full" />
        <ShimmerSkeleton className="h-6 w-32" />
      </div>
      <div className="bg-slate-800/30 backdrop-blur-sm rounded-2xl p-6 border border-slate-700/30">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <ShimmerSkeleton key={i} className="h-16 rounded-xl" />
          ))}
        </div>
      </div>
    </div>
  )
}