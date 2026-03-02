import { get, post } from 'aws-amplify/api'
import { fetchAuthSession } from 'aws-amplify/auth'

const API_NAME = 'RetailMindAPI'

export interface ApiResponse<T> {
  data: T
  error?: string
}

/**
 * Get authentication token for API requests
 */
async function getAuthToken(): Promise<string> {
  const session = await fetchAuthSession()
  return session.tokens?.idToken?.toString() || ''
}

/**
 * Market Intelligence API
 */
export const marketIntelligenceApi = {
  async getTrends(region?: string, category?: string) {
    const restOperation = get({
      apiName: API_NAME,
      path: '/market-intelligence/trends',
      options: {
        queryParams: { region, category },
      },
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async getCompetitorAnalysis(productId: string) {
    const restOperation = get({
      apiName: API_NAME,
      path: `/market-intelligence/competitor/${productId}`,
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async getDemandHeatmap() {
    const restOperation = get({
      apiName: API_NAME,
      path: '/market-intelligence/demand-heatmap',
    })
    const response = await restOperation.response
    return await response.body.json()
  },
}

/**
 * Demand Forecast API
 */
export const demandForecastApi = {
  async getForecast(sku: string, days: number = 30) {
    const restOperation = get({
      apiName: API_NAME,
      path: `/demand-forecast/${sku}`,
      options: {
        queryParams: { days: days.toString() },
      },
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async getRegionalForecast(region: string) {
    const restOperation = get({
      apiName: API_NAME,
      path: `/demand-forecast/region/${region}`,
    })
    const response = await restOperation.response
    return await response.body.json()
  },
}

/**
 * Pricing Optimization API
 */
export const pricingApi = {
  async getRecommendations(productId: string) {
    const restOperation = get({
      apiName: API_NAME,
      path: `/pricing/recommendations/${productId}`,
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async simulatePrice(productId: string, newPrice: number) {
    const restOperation = post({
      apiName: API_NAME,
      path: '/pricing/simulate',
      options: {
        body: { productId, newPrice },
      },
    })
    const response = await restOperation.response
    return await response.body.json()
  },
}

/**
 * Inventory Planning API
 */
export const inventoryApi = {
  async getOptimization() {
    const restOperation = get({
      apiName: API_NAME,
      path: '/inventory/optimization',
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async getStockAlerts() {
    const restOperation = get({
      apiName: API_NAME,
      path: '/inventory/alerts',
    })
    const response = await restOperation.response
    return await response.body.json()
  },
}

/**
 * Risk & Compliance API
 */
export const riskComplianceApi = {
  async getAlerts() {
    const restOperation = get({
      apiName: API_NAME,
      path: '/risk-compliance/alerts',
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async getSupplierRisk(supplierId: string) {
    const restOperation = get({
      apiName: API_NAME,
      path: `/risk-compliance/supplier/${supplierId}`,
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async uploadDocument(file: File) {
    const formData = new FormData()
    formData.append('document', file)
    
    const restOperation = post({
      apiName: API_NAME,
      path: '/risk-compliance/document',
      options: {
        body: formData,
      },
    })
    const response = await restOperation.response
    return await response.body.json()
  },
}

/**
 * Business Copilot API
 */
export const copilotApi = {
  async sendQuery(query: string, context?: any) {
    const restOperation = post({
      apiName: API_NAME,
      path: '/copilot/query',
      options: {
        body: { query, context },
      },
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async getHistory(limit: number = 50) {
    const restOperation = get({
      apiName: API_NAME,
      path: '/copilot/history',
      options: {
        queryParams: { limit: limit.toString() },
      },
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async provideFeedback(messageId: string, rating: number, comment?: string) {
    const restOperation = post({
      apiName: API_NAME,
      path: '/copilot/feedback',
      options: {
        body: { messageId, rating, comment },
      },
    })
    const response = await restOperation.response
    return await response.body.json()
  },
}

/**
 * Alerts and Notifications API
 */
export const alertsApi = {
  async getAll() {
    const restOperation = get({
      apiName: API_NAME,
      path: '/alerts',
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async markAsRead(alertId: string) {
    const restOperation = post({
      apiName: API_NAME,
      path: `/alerts/${alertId}/read`,
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async getEscalations() {
    const restOperation = get({
      apiName: API_NAME,
      path: '/alerts/escalations',
    })
    const response = await restOperation.response
    return await response.body.json()
  },

  async respondToEscalation(escalationId: string, decision: string, notes?: string) {
    const restOperation = post({
      apiName: API_NAME,
      path: `/alerts/escalations/${escalationId}/respond`,
      options: {
        body: { decision, notes },
      },
    })
    const response = await restOperation.response
    return await response.body.json()
  },
}
