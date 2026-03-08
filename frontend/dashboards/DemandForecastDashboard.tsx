import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { demandForecastApi } from '../../services/api'
import './DashboardCommon.css'

function DemandForecastDashboard() {
  const [forecast, setForecast] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedSku, setSelectedSku] = useState<string>('SKU001')
  const [forecastDays, setForecastDays] = useState<number>(30)

  useEffect(() => {
    loadForecast()
  }, [selectedSku, forecastDays])

  const loadForecast = async () => {
    setLoading(true)
    try {
      const data = await demandForecastApi.getForecast(selectedSku, forecastDays)
      setForecast(data)
    } catch (error) {
      console.error('Failed to load demand forecast:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="dashboard-loading">Loading demand forecast...</div>
  }

  return (
    <div className="dashboard-view">
      <h2>Demand Forecast</h2>

      <div className="filters">
        <input
          type="text"
          value={selectedSku}
          onChange={(e) => setSelectedSku(e.target.value)}
          placeholder="Enter SKU"
          className="filter-input"
        />
        <select
          value={forecastDays}
          onChange={(e) => setForecastDays(Number(e.target.value))}
          className="filter-select"
        >
          <option value={7}>7 Days</option>
          <option value={14}>14 Days</option>
          <option value={30}>30 Days</option>
          <option value={60}>60 Days</option>
          <option value={90}>90 Days</option>
        </select>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-card full-width">
          <h3>Demand Forecast - {selectedSku}</h3>
          <div className="forecast-stats">
            <div className="stat">
              <span className="stat-label">Accuracy</span>
              <span className="stat-value">{forecast?.accuracy || 0}%</span>
            </div>
            <div className="stat">
              <span className="stat-label">Confidence</span>
              <span className="stat-value">{forecast?.confidence || 0}%</span>
            </div>
            <div className="stat">
              <span className="stat-label">Predicted Demand</span>
              <span className="stat-value">{forecast?.totalPredicted || 0} units</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={forecast?.forecastData || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey="actual" stackId="1" stroke="#8884d8" fill="#8884d8" name="Actual" />
              <Area type="monotone" dataKey="predicted" stackId="2" stroke="#82ca9d" fill="#82ca9d" name="Predicted" />
              <Area type="monotone" dataKey="upperBound" stackId="3" stroke="#ffc658" fill="#ffc658" fillOpacity={0.3} name="Upper Bound" />
              <Area type="monotone" dataKey="lowerBound" stackId="3" stroke="#ff8042" fill="#ff8042" fillOpacity={0.3} name="Lower Bound" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="dashboard-card">
          <h3>Regional Forecast</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={forecast?.regionalData || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="region" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="forecast" stroke="#8884d8" name="Forecast" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="dashboard-card">
          <h3>Forecast Insights</h3>
          <div className="insights-list">
            {forecast?.insights?.map((insight: any, index: number) => (
              <div key={index} className="insight-item">
                <span className="insight-icon">{insight.type === 'warning' ? '⚠️' : 'ℹ️'}</span>
                <span className="insight-text">{insight.message}</span>
              </div>
            )) || <p>No insights available</p>}
          </div>
        </div>
      </div>
    </div>
  )
}

export default DemandForecastDashboard
