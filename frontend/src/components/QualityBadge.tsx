'use client'

import { cn, getQualityClass } from '@/lib/utils'
import {
  CheckCircleIcon,
  ExclamationCircleIcon,
  QuestionMarkCircleIcon,
} from '@heroicons/react/24/solid'

interface QualityBadgeProps {
  quality: string
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export function QualityBadge({ quality, showLabel = true, size = 'md' }: QualityBadgeProps) {
  const Icon = quality === 'verified'
    ? CheckCircleIcon
    : quality === 'partial'
      ? ExclamationCircleIcon
      : QuestionMarkCircleIcon

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-2.5 py-1',
    lg: 'text-base px-3 py-1.5',
  }

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5',
  }

  const labels = {
    verified: 'Verified',
    partial: 'Partial',
    estimated: 'Estimated',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        sizeClasses[size],
        getQualityClass(quality)
      )}
    >
      <Icon className={iconSizes[size]} />
      {showLabel && <span>{labels[quality as keyof typeof labels] || quality}</span>}
    </span>
  )
}


