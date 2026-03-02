import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Dashboard from './Dashboard'

// Mock the dashboard components
vi.mock('./dashboards/MarketIntelligenceDashboard', () => ({
  default: () => <div>Market Intelligence Dashboard</div>
}))

vi.mock('./dashboards/DemandForecastDashboard', () => ({
  default: () => <div>Demand Forecast Dashboard</div>
}))

vi.mock('./dashboards/PricingOptimizationDashboard', () => ({
  default: () => <div>Pricing Optimization Dashboard</div>
}))

vi.mock('./dashboards/InventoryPlanningDashboard', () => ({
  default: () => <div>Inventory Planning Dashboard</div>
}))

vi.mock('./dashboards/RiskComplianceDashboard', () => ({
  default: () => <div>Risk Compliance Dashboard</div>
}))

vi.mock('./copilot/BusinessCopilot', () => ({
  default: () => <div>Business Copilot</div>
}))

vi.mock('./alerts/AlertsPanel', () => ({
  default: ({ onClose }: { onClose: () => void }) => (
    <div>
      Alerts Panel
      <button onClick={onClose}>Close</button>
    </div>
  )
}))

describe('Dashboard', () => {
  const mockUser = { username: 'testuser' }
  const mockSignOut = vi.fn()

  it('renders dashboard with header', () => {
    render(<Dashboard user={mockUser} signOut={mockSignOut} />)
    
    expect(screen.getByText('RetailMind AI')).toBeInTheDocument()
    expect(screen.getByText('testuser')).toBeInTheDocument()
  })

  it('renders navigation buttons', () => {
    render(<Dashboard user={mockUser} signOut={mockSignOut} />)
    
    expect(screen.getByRole('button', { name: /Market Intelligence/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Demand Forecast/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Pricing Optimization/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Inventory Planning/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Risk & Compliance/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Business Copilot/ })).toBeInTheDocument()
  })

  it('displays market intelligence dashboard by default', () => {
    render(<Dashboard user={mockUser} signOut={mockSignOut} />)
    
    expect(screen.getByText('Market Intelligence Dashboard')).toBeInTheDocument()
  })

  it('switches to demand forecast dashboard when clicked', () => {
    render(<Dashboard user={mockUser} signOut={mockSignOut} />)
    
    const demandButton = screen.getByText(/Demand Forecast/)
    fireEvent.click(demandButton)
    
    expect(screen.getByText('Demand Forecast Dashboard')).toBeInTheDocument()
  })

  it('switches to pricing optimization dashboard when clicked', () => {
    render(<Dashboard user={mockUser} signOut={mockSignOut} />)
    
    const pricingButton = screen.getByText(/Pricing Optimization/)
    fireEvent.click(pricingButton)
    
    expect(screen.getByText('Pricing Optimization Dashboard')).toBeInTheDocument()
  })

  it('switches to inventory planning dashboard when clicked', () => {
    render(<Dashboard user={mockUser} signOut={mockSignOut} />)
    
    const inventoryButton = screen.getByText(/Inventory Planning/)
    fireEvent.click(inventoryButton)
    
    expect(screen.getByText('Inventory Planning Dashboard')).toBeInTheDocument()
  })

  it('switches to risk compliance dashboard when clicked', () => {
    render(<Dashboard user={mockUser} signOut={mockSignOut} />)
    
    const riskButton = screen.getByText(/Risk & Compliance/)
    fireEvent.click(riskButton)
    
    expect(screen.getByText('Risk Compliance Dashboard')).toBeInTheDocument()
  })

  it('switches to business copilot when clicked', () => {
    render(<Dashboard user={mockUser} signOut={mockSignOut} />)
    
    const copilotButton = screen.getByText(/Business Copilot/)
    fireEvent.click(copilotButton)
    
    expect(screen.getByText('Business Copilot')).toBeInTheDocument()
  })

  it('toggles alerts panel when alerts button is clicked', () => {
    render(<Dashboard user={mockUser} signOut={mockSignOut} />)
    
    const alertsButton = screen.getByText(/Alerts/)
    fireEvent.click(alertsButton)
    
    expect(screen.getByText('Alerts Panel')).toBeInTheDocument()
    
    const closeButton = screen.getByText('Close')
    fireEvent.click(closeButton)
    
    expect(screen.queryByText('Alerts Panel')).not.toBeInTheDocument()
  })

  it('calls signOut when sign out button is clicked', () => {
    render(<Dashboard user={mockUser} signOut={mockSignOut} />)
    
    const signOutButton = screen.getByText('Sign Out')
    fireEvent.click(signOutButton)
    
    expect(mockSignOut).toHaveBeenCalled()
  })

  it('renders without sign out button when signOut prop is not provided', () => {
    render(<Dashboard user={mockUser} />)
    
    expect(screen.queryByText('Sign Out')).not.toBeInTheDocument()
  })
})
