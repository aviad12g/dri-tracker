/**
 * Utility functions for DRI Tracker frontend.
 */

import { clsx, type ClassValue } from 'clsx'

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs)
}

export function formatNumber(value: number, decimals: number = 0): string {
  if (value >= 1000000) {
    return (value / 1000000).toFixed(1) + 'M'
  }
  if (value >= 1000) {
    return (value / 1000).toFixed(1) + 'K'
  }
  return value.toFixed(decimals)
}

export function formatPercent(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

export function formatDRI(value: number): string {
  return value.toFixed(2)
}

export function getChangeColor(value: number): string {
  if (value > 0) return 'text-accent-success'
  if (value < 0) return 'text-accent-danger'
  return 'text-terminal-muted'
}

export function getQualityClass(quality: string): string {
  switch (quality) {
    case 'verified':
      return 'quality-verified'
    case 'partial':
      return 'quality-partial'
    case 'estimated':
      return 'quality-estimated'
    default:
      return 'quality-partial'
  }
}

export function getTierColor(tier: string): string {
  switch (tier) {
    case 'mega':
      return '#00d4aa'
    case 'core':
      return '#6366f1'
    case 'prop':
      return '#f59e0b'
    case 'control':
      return '#6b7280'
    default:
      return '#a1a1aa'
  }
}

export function getTierLabel(tier: string): string {
  switch (tier) {
    case 'mega':
      return 'Mega'
    case 'core':
      return 'Core'
    case 'prop':
      return 'Propagandist'
    case 'control':
      return 'Control'
    default:
      return tier
  }
}

export function getPlatformColor(platform: string): string {
  switch (platform) {
    case 'tiktok':
      return '#ff0050'
    case 'youtube':
    case 'youtube_short':
      return '#ff0000'
    case 'x':
      return '#1d9bf0'
    case 'instagram':
    case 'reels':
      return '#e1306c'
    case 'telegram':
      return '#0088cc'
    case 'rumble':
      return '#85c742'
    case 'cozy':
      return '#8b5cf6'
    default:
      return '#a1a1aa'
  }
}

export function getPlatformLabel(platform: string): string {
  switch (platform) {
    case 'youtube_short':
      return 'YT Shorts'
    case 'x':
      return 'X'
    case 'reels':
      return 'Reels'
    default:
      return platform.charAt(0).toUpperCase() + platform.slice(1)
  }
}

export function getScoreColor(type: string): string {
  switch (type) {
    case 'v':
      return '#06b6d4' // cyan
    case 'r':
      return '#f97316' // orange
    case 's':
      return '#a855f7' // purple
    case 'p':
      return '#eab308' // yellow
    default:
      return '#00d4aa' // primary
  }
}

export function getScoreLabel(type: string): string {
  switch (type) {
    case 'v':
      return 'Virality'
    case 'r':
      return 'Radicalization'
    case 's':
      return 'Search'
    case 'p':
      return 'Political'
    default:
      return type.toUpperCase()
  }
}


