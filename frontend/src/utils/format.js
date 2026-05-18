// Currency formatting
export const formatINR = (amount, decimals = 2) => {
  const num = parseFloat(amount || 0)
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(num)
}

export const formatUSDT = (amount, decimals = 4) => {
  const num = parseFloat(amount || 0)
  return `${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: decimals })} USDT`
}

export const formatNumber = (num, decimals = 2) =>
  parseFloat(num || 0).toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })

export const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  })
}

export const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export const formatRelativeTime = (dateStr) => {
  if (!dateStr) return '-'
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return 'Just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export const shortenId = (id) => id ? `${id.slice(0, 8)}...` : '-'

export const getStatusColor = (status) => {
  const map = {
    COMPLETED: 'badge-success',
    FAILED: 'badge-danger',
    PENDING: 'badge-warning',
    REVERSED: 'badge-info',
    REFUNDED: 'badge-info',
    CREDIT: 'badge-success',
    DEBIT: 'badge-danger',
  }
  return map[status?.toUpperCase()] || 'badge-primary'
}

export const getCategoryIcon = (category) => {
  const map = {
    DEPOSIT: '↓',
    WITHDRAWAL: '↑',
    CONVERSION: '⇄',
    PAYMENT: '💳',
    REFUND: '↩',
    FEE: '📊',
    REVERSAL: '↩',
  }
  return map[category] || '•'
}

// Truncate address/ref
export const truncate = (str, len = 16) =>
  str && str.length > len ? `${str.slice(0, len)}...` : str
