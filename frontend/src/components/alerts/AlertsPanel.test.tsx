import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import AlertsPanel from './AlertsPanel'
import { alertsApi } from '../../services/api'

vi.mock('../../services/api', () => ({
  alertsApi: {
    getAll: vi.fn(),
    getEscalations: vi.fn(),
    markAsRead: vi.fn(),
    respondToEscalation: vi.fn(),
  }
}))

describe('AlertsPanel', () => {
  const mockOnClose = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders alerts panel with header', async () => {
    vi.mocked(alertsApi.getAll).mockResolvedValue([])
    vi.mocked(alertsApi.getEscalations).mockResolvedValue([])
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    expect(screen.getByText('Notifications')).toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', async () => {
    vi.mocked(alertsApi.getAll).mockResolvedValue([])
    vi.mocked(alertsApi.getEscalations).mockResolvedValue([])
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    const closeButton = screen.getByText('×')
    fireEvent.click(closeButton)
    
    expect(mockOnClose).toHaveBeenCalled()
  })

  it('displays alerts tab by default', async () => {
    vi.mocked(alertsApi.getAll).mockResolvedValue([])
    vi.mocked(alertsApi.getEscalations).mockResolvedValue([])
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    await waitFor(() => {
      const alertsTab = screen.getByText(/Alerts/)
      expect(alertsTab.closest('button')).toHaveClass('active')
    })
  })

  it('displays unread count badge on alerts tab', async () => {
    const mockAlerts = [
      {
        id: '1',
        type: 'warning',
        title: 'Test Alert 1',
        message: 'Test message 1',
        timestamp: new Date(),
        read: false,
        priority: 'high',
      },
      {
        id: '2',
        type: 'info',
        title: 'Test Alert 2',
        message: 'Test message 2',
        timestamp: new Date(),
        read: true,
        priority: 'low',
      },
    ]
    
    vi.mocked(alertsApi.getAll).mockResolvedValue(mockAlerts)
    vi.mocked(alertsApi.getEscalations).mockResolvedValue([])
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument()
    })
  })

  it('displays alerts list', async () => {
    const mockAlerts = [
      {
        id: '1',
        type: 'warning',
        title: 'Stock Alert',
        message: 'Low stock detected',
        timestamp: new Date(),
        read: false,
        priority: 'high',
      },
    ]
    
    vi.mocked(alertsApi.getAll).mockResolvedValue(mockAlerts)
    vi.mocked(alertsApi.getEscalations).mockResolvedValue([])
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    await waitFor(() => {
      expect(screen.getByText('Stock Alert')).toBeInTheDocument()
      expect(screen.getByText('Low stock detected')).toBeInTheDocument()
    })
  })

  it('marks alert as read when button is clicked', async () => {
    const mockAlerts = [
      {
        id: '1',
        type: 'warning',
        title: 'Test Alert',
        message: 'Test message',
        timestamp: new Date(),
        read: false,
        priority: 'high',
      },
    ]
    
    vi.mocked(alertsApi.getAll).mockResolvedValue(mockAlerts)
    vi.mocked(alertsApi.getEscalations).mockResolvedValue([])
    vi.mocked(alertsApi.markAsRead).mockResolvedValue({})
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    await waitFor(() => {
      expect(screen.getByText('Mark as read')).toBeInTheDocument()
    })
    
    const markReadButton = screen.getByText('Mark as read')
    fireEvent.click(markReadButton)
    
    await waitFor(() => {
      expect(alertsApi.markAsRead).toHaveBeenCalledWith('1')
    })
  })

  it('switches to escalations tab when clicked', async () => {
    vi.mocked(alertsApi.getAll).mockResolvedValue([])
    vi.mocked(alertsApi.getEscalations).mockResolvedValue([])
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    const escalationsTab = screen.getByText(/Escalations/)
    fireEvent.click(escalationsTab)
    
    await waitFor(() => {
      expect(escalationsTab.closest('button')).toHaveClass('active')
    })
  })

  it('displays escalations list', async () => {
    const mockEscalations = [
      {
        id: '1',
        title: 'Pricing Decision',
        description: 'Requires approval for price change',
        confidence: 75,
        agentId: 'pricing-agent',
        timestamp: new Date(),
        status: 'pending',
      },
    ]
    
    vi.mocked(alertsApi.getAll).mockResolvedValue([])
    vi.mocked(alertsApi.getEscalations).mockResolvedValue(mockEscalations)
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    const escalationsTab = screen.getByText(/Escalations/)
    fireEvent.click(escalationsTab)
    
    await waitFor(() => {
      expect(screen.getByText('Pricing Decision')).toBeInTheDocument()
      expect(screen.getByText('Requires approval for price change')).toBeInTheDocument()
    })
  })

  it('shows respond form when respond button is clicked', async () => {
    const mockEscalations = [
      {
        id: '1',
        title: 'Test Escalation',
        description: 'Test description',
        confidence: 75,
        agentId: 'test-agent',
        timestamp: new Date(),
        status: 'pending',
      },
    ]
    
    vi.mocked(alertsApi.getAll).mockResolvedValue([])
    vi.mocked(alertsApi.getEscalations).mockResolvedValue(mockEscalations)
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    const escalationsTab = screen.getByText(/Escalations/)
    fireEvent.click(escalationsTab)
    
    await waitFor(() => {
      expect(screen.getByText('Respond')).toBeInTheDocument()
    })
    
    const respondButton = screen.getByText('Respond')
    fireEvent.click(respondButton)
    
    expect(screen.getByText('✓ Approve')).toBeInTheDocument()
    expect(screen.getByText('✗ Reject')).toBeInTheDocument()
  })

  it('approves escalation when approve button is clicked', async () => {
    const mockEscalations = [
      {
        id: '1',
        title: 'Test Escalation',
        description: 'Test description',
        confidence: 75,
        agentId: 'test-agent',
        timestamp: new Date(),
        status: 'pending',
      },
    ]
    
    vi.mocked(alertsApi.getAll).mockResolvedValue([])
    vi.mocked(alertsApi.getEscalations).mockResolvedValue(mockEscalations)
    vi.mocked(alertsApi.respondToEscalation).mockResolvedValue({})
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    const escalationsTab = screen.getByText(/Escalations/)
    fireEvent.click(escalationsTab)
    
    await waitFor(() => {
      expect(screen.getByText('Respond')).toBeInTheDocument()
    })
    
    const respondButton = screen.getByText('Respond')
    fireEvent.click(respondButton)
    
    const approveButton = screen.getByText('✓ Approve')
    fireEvent.click(approveButton)
    
    await waitFor(() => {
      expect(alertsApi.respondToEscalation).toHaveBeenCalledWith('1', 'approve', '')
    })
  })

  it('rejects escalation when reject button is clicked', async () => {
    const mockEscalations = [
      {
        id: '1',
        title: 'Test Escalation',
        description: 'Test description',
        confidence: 75,
        agentId: 'test-agent',
        timestamp: new Date(),
        status: 'pending',
      },
    ]
    
    vi.mocked(alertsApi.getAll).mockResolvedValue([])
    vi.mocked(alertsApi.getEscalations).mockResolvedValue(mockEscalations)
    vi.mocked(alertsApi.respondToEscalation).mockResolvedValue({})
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    const escalationsTab = screen.getByText(/Escalations/)
    fireEvent.click(escalationsTab)
    
    await waitFor(() => {
      expect(screen.getByText('Respond')).toBeInTheDocument()
    })
    
    const respondButton = screen.getByText('Respond')
    fireEvent.click(respondButton)
    
    const rejectButton = screen.getByText('✗ Reject')
    fireEvent.click(rejectButton)
    
    await waitFor(() => {
      expect(alertsApi.respondToEscalation).toHaveBeenCalledWith('1', 'reject', '')
    })
  })

  it('displays empty state when no alerts', async () => {
    vi.mocked(alertsApi.getAll).mockResolvedValue([])
    vi.mocked(alertsApi.getEscalations).mockResolvedValue([])
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    await waitFor(() => {
      expect(screen.getByText('No alerts')).toBeInTheDocument()
    })
  })

  it('displays empty state when no escalations', async () => {
    vi.mocked(alertsApi.getAll).mockResolvedValue([])
    vi.mocked(alertsApi.getEscalations).mockResolvedValue([])
    
    render(<AlertsPanel onClose={mockOnClose} />)
    
    const escalationsTab = screen.getByText(/Escalations/)
    fireEvent.click(escalationsTab)
    
    await waitFor(() => {
      expect(screen.getByText('No escalations')).toBeInTheDocument()
    })
  })
})
