import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import BusinessCopilot from './BusinessCopilot'
import { copilotApi } from '../../services/api'

vi.mock('../../services/api', () => ({
  copilotApi: {
    getHistory: vi.fn(),
    sendQuery: vi.fn(),
    provideFeedback: vi.fn(),
  }
}))

describe('BusinessCopilot', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders copilot interface', () => {
    vi.mocked(copilotApi.getHistory).mockResolvedValue({ messages: [] })
    
    render(<BusinessCopilot />)
    
    expect(screen.getByRole('heading', { level: 2, name: /Business Copilot/ })).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Ask me anything/)).toBeInTheDocument()
  })

  it('displays welcome message when no messages', async () => {
    vi.mocked(copilotApi.getHistory).mockResolvedValue({ messages: [] })
    
    render(<BusinessCopilot />)
    
    await waitFor(() => {
      expect(screen.getByText(/Welcome to Business Copilot!/)).toBeInTheDocument()
    })
  })

  it('loads and displays message history', async () => {
    const mockHistory = {
      messages: [
        {
          id: '1',
          role: 'user',
          content: 'What are the top products?',
          timestamp: new Date(),
        },
        {
          id: '2',
          role: 'assistant',
          content: 'Here are the top products...',
          timestamp: new Date(),
        },
      ]
    }
    
    vi.mocked(copilotApi.getHistory).mockResolvedValue(mockHistory)
    
    render(<BusinessCopilot />)
    
    await waitFor(() => {
      expect(screen.getByText('What are the top products?')).toBeInTheDocument()
      expect(screen.getByText('Here are the top products...')).toBeInTheDocument()
    })
  })

  it('sends message when send button is clicked', async () => {
    vi.mocked(copilotApi.getHistory).mockResolvedValue({ messages: [] })
    vi.mocked(copilotApi.sendQuery).mockResolvedValue({
      answer: 'Test response',
      reasoning: 'Test reasoning',
    })
    
    render(<BusinessCopilot />)
    
    const input = screen.getByPlaceholderText(/Ask me anything/)
    const sendButton = screen.getByText('Send')
    
    fireEvent.change(input, { target: { value: 'Test query' } })
    fireEvent.click(sendButton)
    
    await waitFor(() => {
      expect(copilotApi.sendQuery).toHaveBeenCalledWith('Test query')
    })
  })

  it('displays user message immediately after sending', async () => {
    vi.mocked(copilotApi.getHistory).mockResolvedValue({ messages: [] })
    vi.mocked(copilotApi.sendQuery).mockResolvedValue({
      answer: 'Test response',
    })
    
    render(<BusinessCopilot />)
    
    const input = screen.getByPlaceholderText(/Ask me anything/)
    const sendButton = screen.getByText('Send')
    
    fireEvent.change(input, { target: { value: 'Test query' } })
    fireEvent.click(sendButton)
    
    expect(screen.getByText('Test query')).toBeInTheDocument()
  })

  it('displays assistant response after API call', async () => {
    vi.mocked(copilotApi.getHistory).mockResolvedValue({ messages: [] })
    vi.mocked(copilotApi.sendQuery).mockResolvedValue({
      answer: 'Test response',
    })
    
    render(<BusinessCopilot />)
    
    const input = screen.getByPlaceholderText(/Ask me anything/)
    const sendButton = screen.getByText('Send')
    
    fireEvent.change(input, { target: { value: 'Test query' } })
    fireEvent.click(sendButton)
    
    await waitFor(() => {
      expect(screen.getByText('Test response')).toBeInTheDocument()
    })
  })

  it('displays action recommendations when provided', async () => {
    vi.mocked(copilotApi.getHistory).mockResolvedValue({ messages: [] })
    vi.mocked(copilotApi.sendQuery).mockResolvedValue({
      answer: 'Test response',
      recommendations: [
        {
          action: 'Reorder inventory',
          priority: 'high',
          expectedImpact: 'Prevent stockout',
        }
      ]
    })
    
    render(<BusinessCopilot />)
    
    const input = screen.getByPlaceholderText(/Ask me anything/)
    const sendButton = screen.getByText('Send')
    
    fireEvent.change(input, { target: { value: 'Test query' } })
    fireEvent.click(sendButton)
    
    await waitFor(() => {
      expect(screen.getByText('Recommended Actions:')).toBeInTheDocument()
      expect(screen.getByText('Reorder inventory')).toBeInTheDocument()
      expect(screen.getByText('Prevent stockout')).toBeInTheDocument()
    })
  })

  it('toggles reasoning display when button is clicked', async () => {
    vi.mocked(copilotApi.getHistory).mockResolvedValue({ messages: [] })
    vi.mocked(copilotApi.sendQuery).mockResolvedValue({
      answer: 'Test response',
      reasoning: 'This is the reasoning',
    })
    
    render(<BusinessCopilot />)
    
    const input = screen.getByPlaceholderText(/Ask me anything/)
    const sendButton = screen.getByText('Send')
    
    fireEvent.change(input, { target: { value: 'Test query' } })
    fireEvent.click(sendButton)
    
    await waitFor(() => {
      expect(screen.getByText(/Show Reasoning/)).toBeInTheDocument()
    })
    
    const reasoningButton = screen.getByText(/Show Reasoning/)
    fireEvent.click(reasoningButton)
    
    expect(screen.getByText('This is the reasoning')).toBeInTheDocument()
  })

  it('sends feedback when thumbs up is clicked', async () => {
    const mockHistory = {
      messages: [
        {
          id: '1',
          role: 'assistant',
          content: 'Test message',
          timestamp: new Date(),
        },
      ]
    }
    
    vi.mocked(copilotApi.getHistory).mockResolvedValue(mockHistory)
    vi.mocked(copilotApi.provideFeedback).mockResolvedValue({})
    
    render(<BusinessCopilot />)
    
    await waitFor(() => {
      expect(screen.getByText('Test message')).toBeInTheDocument()
    })
    
    const thumbsUpButtons = screen.getAllByTitle('Helpful')
    fireEvent.click(thumbsUpButtons[0])
    
    await waitFor(() => {
      expect(copilotApi.provideFeedback).toHaveBeenCalledWith('1', 1)
    })
  })

  it('disables input and button while loading', async () => {
    vi.mocked(copilotApi.getHistory).mockResolvedValue({ messages: [] })
    vi.mocked(copilotApi.sendQuery).mockImplementation(() => 
      new Promise(resolve => setTimeout(() => resolve({ answer: 'Test' }), 1000))
    )
    
    render(<BusinessCopilot />)
    
    const input = screen.getByPlaceholderText(/Ask me anything/) as HTMLTextAreaElement
    const sendButton = screen.getByText('Send') as HTMLButtonElement
    
    fireEvent.change(input, { target: { value: 'Test query' } })
    fireEvent.click(sendButton)
    
    await waitFor(() => {
      expect(input.disabled).toBe(true)
      expect(sendButton.disabled).toBe(true)
    })
  })

  it('clears input after sending message', async () => {
    vi.mocked(copilotApi.getHistory).mockResolvedValue({ messages: [] })
    vi.mocked(copilotApi.sendQuery).mockResolvedValue({
      answer: 'Test response',
    })
    
    render(<BusinessCopilot />)
    
    const input = screen.getByPlaceholderText(/Ask me anything/) as HTMLTextAreaElement
    const sendButton = screen.getByText('Send')
    
    fireEvent.change(input, { target: { value: 'Test query' } })
    expect(input.value).toBe('Test query')
    
    fireEvent.click(sendButton)
    
    await waitFor(() => {
      expect(input.value).toBe('')
    })
  })
})
