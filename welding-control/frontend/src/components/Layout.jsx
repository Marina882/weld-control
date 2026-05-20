import React from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

const Layout = ({ children, currentUser, setCurrentUser }) => {
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    setCurrentUser(null)
    navigate('/')
  }

  return (
    <div className="layout">
      <nav className="navbar">
        <div className="nav-brand">Контроль сварных швов</div>
        <div className="nav-menu">
          <button
            className={`nav-button ${location.pathname === '/' ? 'active' : ''}`}
            onClick={() => navigate('/')}
          >
            Главная
          </button>
          <button
            className={`nav-button ${location.pathname === '/report' ? 'active' : ''}`}
            onClick={() => navigate('/report')}
          >
            Отчёт
          </button>
          {currentUser && (
            <button
              onClick={handleLogout}
              className="nav-button"
              style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '8px',
                cursor: 'pointer'
              }}
              title="Нажмите для выхода"
            >
              {currentUser.full_name}
              <span style={{ fontSize: '0.7rem', opacity: 0.7 }}>↩</span>
            </button>
          )}
        </div>
      </nav>
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}

export default Layout