'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

const data = [
  { date: 'Jan 1', successful: 120, failed: 8, pending: 12 },
  { date: 'Jan 2', successful: 145, failed: 12, pending: 8 },
  { date: 'Jan 3', successful: 132, failed: 6, pending: 15 },
  { date: 'Jan 4', successful: 168, failed: 10, pending: 20 },
  { date: 'Jan 5', successful: 155, failed: 8, pending: 12 },
  { date: 'Jan 6', successful: 140, failed: 5, pending: 10 },
  { date: 'Jan 7', successful: 178, failed: 15, pending: 18 },
]

export function VerificationChart() {
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
          />
          <YAxis tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="successful"
            stroke="#22c55e"
            strokeWidth={2}
            dot={{ fill: '#22c55e', r: 4 }}
            name="Successful"
          />
          <Line
            type="monotone"
            dataKey="failed"
            stroke="#ef4444"
            strokeWidth={2}
            dot={{ fill: '#ef4444', r: 4 }}
            name="Failed"
          />
          <Line
            type="monotone"
            dataKey="pending"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={{ fill: '#f59e0b', r: 4 }}
            name="Pending"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
