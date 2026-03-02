import { useState, useEffect, useRef } from 'react'
import { copilotApi } from '../../services/api'
import './BusinessCopilot.css'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  reasoning?: string
  actions?: ActionRecommendation[]
}

interface ActionRecommendation {
  action: string
  priority: 'high' | 'medium' | 'low'
  expectedImpact: string
}

function BusinessCopilot() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showReasoning, setShowReasoning] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadHistory()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadHistory = async () => {
    try {
      const history = await copilotApi.getHistory(20)
      if (history && history.messages) {
        setMessages(history.messages)
      }
    } catch (error) {
      console.error('Failed to load chat history:', error)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await copilotApi.sendQuery(input)
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer || 'I apologize, but I could not generate a response.',
        timestamp: new Date(),
        reasoning: response.reasoning,
        actions: response.recommendations,
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'I apologize, but I encountered an error processing your request. Please try again.',
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFeedback = async (messageId: string, rating: number) => {
    try {
      await copilotApi.provideFeedback(messageId, rating)
    } catch (error) {
      console.error('Failed to submit feedback:', error)
    }
  }

  return (
    <div className="copilot-container">
      <div className="copilot-header">
        <h2>🤖 Business Copilot</h2>
        <p className="copilot-subtitle">Ask me anything about your business data</p>
      </div>

      <div className="copilot-messages">
        {messages.length === 0 && (
          <div className="welcome-message">
            <h3>Welcome to Business Copilot!</h3>
            <p>I can help you with:</p>
            <ul>
              <li>Market trends and competitor analysis</li>
              <li>Demand forecasting and inventory planning</li>
              <li>Pricing optimization strategies</li>
              <li>Risk assessment and compliance questions</li>
              <li>Business insights and recommendations</li>
            </ul>
            <p>Try asking: "What are the top selling products this month?" or "Show me inventory alerts"</p>
          </div>
        )}

        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            <div className="message-avatar">
              {message.role === 'user' ? '👤' : '🤖'}
            </div>
            <div className="message-content">
              <div className="message-text">{message.content}</div>
              
              {message.actions && message.actions.length > 0 && (
                <div className="message-actions">
                  <h4>Recommended Actions:</h4>
                  {message.actions.map((action, index) => (
                    <div key={index} className={`action-item priority-${action.priority}`}>
                      <span className="action-icon">
                        {action.priority === 'high' ? '🔴' : action.priority === 'medium' ? '🟡' : '🟢'}
                      </span>
                      <div className="action-details">
                        <p className="action-text">{action.action}</p>
                        <p className="action-impact">{action.expectedImpact}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {message.reasoning && (
                <div className="message-reasoning">
                  <button
                    className="reasoning-toggle"
                    onClick={() => setShowReasoning(showReasoning === message.id ? null : message.id)}
                  >
                    {showReasoning === message.id ? '▼' : '▶'} Show Reasoning
                  </button>
                  {showReasoning === message.id && (
                    <div className="reasoning-content">
                      {message.reasoning}
                    </div>
                  )}
                </div>
              )}

              <div className="message-footer">
                <span className="message-time">
                  {new Date(message.timestamp).toLocaleTimeString()}
                </span>
                {message.role === 'assistant' && (
                  <div className="message-feedback">
                    <button onClick={() => handleFeedback(message.id, 1)} title="Helpful">
                      👍
                    </button>
                    <button onClick={() => handleFeedback(message.id, -1)} title="Not helpful">
                      👎
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <div className="message-avatar">🤖</div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="copilot-input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Ask me anything about your business..."
          rows={3}
          disabled={loading}
        />
        <button onClick={handleSend} disabled={!input.trim() || loading}>
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  )
}

export default BusinessCopilot
