import React, { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadImage } from '../services/api'

const Upload = ({ setResults }) => {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selectedImage, setSelectedImage] = useState(null)
  const [preview, setPreview] = useState(null)
  const [isDragActive, setIsDragActive] = useState(false)
  const navigate = useNavigate()

  const handleFile = (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setError('Пожалуйста, загрузите изображение')
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => setPreview(e.target.result)
    reader.readAsDataURL(file)
    
    setSelectedImage(file)
    setError(null)
  }

  const handleFileInput = (event) => {
    const file = event.target.files[0]
    handleFile(file)
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
    handleFile(file)
  }, [])

  const analyzeImage = async () => {
    if (!selectedImage) {
      setError('Нет изображения для анализа')
      return
    }

    setLoading(true)
    setError(null)
    
    try {
      const data = await uploadImage(selectedImage)
      
      if (data.success || data.result) {
        setResults(data.result || data)
        navigate('/results')
      } else {
        setError('Ошибка при анализе изображения')
      }
    } catch (err) {
      setError('Ошибка при обработке: ' + (err.response?.data?.detail || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleNewImage = () => {
    setSelectedImage(null)
    setPreview(null)
  }

  return (
    <div className="upload-page">
      <h2>Загрузка изображения сварного шва</h2>
      
      {error && <div className="error-message">{error}</div>}
      
      {!selectedImage ? (
        <div
          className={`upload-area ${isDragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-input').click()}
        >
          <div className="upload-icon"></div>
          <p>Перетащите изображение сюда</p>
          <p className="upload-hint">или кликните для выбора файла</p>
          <p className="file-types">Поддерживаются: JPG, PNG</p>
          <input
            id="file-input"
            type="file"
            accept="image/*"
            onChange={handleFileInput}
            style={{ display: 'none' }}
          />
        </div>
      ) : (
        <div className="preview">
          <img src={preview} alt="Preview" />
        </div>
      )}

      {selectedImage && (
        <div className="controls" style={{ textAlign: 'center', marginTop: '20px' }}>
          <button 
            onClick={analyzeImage} 
            disabled={loading}
            style={{ margin: '10px auto', display: 'block', width: '300px' }}
          >
            {loading ? 'Анализ фото...' : 'Анализировать фото'}
          </button>
          <button 
            onClick={handleNewImage}
            style={{ margin: '10px auto', display: 'block', width: '300px' }}
          >
            Выбрать другое фото
          </button>
        </div>
      )}
    </div>
  )
}

export default Upload