import { useState } from 'react'
import MarketIntelligenceDashboard from './dashboards/MarketIntelligenceDashboard'
import DemandForecastDashboard from './dashboards/DemandForecastDashboard'
import PricingOptimizationDashboard from './dashboards/PricingOptimizationDashboard'
import InventoryPlanningDashboard from './dashboards/InventoryPlanningDashboard'
import RiskComplianceDashboard from './dashboards/RiskComplianceDashboard'
import BusinessCopilot from './copilot/BusinessCopilot'
import AlertsPanel from './alerts/AlertsPanel'
import './Dashboard.css'

interface DashboardProps {
  user: any
  signOut?: () => void
}

type DashboardView = 'market' | 'demand' | 'pricing' | 'inventory' | 'risk' | 'copilot'

function Dashboard({ user, signOut }: DashboardProps) {
  const [activeView, setActiveView] = useState<DashboardView>('market')
  const [showAlerts, setShowAlerts] = useState(false)

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>RetailMind AI</h1>
        <div className="header-actions">
          <button 
            className="alerts-button"
            onClick={() => setShowAlerts(!showAlerts)}
          >
            🔔 Alerts
          </button>
          <span className="user-info">{user?.username}</span>
          {signOut && (
            <button onClick={signOut} className="sign-out-button">
              Sign Out
            </button>
          )}
        </div>
      </header>

      <div className="dashboard-content">
        <nav className="dashboard-nav">
          <button
            className={activeView === 'market' ? 'active' : ''}
            onClick={() => setActiveView('market')}
          >
            📊 Market Intelligence
          </button>
          <button
            className={activeView === 'demand' ? 'active' : ''}
            onClick={() => setActiveView('demand')}
          >
            📈 Demand Forecast
          </button>
          <button
            className={activeView === 'pricing' ? 'active' : ''}
            onClick={() => setActiveView('pricing')}
          >
            💰 Pricing Optimization
          </button>
          <button
            className={activeView === 'inventory' ? 'active' : ''}
            onClick={() => setActiveView('inventory')}
          >
            📦 Inventory Planning
          </button>
          <button
            className={activeView === 'risk' ? 'active' : ''}
            onClick={() => setActiveView('risk')}
          >
            🛡️ Risk & Compliance
          </button>
          <button
            className={activeView === 'copilot' ? 'active' : ''}
            onClick={() => setActiveView('copilot')}
          >
            🤖 Business Copilot
          </button>
        </nav>

        <main className="dashboard-main">
          {activeView === 'market' && <MarketIntelligenceDashboard />}
          {activeView === 'demand' && <DemandForecastDashboard />}
          {activeView === 'pricing' && <PricingOptimizationDashboard />}
          {activeView === 'inventory' && <InventoryPlanningDashboard />}
          {activeView === 'risk' && <RiskComplianceDashboard />}
          {activeView === 'copilot' && <BusinessCopilot />}
        </main>

        {showAlerts && (
          <aside className="alerts-sidebar">
            <AlertsPanel onClose={() => setShowAlerts(false)} />
          </aside>
        )}
      </div>
    </div>
  )
}

export default Dashboard
