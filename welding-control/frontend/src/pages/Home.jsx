import React from 'react'
import { useNavigate } from 'react-router-dom'

const Home = ({ setResults }) => {
  const navigate = useNavigate()

  return (
    <div className="home-page">
      <h1>Система контроля качества сварных швов</h1>
      <p>Автоматическое обнаружение дефектов с использованием ML</p>
      
      <div className="features-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="feature-card" onClick={() => navigate('/upload')}>
          <h3>Обработка изображения</h3>
          <p>Загрузите фото сварочного шва для анализа</p>
        </div>

        <div className="feature-card" onClick={() => navigate('/upload-video')}>
          <h3>Обработка видео</h3>
          <p>Загрузите видео сварочного шва для анализа</p>
        </div>
        
        <div className="feature-card" onClick={() => navigate('/live-camera')}>
          <h3>Обработка с камеры</h3>
          <p>Анализ в реальном времени</p>
        </div>
      </div>
    </div>
  )
}

export default Home