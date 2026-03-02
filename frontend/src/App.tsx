import { useState, useEffect } from 'react'
import { Authenticator } from '@aws-amplify/ui-react'
import '@aws-amplify/ui-react/styles.css'
import Dashboard from './components/Dashboard'
import { getCurrentUser } from 'aws-amplify/auth'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    try {
      await getCurrentUser()
      setIsAuthenticated(true)
    } catch {
      setIsAuthenticated(false)
    }
  }

  return (
    <Authenticator>
      {({ signOut, user }) => (
        <div className="app">
          <Dashboard user={user} signOut={signOut} />
        </div>
      )}
    </Authenticator>
  )
}

export default App
