import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'

const UploadVideo = ({ setResults }) => {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [uploadedVideo, setUploadedVideo] = useState(null)
  const [isDragActive, setIsDragActive] = useState(false)

  const handleVideoFile = (file) => {
    if (!file) return
    if (!file.type.startsWith('video/')) {
      setError('Пожалуйста, загрузите видео файл')
      return
    }
    setUploadedVideo(file)
    setError(null)
  }

  const handleFileInput = (event) => {
    const file = event.target.files[0]
    handleVideoFile(file)
  }

  const handleDragEnter = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(true)
  }, [])

  const handleDragLeave = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)
  }, [])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)
    const file = e.dataTransfer.files[0]
    handleVideoFile(file)
  }, [])

  const analyzeVideo = async () => {
    if (!uploadedVideo) {
      setError('Нет видео для анализа')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append('video', uploadedVideo)

      const response = await fetch('/api/analyze/video', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('Ошибка при анализе видео')
      }

      const data = await response.json()
      
      if (data.success || data.result) {
        setResults(data.result || data)
        navigate('/results')
      } else {
        setError('Ошибка при анализе видео')
      }
    } catch (err) {
      setError('Ошибка: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="upload-page">
      <h2>Загрузка видео сварного шва</h2>
      
      {error && <div className="error-message">{error}</div>}
      
      {!uploadedVideo ? (
        <div
          className={`upload-area ${isDragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => document.getElementById('video-input').click()}
        >
          <div className="upload-icon"></div>
          {loading ? (
            <p>Анализируем видео...</p>
          ) : isDragActive ? (
            <p>Отпустите файл для загрузки</p>
          ) : (
            <>
              <p>Перетащите видео сюда</p>
              <p className="upload-hint">или кликните для выбора файла</p>
              <p className="file-types">Поддерживаются: MP4, WebM</p>
            </>
          )}
          <input
            id="video-input"
            type="file"
            accept="video/*"
            onChange={handleFileInput}
            style={{ display: 'none' }}
          />
        </div>
      ) : (
        <div className="camera-container" style={{ maxWidth: '640px', margin: '0 auto' }}>
          <video 
            src={URL.createObjectURL(uploadedVideo)} 
            controls
            style={{ width: '100%', borderRadius: '7px' }}
          />
        </div>
      )}

      {uploadedVideo && (
        <div className="controls" style={{ textAlign: 'center', marginTop: '20px' }}>
          <button 
            onClick={analyzeVideo} 
            disabled={loading}
            style={{ margin: '10px auto', display: 'block', width: '300px' }}
          >
            {loading ? 'Анализируем видео...' : 'Анализировать видео'}
          </button>
          <button 
            onClick={() => setUploadedVideo(null)}
            style={{ margin: '10px auto', display: 'block', width: '300px' }}
          >
            Выбрать другое видео
          </button>
        </div>
      )}
    </div>
  )
}

export default UploadVideo