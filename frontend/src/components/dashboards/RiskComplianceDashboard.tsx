import { useState, useEffect } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts'
import { riskComplianceApi } from '../../services/api'
import './DashboardCommon.css'

function RiskComplianceDashboard() {
  const [alerts, setAlerts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadResult, setUploadResult] = useState<any>(null)

  useEffect(() => {
    loadAlerts()
  }, [])

  const loadAlerts = async () => {
    setLoading(true)
    try {
      const data = await riskComplianceApi.getAlerts()
      setAlerts(data)
    } catch (error) {
      console.error('Failed to load risk compliance alerts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async () => {
    if (!selectedFile) return
    try {
      const result = await riskComplianceApi.uploadDocument(selectedFile)
      setUploadResult(result)
      setSelectedFile(null)
    } catch (error) {
      console.error('Failed to upload document:', error)
    }
  }

  if (loading) {
    return <div className="dashboard-loading">Loading risk & compliance...</div>
  }

  return (
    <div className="dashboard-view">
      <h2>Risk & Compliance</h2>

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h3>Document Upload</h3>
          <div className="upload-section">
            <input
              type="file"
              onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              accept=".pdf,.jpg,.jpeg,.png"
              className="file-input"
            />
            <button
              onClick={handleFileUpload}
              disabled={!selectedFile}
              className="upload-button"
            >
              Upload & Analyze
            </button>
          </div>
          {uploadResult && (
            <div className="upload-result">
              <h4>Analysis Result</h4>
              <p><strong>Document Type:</strong> {uploadResult.documentType}</p>
              <p><strong>Confidence:</strong> {uploadResult.confidence}%</p>
              <p><strong>Status:</strong> {uploadResult.status}</p>
              {uploadResult.issues && uploadResult.issues.length > 0 && (
                <div className="issues-list">
                  <strong>Issues Found:</strong>
                  <ul>
                    {uploadResult.issues.map((issue: string, index: number) => (
                      <li key={index}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="dashboard-card">
          <h3>Compliance Alerts</h3>
          <div className="alerts-list">
            {alerts.map((alert: any, index: number) => (
              <div key={index} className={`alert-item severity-${alert.severity}`}>
                <div className="alert-header">
                  <span className="alert-type">{alert.type}</span>
                  <span className="alert-severity">{alert.severity}</span>
                </div>
                <p className="alert-message">{alert.message}</p>
                <p className="alert-action">
                  <strong>Action:</strong> {alert.recommendedAction}
                </p>
                <span className="alert-time">{alert.timestamp}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="dashboard-card">
          <h3>Supplier Risk Scores</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={alerts.filter((a: any) => a.type === 'supplier_risk')}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="supplierId" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="riskScore" fill="#ff8042" name="Risk Score" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="dashboard-card">
          <h3>Fraud Detection Summary</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={alerts.filter((a: any) => a.type === 'fraud_detection').slice(0, 6)}>
              <PolarGrid />
              <PolarAngleAxis dataKey="category" />
              <PolarRadiusAxis />
              <Radar name="Risk Level" dataKey="riskLevel" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        <div className="dashboard-card full-width">
          <h3>Recent Compliance Activities</h3>
          <div className="activities-timeline">
            {alerts.slice(0, 10).map((activity: any, index: number) => (
              <div key={index} className="timeline-item">
                <div className="timeline-marker"></div>
                <div className="timeline-content">
                  <span className="timeline-time">{activity.timestamp}</span>
                  <p className="timeline-text">{activity.message}</p>
                  <span className={`timeline-status ${activity.status}`}>
                    {activity.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default RiskComplianceDashboard
