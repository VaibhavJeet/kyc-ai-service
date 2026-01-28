'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Shield,
  Users,
  Building2,
  Webhook,
  Settings,
  FileText,
  AlertTriangle,
  Key,
  BarChart3,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Verifications', href: '/verifications', icon: Shield },
  { name: 'Trust Scores', href: '/trust-scores', icon: BarChart3 },
  { name: 'Business Verify', href: '/business', icon: Building2 },
  { name: 'Scam Reports', href: '/scam-reports', icon: AlertTriangle },
  { name: 'Webhooks', href: '/webhooks', icon: Webhook },
  { name: 'API Keys', href: '/api-keys', icon: Key },
  { name: 'Audit Logs', href: '/audit-logs', icon: FileText },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="hidden lg:flex lg:flex-shrink-0">
      <div className="flex flex-col w-64">
        <div className="flex flex-col flex-grow bg-gray-900 pt-5 pb-4 overflow-y-auto">
          {/* Logo */}
          <div className="flex items-center flex-shrink-0 px-4">
            <Shield className="h-8 w-8 text-blue-500" />
            <span className="ml-2 text-xl font-bold text-white">TrustVault</span>
          </div>

          {/* Navigation */}
          <nav className="mt-8 flex-1 px-2 space-y-1">
            {navigation.map((item) => {
              const isActive = pathname === item.href
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'group flex items-center px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                    isActive
                      ? 'bg-gray-800 text-white'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  )}
                >
                  <item.icon
                    className={cn(
                      'mr-3 h-5 w-5 flex-shrink-0',
                      isActive ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-300'
                    )}
                  />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* User section */}
          <div className="flex-shrink-0 flex border-t border-gray-800 p-4">
            <div className="flex items-center">
              <div className="h-9 w-9 rounded-full bg-gray-700 flex items-center justify-center">
                <Users className="h-5 w-5 text-gray-300" />
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-white">Admin User</p>
                <p className="text-xs text-gray-400">admin@company.com</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
