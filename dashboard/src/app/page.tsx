'use client'

import { useState, useEffect } from 'react'
import {
  Shield,
  Users,
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  AlertTriangle,
  Activity
} from 'lucide-react'
import { StatsCard } from '@/components/StatsCard'
import { VerificationChart } from '@/components/VerificationChart'
import { RecentVerifications } from '@/components/RecentVerifications'
import { TrustScoreDistribution } from '@/components/TrustScoreDistribution'

export default function Dashboard() {
  const [stats, setStats] = useState({
    totalVerifications: 12453,
    successRate: 94.2,
    avgTrustScore: 78.5,
    pendingReviews: 23,
    todayVerifications: 156,
    monthlyGrowth: 12.5,
  })

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">Welcome to TrustVault - Your verification overview</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatsCard
          title="Total Verifications"
          value={stats.totalVerifications.toLocaleString()}
          icon={<Shield className="h-6 w-6" />}
          change="+12.5%"
          changeType="positive"
        />
        <StatsCard
          title="Success Rate"
          value={`${stats.successRate}%`}
          icon={<CheckCircle className="h-6 w-6" />}
          change="+2.1%"
          changeType="positive"
        />
        <StatsCard
          title="Avg Trust Score"
          value={stats.avgTrustScore.toString()}
          icon={<TrendingUp className="h-6 w-6" />}
          change="+3.2"
          changeType="positive"
        />
        <StatsCard
          title="Pending Reviews"
          value={stats.pendingReviews.toString()}
          icon={<Clock className="h-6 w-6" />}
          change="-5"
          changeType="positive"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Verification Trends</h2>
          <VerificationChart />
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Trust Score Distribution</h2>
          <TrustScoreDistribution />
        </div>
      </div>

      {/* Recent Verifications */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Verifications</h2>
        <RecentVerifications />
      </div>
    </div>
  )
}
