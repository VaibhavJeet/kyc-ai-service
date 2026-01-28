'use client'

import { cn } from '@/lib/utils'
import { TrendingUp, TrendingDown } from 'lucide-react'

interface StatsCardProps {
  title: string
  value: string
  icon: React.ReactNode
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
  description?: string
}

export function StatsCard({
  title,
  value,
  icon,
  change,
  changeType = 'neutral',
  description,
}: StatsCardProps) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-500">{title}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900">{value}</p>
          {change && (
            <div className="mt-2 flex items-center">
              {changeType === 'positive' && (
                <TrendingUp className="h-4 w-4 text-green-500 mr-1" />
              )}
              {changeType === 'negative' && (
                <TrendingDown className="h-4 w-4 text-red-500 mr-1" />
              )}
              <span
                className={cn(
                  'text-sm font-medium',
                  changeType === 'positive' && 'text-green-600',
                  changeType === 'negative' && 'text-red-600',
                  changeType === 'neutral' && 'text-gray-500'
                )}
              >
                {change}
              </span>
              {description && (
                <span className="text-sm text-gray-500 ml-1">{description}</span>
              )}
            </div>
          )}
        </div>
        <div className="p-3 bg-blue-50 rounded-lg text-blue-600">{icon}</div>
      </div>
    </div>
  )
}
