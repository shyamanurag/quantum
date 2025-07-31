import { useEffect, useState } from 'react'
import './App.css'

// API Base URL - environment configurable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function App() {
  const [isConnected, setIsConnected] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [authToken, setAuthToken] = useState(localStorage.getItem('authToken'))
  const [trades, setTrades] = useState([])
  const [userAnalytics, setUserAnalytics] = useState([])
  const [portfolioData, setPortfolioData] = useState(null)
  const [marketData, setMarketData] = useState(null)
  const [strategyPerformance, setStrategyPerformance] = useState([])
  const [dailyPnL, setDailyPnL] = useState([])
  const [activeTab, setActiveTab] = useState('dashboard')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loginForm, setLoginForm] = useState({ username: '', password: '' })
  const [showLogin, setShowLogin] = useState(!authToken)

  // Helper function to make authenticated API calls
  const apiCall = async (endpoint, options = {}) => {
    const headers = {
      'Content-Type': 'application/json',
      ...(authToken && { 'Authorization': `Bearer ${authToken}` }),
      ...options.headers
    }

    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers
      })

      if (response.status === 401) {
        // Token expired or invalid
        localStorage.removeItem('authToken')
        setAuthToken(null)
        setIsAuthenticated(false)
        setShowLogin(true)
        throw new Error('Authentication required')
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      return await response.json()
    } catch (error) {
      console.error(`API call failed for ${endpoint}:`, error)
      throw error
    }
  }

  // Login function
  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const response = await apiCall('/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginForm)
      })

      if (response.access_token) {
        setAuthToken(response.access_token)
        localStorage.setItem('authToken', response.access_token)
        setIsAuthenticated(true)
        setShowLogin(false)
        console.log('Login successful:', response)
      }
    } catch (error) {
      setError('Login failed: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  // Logout function
  const handleLogout = () => {
    localStorage.removeItem('authToken')
    setAuthToken(null)
    setIsAuthenticated(false)
    setShowLogin(true)
    setTrades([])
    setUserAnalytics([])
    setPortfolioData(null)
  }

  // Verify authentication on load
  useEffect(() => {
    if (authToken) {
      apiCall('/auth/verify')
        .then(() => {
          setIsAuthenticated(true)
          setShowLogin(false)
        })
        .catch(() => {
          localStorage.removeItem('authToken')
          setAuthToken(null)
          setShowLogin(true)
        })
    }
  }, [authToken])

  useEffect(() => {
    if (!isAuthenticated) return

    console.log('Fetching data...')
    const fetchData = async () => {
      setLoading(true)
      setError(null)

      try {
        // Health check
        const healthData = await apiCall('/health')
        console.log('Health check:', healthData)
        setIsConnected(healthData.status === 'healthy' || healthData.status === 'degraded')

        // Fetch trades
        try {
          const tradesData = await apiCall('/trades/')
          console.log('Trades fetched:', tradesData)
          setTrades(Array.isArray(tradesData) ? tradesData : [])
        } catch (err) {
          console.warn('Trade data unavailable:', err.message)
          setTrades([])
        }

        // Fetch user analytics
        try {
          const analyticsData = await apiCall('/api/users/performance?user_id=1')
          console.log('User analytics fetched:', analyticsData)
          setUserAnalytics(analyticsData.data ? [analyticsData.data] : [])
        } catch (err) {
          console.warn('Analytics data unavailable:', err.message)
          setUserAnalytics([])
        }

        // Fetch dashboard summary
        try {
          const dashboardData = await apiCall('/api/dashboard/summary')
          console.log('Dashboard data:', dashboardData)
          setPortfolioData(dashboardData.portfolio || dashboardData)
        } catch (err) {
          console.warn('Dashboard data unavailable:', err.message)
          setPortfolioData(null)
        }

        // Fetch daily P&L
        try {
          const dailyPnLData = await apiCall('/api/monitoring/daily-pnl')
          console.log('Daily P&L fetched:', dailyPnLData)
          setDailyPnL(dailyPnLData.daily_pnl || [])
        } catch (err) {
          console.warn('Daily P&L data unavailable:', err.message)
          setDailyPnL([])
        }

        // Fetch strategy performance
        try {
          const strategiesData = await apiCall('/api/strategies/performance')
          console.log('Strategy performance fetched:', strategiesData)
          setStrategyPerformance(strategiesData.strategies || [])
        } catch (err) {
          console.warn('Strategy performance data unavailable:', err.message)
          setStrategyPerformance([])
        }

      } catch (err) {
        setError('Failed to load data: ' + err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 30000) // Poll every 30s
    return () => clearInterval(interval)
  }, [isAuthenticated])

  const renderDashboard = () => (
    <div className="dashboard-content">
      <div className="metrics-grid">
        <div className="metric-card">
          <h3>Total Trades</h3>
          <div className="metric-value">{trades.length}</div>
        </div>
        <div className="metric-card">
          <h3>Active Strategies</h3>
          <div className="metric-value">{strategyPerformance.length}</div>
        </div>
        <div className="metric-card">
          <h3>Daily P&L</h3>
          <div className="metric-value">
            ${dailyPnL.reduce((sum, day) => sum + (day.total_pnl || 0), 0).toFixed(2)}
          </div>
        </div>
        <div className="metric-card">
          <h3>Connection</h3>
          <div className={`metric-value ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? 'Live' : 'Offline'}
          </div>
        </div>
      </div>

      <div className="charts-section">
        <div className="chart-card">
          <h3>Daily P&L Trend</h3>
          {dailyPnL.length > 0 ? (
            <div className="pnl-chart">
              {dailyPnL.map((day, index) => (
                <div key={index} className="pnl-bar">
                  <div className="pnl-date">{day.date}</div>
                  <div className={`pnl-amount ${day.total_pnl >= 0 ? 'positive' : 'negative'}`}>
                    ${day.total_pnl?.toFixed(2) || '0.00'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p>No P&L data available</p>
          )}
        </div>
      </div>
    </div>
  )

  const renderTradeDetails = () => (
    <div className="trade-details-content">
      <h2>Trade History</h2>
      {trades.length > 0 ? (
        <div className="table-container">
          <table className="trades-table">
            <thead>
              <tr>
                <th>Trade ID</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>P&L</th>
                <th>Status</th>
                <th>Strategy</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {trades.map(trade => (
                <tr key={trade.trade_id || trade.id}>
                  <td>{trade.trade_id || trade.id}</td>
                  <td>{trade.symbol}</td>
                  <td className={`side ${trade.side?.toLowerCase()}`}>{trade.side}</td>
                  <td>{trade.quantity}</td>
                  <td>${trade.price?.toFixed(4) || '0.0000'}</td>
                  <td className={`pnl ${(trade.pnl || 0) >= 0 ? 'positive' : 'negative'}`}>
                    ${trade.pnl?.toFixed(2) || '0.00'}
                  </td>
                  <td className={`status ${trade.status?.toLowerCase()}`}>{trade.status}</td>
                  <td>{trade.strategy || 'Manual'}</td>
                  <td>{trade.executed_at || trade.created_at || 'N/A'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="no-data">
          <p>No trades found</p>
          <small>Trades will appear here as they are executed</small>
        </div>
      )}
    </div>
  )

  const renderAnalytics = () => (
    <div className="analytics-content">
      <h2>Performance Analytics</h2>

      <div className="analytics-grid">
        <div className="analytics-card">
          <h3>User Performance</h3>
          {userAnalytics.length > 0 ? (
            <div className="user-stats">
              {userAnalytics.map((user, index) => (
                <div key={index} className="user-row">
                  <div className="stat">
                    <label>Total Trades Today:</label>
                    <span>{user.total_trades_today}</span>
                  </div>
                  <div className="stat">
                    <label>Win Rate:</label>
                    <span>{user.win_rate}%</span>
                  </div>
                  <div className="stat">
                    <label>Total P&L:</label>
                    <span className={user.total_pnl >= 0 ? 'positive' : 'negative'}>
                      ${user.total_pnl?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                  <div className="stat">
                    <label>Unrealized P&L:</label>
                    <span className={user.unrealized_pnl >= 0 ? 'positive' : 'negative'}>
                      ${user.unrealized_pnl?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p>No user analytics available</p>
          )}
        </div>

        <div className="analytics-card">
          <h3>Strategy Performance</h3>
          {strategyPerformance.length > 0 ? (
            <div className="strategy-list">
              {strategyPerformance.map((strategy, index) => (
                <div key={index} className="strategy-item">
                  <div className="strategy-name">{strategy.name}</div>
                  <div className="strategy-metrics">
                    <span>P&L: ${strategy.pnl?.toFixed(2) || '0.00'}</span>
                    <span>Trades: {strategy.trades || 0}</span>
                    <span>Win Rate: {strategy.win_rate || 0}%</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p>No strategy data available</p>
          )}
        </div>
      </div>
    </div>
  )

  const renderPortfolio = () => (
    <div className="portfolio-content">
      <h2>Portfolio Overview</h2>
      {portfolioData ? (
        <div className="portfolio-details">
          <pre>{JSON.stringify(portfolioData, null, 2)}</pre>
        </div>
      ) : (
        <p>Loading portfolio data...</p>
      )}
    </div>
  )

  return (
    <div className="App">
      <header className="app-header">
        <h1>🚀 Quantum Crypto Trading System</h1>
        <div className="connection-status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}>
            {isConnected ? '✅ Connected' : '❌ Disconnected'}
          </span>
        </div>
      </header>

      <nav className="navigation">
        <button
          className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setActiveTab('dashboard')}
        >
          📊 Dashboard
        </button>
        <button
          className={`nav-tab ${activeTab === 'trades' ? 'active' : ''}`}
          onClick={() => setActiveTab('trades')}
        >
          📋 Trade Details
        </button>
        <button
          className={`nav-tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          📈 Analytics
        </button>
        <button
          className={`nav-tab ${activeTab === 'portfolio' ? 'active' : ''}`}
          onClick={() => setActiveTab('portfolio')}
        >
          💼 Portfolio
        </button>
      </nav>

      <main className="app-main">
        {loading && <div className="loading">Loading...</div>}
        {error && <div className="error-message">{error}</div>}

        {showLogin && (
          <div className="login-form-container">
            <h2>Login</h2>
            <form onSubmit={handleLogin}>
              <div>
                <label>Username:</label>
                <input
                  type="text"
                  value={loginForm.username}
                  onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
                  required
                />
              </div>
              <div>
                <label>Password:</label>
                <input
                  type="password"
                  value={loginForm.password}
                  onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                  required
                />
              </div>
              <button type="submit" disabled={loading}>
                {loading ? 'Logging In...' : 'Login'}
              </button>
            </form>
            {error && <p className="error-message">{error}</p>}
          </div>
        )}

        {!showLogin && (
          <>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
            {activeTab === 'dashboard' && renderDashboard()}
            {activeTab === 'trades' && renderTradeDetails()}
            {activeTab === 'analytics' && renderAnalytics()}
            {activeTab === 'portfolio' && renderPortfolio()}
          </>
        )}
      </main>
    </div>
  )
}

export default App 