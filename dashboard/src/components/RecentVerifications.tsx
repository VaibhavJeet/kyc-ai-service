'use client'

import { CheckCircle, XCircle, Clock, Eye } from 'lucide-react'
import { cn } from '@/lib/utils'

const verifications = [
  {
    id: 'VRF-001234',
    type: 'KYC',
    status: 'verified',
    trustScore: 92,
    timestamp: '2 mins ago',
    documentType: 'Aadhaar',
  },
  {
    id: 'VRF-001233',
    type: 'Face',
    status: 'verified',
    trustScore: 88,
    timestamp: '5 mins ago',
    documentType: 'PAN',
  },
  {
    id: 'VRF-001232',
    type: 'KYC',
    status: 'manual_review',
    trustScore: 62,
    timestamp: '8 mins ago',
    documentType: 'Passport',
  },
  {
    id: 'VRF-001231',
    type: 'Liveness',
    status: 'failed',
    trustScore: 35,
    timestamp: '12 mins ago',
    documentType: 'Aadhaar',
  },
  {
    id: 'VRF-001230',
    type: 'Business',
    status: 'verified',
    trustScore: 95,
    timestamp: '15 mins ago',
    documentType: 'GSTIN',
  },
]

const statusConfig = {
  verified: {
    icon: CheckCircle,
    color: 'text-green-600',
    bg: 'bg-green-50',
    label: 'Verified',
  },
  failed: {
    icon: XCircle,
    color: 'text-red-600',
    bg: 'bg-red-50',
    label: 'Failed',
  },
  manual_review: {
    icon: Clock,
    color: 'text-yellow-600',
    bg: 'bg-yellow-50',
    label: 'Review',
  },
}

export function RecentVerifications() {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead>
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              ID
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Document
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Trust Score
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Status
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Time
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {verifications.map((v) => {
            const status = statusConfig[v.status as keyof typeof statusConfig]
            const StatusIcon = status.icon

            return (
              <tr key={v.id} className="hover:bg-gray-50">
                <td className="px-4 py-4 whitespace-nowrap">
                  <span className="text-sm font-mono text-gray-900">{v.id}</span>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <span className="px-2 py-1 text-xs font-medium bg-blue-50 text-blue-700 rounded">
                    {v.type}
                  </span>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-600">
                  {v.documentType}
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <div className="w-16 bg-gray-200 rounded-full h-2 mr-2">
                      <div
                        className={cn(
                          'h-2 rounded-full',
                          v.trustScore >= 85 && 'bg-green-500',
                          v.trustScore >= 50 && v.trustScore < 85 && 'bg-yellow-500',
                          v.trustScore < 50 && 'bg-red-500'
                        )}
                        style={{ width: `${v.trustScore}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium text-gray-700">{v.trustScore}</span>
                  </div>
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <span
                    className={cn(
                      'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                      status.bg,
                      status.color
                    )}
                  >
                    <StatusIcon className="w-3 h-3 mr-1" />
                    {status.label}
                  </span>
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                  {v.timestamp}
                </td>
                <td className="px-4 py-4 whitespace-nowrap">
                  <button className="text-blue-600 hover:text-blue-800">
                    <Eye className="h-4 w-4" />
                  </button>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
