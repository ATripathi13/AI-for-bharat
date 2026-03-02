import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { inventoryApi } from '../../services/api'
import './DashboardCommon.css'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

function InventoryPlanningDashboard() {
  const [optimization, setOptimization] = useState<any>(null)
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    setLoading(true)
    try {
      const [optimizationData, alertsData] = await Promise.all([
        inventoryApi.getOptimization(),
        inventoryApi.getStockAlerts(),
      ])
      setOptimization(optimizationData)
      setAlerts(alertsData)
    } catch (error) {
      console.error('Failed to load inventory data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="dashboard-loading">Loading inventory planning...</div>
  }

  return (
    <div className="dashboard-view">
      <h2>Inventory Planning</h2>

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>Inventory Status</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={optimization?.statusDistribution || []}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={(entry) => `${entry.name}: ${entry.value}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {(optimization?.statusDistribution || []).map((entry: any, index: number) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="dashboard-card">
          <h3>Stock Levels by Category</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={optimization?.categoryLevels || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="category" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="current" fill="#8884d8" name="Current Stock" />
              <Bar dataKey="optimal" fill="#82ca9d" name="Optimal Stock" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="dashboard-card full-width">
          <h3>Stock Alerts</h3>
          <div className="alerts-table">
            <table>
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Product</th>
                  <th>Current Stock</th>
                  <th>Status</th>
                  <th>Recommended Action</th>
                  <th>Priority</th>
                </tr>
              </thead>
              <tbody>
                {alerts.map((alert: any, index: number) => (
                  <tr key={index} className={`alert-${alert.priority}`}>
                    <td>{alert.sku}</td>
                    <td>{alert.productName}</td>
                    <td>{alert.currentStock}</td>
                    <td>
                      <span className={`status-badge ${alert.status}`}>
                        {alert.status}
                      </span>
                    </td>
                    <td>{alert.recommendation}</td>
                    <td>
                      <span className={`priority-badge ${alert.priority}`}>
                        {alert.priority}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="dashboard-card">
          <h3>Reorder Recommendations</h3>
          <div className="recommendations-list">
            {optimization?.reorderRecommendations?.map((rec: any, index: number) => (
              <div key={index} className="recommendation-item">
                <div className="rec-header">
                  <span className="rec-sku">{rec.sku}</span>
                  <span className="rec-priority">{rec.priority}</span>
                </div>
                <div className="rec-details">
                  <p>Reorder Quantity: <strong>{rec.quantity} units</strong></p>
                  <p>Expected Delivery: {rec.deliveryDate}</p>
                  <p>Cost: ₹{rec.cost}</p>
                </div>
              </div>
            )) || <p>No reorder recommendations</p>}
          </div>
        </div>

        <div className="dashboard-card">
          <h3>Supply-Demand Analysis</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={optimization?.supplyDemand || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="supply" fill="#8884d8" name="Supply" />
              <Bar dataKey="demand" fill="#82ca9d" name="Demand" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

export default InventoryPlanningDashboard
