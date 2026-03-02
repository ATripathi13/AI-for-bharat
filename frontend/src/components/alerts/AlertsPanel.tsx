import { useState, useEffect } from 'react'
import { alertsApi } from '../../services/api'
import './AlertsPanel.css'

interface Alert {
  id: string
  type: 'info' | 'warning' | 'error' | 'escalation'
  title: string
  message: string
  timestamp: Date
  read: boolean
  priority: 'high' | 'medium' | 'low'
  source?: string
}

interface Escalation {
  id: string
  title: string
  description: string
  confidence: number
  agentId: string
  timestamp: Date
  status: 'pending' | 'approved' | 'rejected'
  data?: any
}

interface AlertsPanelProps {
  onClose: () => void
}

function AlertsPanel({ onClose }: AlertsPanelProps) {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [escalations, setEscalations] = useState<Escalation[]>([])
  const [activeTab, setActiveTab] = useState<'alerts' | 'escalations'>('alerts')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    // Poll for new alerts every 30 seconds
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [alertsData, escalationsData] = await Promise.all([
        alertsApi.getAll(),
        alertsApi.getEscalations(),
      ])
      setAlerts(alertsData || [])
      setEscalations(escalationsData || [])
    } catch (error) {
      console.error('Failed to load alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleMarkAsRead = async (alertId: string) => {
    try {
      await alertsApi.markAsRead(alertId)
      setAlerts(prev => prev.map(alert => 
        alert.id === alertId ? { ...alert, read: true } : alert
      ))
    } catch (error) {
      console.error('Failed to mark alert as read:', error)
    }
  }

  const handleEscalationResponse = async (escalationId: string, decision: 'approve' | 'reject', notes?: string) => {
    try {
      await alertsApi.respondToEscalation(escalationId, decision, notes)
      setEscalations(prev => prev.map(esc => 
        esc.id === escalationId ? { ...esc, status: decision === 'approve' ? 'approved' : 'rejected' } : esc
      ))
    } catch (error) {
      console.error('Failed to respond to escalation:', error)
    }
  }

  const unreadCount = alerts.filter(a => !a.read).length
  const pendingEscalations = escalations.filter(e => e.status === 'pending').length

  return (
    <div className="alerts-panel">
      <div className="alerts-header">
        <h3>Notifications</h3>
        <button className="close-button" onClick={onClose}>×</button>
      </div>

      <div className="alerts-tabs">
        <button
          className={activeTab === 'alerts' ? 'active' : ''}
          onClick={() => setActiveTab('alerts')}
        >
          Alerts {unreadCount > 0 && <span className="badge">{unreadCount}</span>}
        </button>
        <button
          className={activeTab === 'escalations' ? 'active' : ''}
          onClick={() => setActiveTab('escalations')}
        >
          Escalations {pendingEscalations > 0 && <span className="badge">{pendingEscalations}</span>}
        </button>
      </div>

      <div className="alerts-content">
        {loading ? (
          <div className="alerts-loading">Loading...</div>
        ) : activeTab === 'alerts' ? (
          <AlertsList alerts={alerts} onMarkAsRead={handleMarkAsRead} />
        ) : (
          <EscalationsList escalations={escalations} onRespond={handleEscalationResponse} />
        )}
      </div>
    </div>
  )
}

interface AlertsListProps {
  alerts: Alert[]
  onMarkAsRead: (id: string) => void
}

function AlertsList({ alerts, onMarkAsRead }: AlertsListProps) {
  if (alerts.length === 0) {
    return <div className="empty-state">No alerts</div>
  }

  return (
    <div className="alerts-list">
      {alerts.map(alert => (
        <div
          key={alert.id}
          className={`alert-card ${alert.type} ${alert.read ? 'read' : 'unread'}`}
        >
          <div className="alert-icon">
            {alert.type === 'error' && '🔴'}
            {alert.type === 'warning' && '⚠️'}
            {alert.type === 'info' && 'ℹ️'}
            {alert.type === 'escalation' && '🔔'}
          </div>
          <div className="alert-body">
            <div className="alert-title-row">
              <h4 className="alert-title">{alert.title}</h4>
              <span className={`priority-badge ${alert.priority}`}>
                {alert.priority}
              </span>
            </div>
            <p className="alert-message">{alert.message}</p>
            {alert.source && (
              <p className="alert-source">Source: {alert.source}</p>
            )}
            <div className="alert-footer">
              <span className="alert-time">
                {new Date(alert.timestamp).toLocaleString()}
              </span>
              {!alert.read && (
                <button
                  className="mark-read-button"
                  onClick={() => onMarkAsRead(alert.id)}
                >
                  Mark as read
                </button>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

interface EscalationsListProps {
  escalations: Escalation[]
  onRespond: (id: string, decision: 'approve' | 'reject', notes?: string) => void
}

function EscalationsList({ escalations, onRespond }: EscalationsListProps) {
  const [selectedEscalation, setSelectedEscalation] = useState<string | null>(null)
  const [notes, setNotes] = useState('')

  if (escalations.length === 0) {
    return <div className="empty-state">No escalations</div>
  }

  const handleApprove = (id: string) => {
    onRespond(id, 'approve', notes)
    setNotes('')
    setSelectedEscalation(null)
  }

  const handleReject = (id: string) => {
    onRespond(id, 'reject', notes)
    setNotes('')
    setSelectedEscalation(null)
  }

  return (
    <div className="escalations-list">
      {escalations.map(escalation => (
        <div key={escalation.id} className={`escalation-card status-${escalation.status}`}>
          <div className="escalation-header">
            <h4>{escalation.title}</h4>
            <span className={`status-badge ${escalation.status}`}>
              {escalation.status}
            </span>
          </div>
          <p className="escalation-description">{escalation.description}</p>
          <div className="escalation-meta">
            <div className="meta-item">
              <span className="meta-label">Agent:</span>
              <span className="meta-value">{escalation.agentId}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Confidence:</span>
              <span className="meta-value">{escalation.confidence}%</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Time:</span>
              <span className="meta-value">
                {new Date(escalation.timestamp).toLocaleString()}
              </span>
            </div>
          </div>

          {escalation.data && (
            <div className="escalation-data">
              <details>
                <summary>View Details</summary>
                <pre>{JSON.stringify(escalation.data, null, 2)}</pre>
              </details>
            </div>
          )}

          {escalation.status === 'pending' && (
            <div className="escalation-actions">
              {selectedEscalation === escalation.id ? (
                <div className="action-form">
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Add notes (optional)"
                    rows={3}
                  />
                  <div className="action-buttons">
                    <button
                      className="approve-button"
                      onClick={() => handleApprove(escalation.id)}
                    >
                      ✓ Approve
                    </button>
                    <button
                      className="reject-button"
                      onClick={() => handleReject(escalation.id)}
                    >
                      ✗ Reject
                    </button>
                    <button
                      className="cancel-button"
                      onClick={() => {
                        setSelectedEscalation(null)
                        setNotes('')
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  className="respond-button"
                  onClick={() => setSelectedEscalation(escalation.id)}
                >
                  Respond
                </button>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default AlertsPanel
