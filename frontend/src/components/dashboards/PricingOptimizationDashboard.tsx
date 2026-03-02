import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter } from 'recharts'
import { pricingApi } from '../../services/api'
import './DashboardCommon.css'

function PricingOptimizationDashboard() {
  const [recommendations, setRecommendations] = useState<any>(null)
  const [simulation, setSimulation] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedProduct, setSelectedProduct] = useState<string>('PROD001')
  const [simulatedPrice, setSimulatedPrice] = useState<string>('')

  useEffect(() => {
    loadRecommendations()
  }, [selectedProduct])

  const loadRecommendations = async () => {
    setLoading(true)
    try {
      const data = await pricingApi.getRecommendations(selectedProduct)
      setRecommendations(data)
    } catch (error) {
      console.error('Failed to load pricing recommendations:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSimulate = async () => {
    if (!simulatedPrice) return
    try {
      const result = await pricingApi.simulatePrice(selectedProduct, Number(simulatedPrice))
      setSimulation(result)
    } catch (error) {
      console.error('Failed to simulate price:', error)
    }
  }

  if (loading) {
    return <div className="dashboard-loading">Loading pricing optimization...</div>
  }

  return (
    <div className="dashboard-view">
      <h2>Pricing Optimization</h2>

      <div className="filters">
        <input
          type="text"
          value={selectedProduct}
          onChange={(e) => setSelectedProduct(e.target.value)}
          placeholder="Enter Product ID"
          className="filter-input"
        />
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>Current Pricing</h3>
          <div className="pricing-summary">
            <div className="price-item">
              <span className="label">Current Price</span>
              <span className="value">₹{recommendations?.currentPrice || 0}</span>
            </div>
            <div className="price-item">
              <span className="label">Recommended Price</span>
              <span className="value recommended">₹{recommendations?.recommendedPrice || 0}</span>
            </div>
            <div className="price-item">
              <span className="label">Expected Margin</span>
              <span className="value">{recommendations?.expectedMargin || 0}%</span>
            </div>
            <div className="price-item">
              <span className="label">Competitor Avg</span>
              <span className="value">₹{recommendations?.competitorAvg || 0}</span>
            </div>
          </div>
        </div>

        <div className="dashboard-card">
          <h3>Price Elasticity</h3>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="price" name="Price" />
              <YAxis dataKey="demand" name="Demand" />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} />
              <Legend />
              <Scatter name="Price vs Demand" data={recommendations?.elasticityData || []} fill="#8884d8" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>

        <div className="dashboard-card">
          <h3>Price Simulation</h3>
          <div className="simulation-controls">
            <input
              type="number"
              value={simulatedPrice}
              onChange={(e) => setSimulatedPrice(e.target.value)}
              placeholder="Enter price to simulate"
              className="filter-input"
            />
            <button onClick={handleSimulate} className="simulate-button">
              Simulate
            </button>
          </div>
          {simulation && (
            <div className="simulation-results">
              <div className="result-item">
                <span>Expected Demand:</span>
                <span>{simulation.expectedDemand} units</span>
              </div>
              <div className="result-item">
                <span>Expected Revenue:</span>
                <span>₹{simulation.expectedRevenue}</span>
              </div>
              <div className="result-item">
                <span>Expected Margin:</span>
                <span>{simulation.expectedMargin}%</span>
              </div>
              <div className="result-item">
                <span>Impact:</span>
                <span style={{ color: simulation.impact > 0 ? 'green' : 'red' }}>
                  {simulation.impact > 0 ? '+' : ''}{simulation.impact}%
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="dashboard-card">
          <h3>Pricing History</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={recommendations?.priceHistory || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="price" stroke="#8884d8" name="Price" />
              <Line type="monotone" dataKey="margin" stroke="#82ca9d" name="Margin %" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

export default PricingOptimizationDashboard
