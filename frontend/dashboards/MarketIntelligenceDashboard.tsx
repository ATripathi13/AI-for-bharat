import { useState, useEffect } from 'react'
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { marketIntelligenceApi } from '../../services/api'
import './DashboardCommon.css'

function MarketIntelligenceDashboard() {
  const [trends, setTrends] = useState<any>(null)
  const [demandHeatmap, setDemandHeatmap] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedRegion, setSelectedRegion] = useState<string>('all')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')

  useEffect(() => {
    loadData()
  }, [selectedRegion, selectedCategory])

  const loadData = async () => {
    setLoading(true)
    try {
      const [trendsData, heatmapData] = await Promise.all([
        marketIntelligenceApi.getTrends(
          selectedRegion !== 'all' ? selectedRegion : undefined,
          selectedCategory !== 'all' ? selectedCategory : undefined
        ),
        marketIntelligenceApi.getDemandHeatmap(),
      ])
      setTrends(trendsData)
      setDemandHeatmap(heatmapData)
    } catch (error) {
      console.error('Failed to load market intelligence data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="dashboard-loading">Loading market intelligence...</div>
  }

  return (
    <div className="dashboard-view">
      <h2>Market Intelligence</h2>
      
      <div className="filters">
        <select 
          value={selectedRegion} 
          onChange={(e) => setSelectedRegion(e.target.value)}
          className="filter-select"
        >
          <option value="all">All Regions</option>
          <option value="north">North</option>
          <option value="south">South</option>
          <option value="east">East</option>
          <option value="west">West</option>
        </select>

        <select 
          value={selectedCategory} 
          onChange={(e) => setSelectedCategory(e.target.value)}
          className="filter-select"
        >
          <option value="all">All Categories</option>
          <option value="electronics">Electronics</option>
          <option value="fashion">Fashion</option>
          <option value="grocery">Grocery</option>
          <option value="home">Home & Living</option>
        </select>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>Pricing Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trends?.pricingTrends || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="avgPrice" stroke="#8884d8" name="Average Price" />
              <Line type="monotone" dataKey="competitorPrice" stroke="#82ca9d" name="Competitor Price" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="dashboard-card">
          <h3>Demand Heatmap by Region</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={demandHeatmap?.regions || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="region" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="demand" fill="#8884d8" name="Demand Score" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="dashboard-card">
          <h3>Seasonal Trends</h3>
          <div className="trends-list">
            {trends?.seasonalTrends?.map((trend: any, index: number) => (
              <div key={index} className="trend-item">
                <span className="trend-name">{trend.event}</span>
                <span className="trend-date">{trend.date}</span>
                <span className="trend-impact">{trend.impact}% impact</span>
              </div>
            )) || <p>No seasonal trends detected</p>}
          </div>
        </div>

        <div className="dashboard-card">
          <h3>Competitor Analysis</h3>
          <div className="competitor-grid">
            {trends?.competitors?.map((competitor: any, index: number) => (
              <div key={index} className="competitor-card">
                <h4>{competitor.name}</h4>
                <p className="price">₹{competitor.avgPrice}</p>
                <p className="change" style={{ color: competitor.change > 0 ? 'green' : 'red' }}>
                  {competitor.change > 0 ? '+' : ''}{competitor.change}%
                </p>
              </div>
            )) || <p>No competitor data available</p>}
          </div>
        </div>
      </div>
    </div>
  )
}

export default MarketIntelligenceDashboard
