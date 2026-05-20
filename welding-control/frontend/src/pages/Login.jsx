import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const Login = ({ setCurrentUser }) => {
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    
    if (!login || !password) {
      setError('Введите логин и пароль')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login, password })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Ошибка входа')
      }

      const data = await response.json()
      
      if (data.success && data.user) {
        setCurrentUser(data.user)
        // После входа пользователь попадет на главную через App.jsx
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      backgroundColor: '#F9F4ED'
    }}>
      <div style={{
        background: 'white',
        padding: '40px',
        borderRadius: '10px',
        boxShadow: '0 8px 32px rgba(51, 67, 64, 0.1)',
        width: '400px',
        textAlign: 'center'
      }}>
        <h1 style={{ 
          color: '#334340', 
          marginBottom: '10px',
          fontSize: '1.8rem'
        }}>
          Контроль сварных швов
        </h1>
        <p style={{ 
          color: '#334340', 
          opacity: 0.7,
          marginBottom: '30px'
        }}>
          Войдите в систему
        </p>

        {error && (
          <div style={{
            background: '#FFE5E5',
            color: '#c62828',
            padding: '10px',
            borderRadius: '7px',
            marginBottom: '15px',
            fontSize: '0.9rem'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleLogin}>
          <input
            type="text"
            placeholder="Логин"
            value={login}
            onChange={(e) => setLogin(e.target.value)}
            style={{
              width: '100%',
              padding: '12px',
              marginBottom: '15px',
              border: '2px solid #334340',
              borderRadius: '7px',
              fontSize: '1rem',
              fontFamily: 'Montserrat, sans-serif'
            }}
          />
          
          <input
            type="password"
            placeholder="Пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{
              width: '100%',
              padding: '12px',
              marginBottom: '20px',
              border: '2px solid #334340',
              borderRadius: '7px',
              fontSize: '1rem',
              fontFamily: 'Montserrat, sans-serif'
            }}
          />
          
          <button
            type="submit"
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px',
              background: '#334340',
              color: '#F9F4ED',
              border: 'none',
              borderRadius: '7px',
              fontSize: '1.1rem',
              fontWeight: '600',
              cursor: 'pointer',
              fontFamily: 'Montserrat, sans-serif'
            }}
          >
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default Login