import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const LiveCamera = ({ setResults }) => {
  const navigate = useNavigate()
  const videoContainerRef = useRef(null)
  const videoElementRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const streamRef = useRef(null)
  
  const [isRecording, setIsRecording] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [uploadedVideo, setUploadedVideo] = useState(null)
  const [recordingTime, setRecordingTime] = useState(0)
  const [cameraActive, setCameraActive] = useState(false)
  const timerRef = useRef(null)

  useEffect(() => {
    return () => {
      stopAllTracks()
    }
  }, [])

  const stopAllTracks = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
    
    if (mediaRecorderRef.current) {
      try {
        if (mediaRecorderRef.current.state === 'recording') {
          mediaRecorderRef.current.stop()
        }
      } catch (e) {}
      mediaRecorderRef.current = null
    }
    
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
      streamRef.current = null
    }
    
    // Удаляем видео элемент
    if (videoElementRef.current && videoContainerRef.current) {
      videoElementRef.current.remove()
      videoElementRef.current = null
    }
    
    setIsRecording(false)
    setCameraActive(false)
  }

  const startCamera = async () => {
    try {
      stopAllTracks()
      setError(null)
      setUploadedVideo(null)
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'environment'
        } 
      })
      
      streamRef.current = stream
      
      // Создаем видео элемент динамически
      if (videoContainerRef.current) {
        const video = document.createElement('video')
        video.autoplay = true
        video.playsInline = true
        video.muted = true
        video.style.width = '100%'
        video.style.borderRadius = '7px'
        video.style.backgroundColor = '#000'
        video.style.minHeight = '400px'
        video.style.display = 'block'
        
        video.srcObject = stream
        
        video.onloadedmetadata = () => {
          video.play()
        }
        
        videoContainerRef.current.innerHTML = ''
        videoContainerRef.current.appendChild(video)
        videoElementRef.current = video
      }
      
      setCameraActive(true)
    } catch (err) {
      console.error('Ошибка камеры:', err)
      setError('Не удалось получить доступ к камере: ' + err.message)
    }
  }

  const startRecording = () => {
    if (!streamRef.current) {
      setError('Камера не активна')
      return
    }
    
    setError(null)
    
    try {
      const mediaRecorder = new MediaRecorder(streamRef.current, {
        mimeType: 'video/webm;codecs=vp8'
      })
      const chunks = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' })
        const file = new File([blob], 'camera_recording.webm', { type: 'video/webm' })
        setUploadedVideo(file)
        stopAllTracks()
      }

      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start(1000)
      setIsRecording(true)
      setRecordingTime(0)
      
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => {
          if (prev >= 9) {
            if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
              mediaRecorderRef.current.stop()
            }
            return 0
          }
          return prev + 1
        })
      }, 1000)

    } catch (err) {
      console.error('Ошибка записи:', err)
      setError('Ошибка при начале записи: ' + err.message)
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }

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

      const response = await fetch('http://localhost:8000/api/analyze/video', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        throw new Error('Ошибка при анализе видео')
      }

      const data = await response.json()
      
      if (data.success || data.result) {
        const results_data = data.result || data
        stopAllTracks()
        setResults(results_data)
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

  const handleNewVideo = () => {
    setUploadedVideo(null)
  }

  return (
    <div className="camera-page">
      <h2>Обработка с камеры</h2>
      
      {error && <div className="error-message">{error}</div>}

      <div 
        ref={videoContainerRef}
        className="camera-container" 
        style={{ 
          width: '100%', 
          maxWidth: '640px', 
          margin: '0 auto'
        }}
      />

      {isRecording && (
        <div style={{
          textAlign: 'center',
          marginTop: '10px',
          color: '#334340',
          fontWeight: 'bold',
          fontSize: '1.2rem'
        }}>
          Запись... {10 - recordingTime} сек
        </div>
      )}

      {!cameraActive && !uploadedVideo && !videoContainerRef.current?.children?.length && (
        <div style={{ textAlign: 'center', padding: '50px' }}>
          <button onClick={startCamera} style={{ margin: '10px auto', display: 'block', width: '300px' }}>
            Включить камеру
          </button>
        </div>
      )}

      {uploadedVideo && (
        <div className="camera-container" style={{ maxWidth: '640px', margin: '0 auto' }}>
          <video 
            src={URL.createObjectURL(uploadedVideo)} 
            controls
            style={{ width: '100%', borderRadius: '7px' }}
          />
        </div>
      )}

      <div className="controls" style={{ textAlign: 'center', marginTop: '20px' }}>
        {cameraActive && (
          <div>
            {!isRecording ? (
              <button onClick={startRecording} style={{ margin: '10px auto', display: 'block', width: '300px' }}>
                Начать запись (10 сек)
              </button>
            ) : (
              <button onClick={stopRecording} style={{ margin: '10px auto', display: 'block', width: '300px' }}>
                Остановить запись
              </button>
            )}
            {!isRecording && (
              <button onClick={stopAllTracks} style={{ margin: '10px auto', display: 'block', width: '300px' }}>
                Выключить камеру
              </button>
            )}
          </div>
        )}

        {uploadedVideo && (
          <div>
            <button 
              onClick={analyzeVideo} 
              disabled={loading}
              style={{ margin: '10px auto', display: 'block', width: '300px' }}
            >
              {loading ? 'Анализируем видео...' : 'Анализировать видео'}
            </button>
            <button onClick={handleNewVideo} style={{ margin: '10px auto', display: 'block', width: '300px' }}>
              Записать новое видео
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default LiveCamera