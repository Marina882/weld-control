import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

const DEFECT_CLASSES = [
  'Смежные дефекты (брызги/дуги)',
  'Дефекты целостности',
  'Геометрические дефекты',
  'Дефекты постобработки',
  'Неполные провары',
  'Шов без дефектов'
]

const CLASS_MAPPING = {
  'Смежные дефекты (брызги/дуги)': 'adj',
  'Дефекты целостности': 'int',
  'Геометрические дефекты': 'geo',
  'Дефекты постобработки': 'pro',
  'Неполные провары': 'non',
  'Шов без дефектов': 'good'
}

const Results = ({ results, setResults, currentUser }) => {
  const navigate = useNavigate()

  if (!results) {
    return (
      <div className="results-page">
        <h2>Результаты анализа</h2>
        <p>Нет данных. Загрузите изображение или используйте камеру.</p>
        <button onClick={() => navigate('/upload')}>Загрузить изображение</button>
      </div>
    )
  }

  const isVideoResult = results.frames && results.frames.length > 0

  if (isVideoResult) {
    return <VideoResults results={results} navigate={navigate} setResults={setResults} currentUser={currentUser} />
  }

  return <ImageResults results={results} navigate={navigate} setResults={setResults} currentUser={currentUser} />
}

const ImageResults = ({ results, navigate, setResults, currentUser }) => {
  const [zoomedImage, setZoomedImage] = useState(null)
  const [showDetails, setShowDetails] = useState(true)
  const [editMode, setEditMode] = useState(true)
  const [editedResults, setEditedResults] = useState(null)
  const [newDefectClass, setNewDefectClass] = useState('Смежные дефекты (брызги/дуги)')
  const [showAddDefect, setShowAddDefect] = useState(false)
  const [selectingPosition, setSelectingPosition] = useState(false)
  const [firstClick, setFirstClick] = useState(null)
  const [firstClickPercent, setFirstClickPercent] = useState(null)
  const [secondClickPercent, setSecondClickPercent] = useState(null)
  const [newDefectX, setNewDefectX] = useState(100)
  const [newDefectY, setNewDefectY] = useState(100)
  const [newDefectW, setNewDefectW] = useState(50)
  const [newDefectH, setNewDefectH] = useState(50)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    setEditedResults(JSON.parse(JSON.stringify(results)))
  }, [results])

  if (!editedResults) return null

  const deleteDefect = (index) => {
    const newResults = { ...editedResults }
    newResults.defects = newResults.defects.filter((_, i) => i !== index)
    newResults.total_defects = newResults.defects.length
    recalculateStats(newResults)
    setEditedResults(newResults)
    setHasChanges(true)
  }

  const changeDefectClass = (index, newClass) => {
    const newResults = { ...editedResults }
    newResults.defects[index].class_name = newClass
    newResults.defects[index].class = CLASS_MAPPING[newClass] || 'adj'
    recalculateStats(newResults)
    setEditedResults(newResults)
    setHasChanges(true)
  }

  const recalculateStats = (res) => {
    const classStats = {}
    res.defects.forEach(d => {
      if (!classStats[d.class_name]) {
        classStats[d.class_name] = { count: 0, total_confidence: 0 }
      }
      classStats[d.class_name].count++
      classStats[d.class_name].total_confidence += d.confidence
    })
    
    for (const name in classStats) {
      classStats[name].avg_confidence = Math.round(
        (classStats[name].total_confidence / classStats[name].count) * 1000
      ) / 1000
    }
    
    res.class_stats = classStats
    updateQuality(res)
  }

  const updateQuality = (res) => {
    const defects = res.defects
    if (!defects || defects.length === 0) {
      res.quality = 'Шов годен'
      return
    }
    
    const hasGood = defects.some(d => d.class === 'good')
    const hasNon = defects.some(d => d.class === 'non')
    const hasInt = defects.some(d => d.class === 'int')
    
    if (defects.every(d => d.class === 'good')) {
      res.quality = 'Шов годен'
    } else if (hasGood && defects.length === 1) {
      res.quality = 'Шов годен'
    } else if (hasNon || hasInt) {
      res.quality = 'Шов бракованный и не подлежит исправлению'
    } else {
      res.quality = 'Шов бракованный, необходимо исправить дефекты'
    }
  }

  const handleImageClick = (e) => {
    if (!selectingPosition) return
    
    const rect = e.target.getBoundingClientRect()
    const scaleX = e.target.naturalWidth / rect.width
    const scaleY = e.target.naturalHeight / rect.height
    
    const x = Math.round((e.clientX - rect.left) * scaleX)
    const y = Math.round((e.clientY - rect.top) * scaleY)
    const xPercent = ((e.clientX - rect.left) / rect.width) * 100
    const yPercent = ((e.clientY - rect.top) / rect.height) * 100
    
    if (!firstClick) {
      setFirstClick({ x, y })
      setFirstClickPercent({ x: xPercent, y: yPercent })
    } else {
      const x1 = Math.min(firstClick.x, x)
      const y1 = Math.min(firstClick.y, y)
      const x2 = Math.max(firstClick.x, x)
      const y2 = Math.max(firstClick.y, y)
      
      setNewDefectX(Math.round((x1 + x2) / 2))
      setNewDefectY(Math.round((y1 + y2) / 2))
      setNewDefectW(x2 - x1)
      setNewDefectH(y2 - y1)
      setSecondClickPercent({ x: xPercent, y: yPercent })
      setFirstClick(null)
      setFirstClickPercent(null)
      setSelectingPosition(false)
      setTimeout(() => setSecondClickPercent(null), 1500)
    }
  }

  const addDefect = () => {
    const newResults = { ...editedResults }
    
    const newDefect = {
      class: CLASS_MAPPING[newDefectClass] || 'adj',
      class_name: newDefectClass,
      confidence: 0.95,
      bbox: { 
        width: newDefectW, 
        height: newDefectH,
        x1: newDefectX - newDefectW/2, 
        y1: newDefectY - newDefectH/2, 
        x2: newDefectX + newDefectW/2, 
        y2: newDefectY + newDefectH/2 
      },
      center: { x: newDefectX, y: newDefectY }
    }
    
    newResults.defects = [...(newResults.defects || []), newDefect]
    newResults.total_defects = newResults.defects.length
    recalculateStats(newResults)
    setEditedResults(newResults)
    setShowAddDefect(false)
    setFirstClickPercent(null)
    setSecondClickPercent(null)
    setHasChanges(true)
  }
  
  const closeEditMode = async () => {
    try {
      const response = await fetch('/api/save-results', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...editedResults,
          operator_name: currentUser?.full_name || 'Оператор не определён',
          edited: hasChanges  
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setResults(editedResults)
        setEditMode(false)
        alert('Результат сохранен в БД. ID шва: ' + data.weld_id)
      } else {
        alert('Ошибка при сохранении')
      }
    } catch (err) {
      alert('Ошибка: ' + err.message)
    }
  }

  const { defects, total_defects, class_stats, annotated_image, quality } = editedResults

  return (
    <div className="results-page">
      <h2>Результаты анализа сварного шва</h2>
      
      {editMode && (
        <div style={{ padding: '8px 15px', borderRadius: '7px', marginBottom: '15px', textAlign: 'center', color: '#2e7d32', border: '2px solid #2e7d32', fontSize: '0.95rem' }}>
          Режим редактирования. Внесите изменения и нажмите "Закрыть режим редактирования"
        </div>
      )}
      
      <div className="result-single" style={{ position: 'relative', display: 'inline-block', width: '100%' }}>
        {annotated_image && (
          <>
            <img 
              src={`data:image/jpeg;base64,${annotated_image}`} 
              alt="Annotated weld" 
              onClick={selectingPosition ? handleImageClick : () => setZoomedImage(`data:image/jpeg;base64,${annotated_image}`)}
              style={{ cursor: selectingPosition ? 'crosshair' : 'pointer', width: '100%', display: 'block' }} 
            />
            {firstClickPercent && (
              <div style={{
                position: 'absolute', left: `${firstClickPercent.x}%`, top: `${firstClickPercent.y}%`,
                width: '14px', height: '14px', backgroundColor: '#2e7d32', border: '2px solid white',
                borderRadius: '50%', transform: 'translate(-50%, -50%)', pointerEvents: 'none', zIndex: 10,
                boxShadow: '0 0 4px rgba(0,0,0,0.5)'
              }} />
            )}
            {secondClickPercent && (
              <div style={{
                position: 'absolute', left: `${secondClickPercent.x}%`, top: `${secondClickPercent.y}%`,
                width: '14px', height: '14px', backgroundColor: '#2e7d32', border: '2px solid white',
                borderRadius: '50%', transform: 'translate(-50%, -50%)', pointerEvents: 'none', zIndex: 10,
                boxShadow: '0 0 4px rgba(0,0,0,0.5)'
              }} />
            )}
          </>
        )}
      </div>
      
      <div className="defects-list">
        <p>Всего дефектов: {total_defects}</p>
        <p>Качество шва: {quality || 'Не определено'}</p>
        
        {class_stats && Object.keys(class_stats).length > 0 && (
          <table>
            <thead><tr><th>Тип дефекта</th><th>Количество</th><th>Средняя уверенность</th></tr></thead>
            <tbody>
              {Object.entries(class_stats).map(([className, stats]) => (
                <tr key={className}><td>{className}</td><td>{stats.count}</td><td>{(stats.avg_confidence * 100).toFixed(1)}%</td></tr>
              ))}
            </tbody>
          </table>
        )}

        {editMode && (
          <div style={{ textAlign: 'center', marginTop: '20px' }}>
            {!showAddDefect ? (
              <button onClick={() => setShowAddDefect(true)} style={{ background: '#839958', width: '300px' }}>+ Добавить дефект</button>
            ) : (
              <div style={{ background: 'white', padding: '15px', borderRadius: '7px', maxWidth: '400px', margin: '0 auto' }}>
                <p style={{ marginBottom: '10px' }}>Выберите вид дефекта:</p>
                <select value={newDefectClass} onChange={(e) => setNewDefectClass(e.target.value)} style={{ width: '100%', marginBottom: '10px' }}>
                  {DEFECT_CLASSES.map(cls => (<option key={cls} value={cls}>{cls}</option>))}
                </select>
                
                <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '0.8rem' }}>X центра:</label>
                    <input type="number" value={newDefectX} onChange={(e) => setNewDefectX(Number(e.target.value))} style={{ width: '100%', padding: '5px' }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '0.8rem' }}>Y центра:</label>
                    <input type="number" value={newDefectY} onChange={(e) => setNewDefectY(Number(e.target.value))} style={{ width: '100%', padding: '5px' }} />
                  </div>
                </div>
                <button 
                  onClick={(e) => { e.stopPropagation(); setSelectingPosition(true); setFirstClick(null); setFirstClickPercent(null); setSecondClickPercent(null); }}
                  style={{ width: '100%', marginBottom: '10px', background: '#334340', fontSize: '0.9rem' }}
                >
                  Выделить область на фото
                </button>
                {selectingPosition && (
                  <p style={{ fontSize: '0.8rem', color: '#839958', marginBottom: '10px' }}>
                    {firstClick ? 'Кликните второй раз чтобы задать конец области' : 'Кликните на фото чтобы задать начало области'}
                  </p>
                )}
                
                <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '0.8rem' }}>Ширина:</label>
                    <input type="number" value={newDefectW} onChange={(e) => setNewDefectW(Number(e.target.value))} style={{ width: '100%', padding: '5px' }} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={{ fontSize: '0.8rem' }}>Высота:</label>
                    <input type="number" value={newDefectH} onChange={(e) => setNewDefectH(Number(e.target.value))} style={{ width: '100%', padding: '5px' }} />
                  </div>
                </div>
                
                <p style={{ fontSize: '0.9rem', opacity: 0.7, marginBottom: '10px' }}>Уверенность: 95%</p>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button onClick={addDefect} style={{ flex: 1, background: '#2e7d32' }}>Добавить</button>
                  <button onClick={() => { setShowAddDefect(false); setFirstClick(null); setFirstClickPercent(null); setSecondClickPercent(null); setSelectingPosition(false); }} style={{ flex: 1, background: '#999' }}>Отмена</button>
                </div>
              </div>
            )}
          </div>
        )}
        
        {defects && defects.length > 0 && (
          <div style={{ marginTop: '20px' }}>
            <button onClick={() => setShowDetails(!showDetails)} style={{ width: '100%', textAlign: 'left', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Детальная информация о дефектах</span>
              <span>{showDetails ? '▲' : '▼'}</span>
            </button>
            
            {showDetails && (
              <div style={{ marginTop: '20px' }}>
                <table>
                  <thead><tr><th>Тип</th><th>Уверенность</th><th>Позиция (x, y)</th><th>Размер (w × h)</th>{editMode && <th>Действия</th>}</tr></thead>
                  <tbody>
                    {defects.map((defect, index) => (
                      <tr key={index}>
                        <td>{editMode ? (<select value={defect.class_name} onChange={(e) => changeDefectClass(index, e.target.value)} style={{ padding: '5px', fontSize: '0.9rem' }}>{DEFECT_CLASSES.map(cls => (<option key={cls} value={cls}>{cls}</option>))}</select>) : defect.class_name}</td>
                        <td>{(defect.confidence * 100).toFixed(1)}%</td>
                        <td>{defect.center.x}, {defect.center.y}</td>
                        <td>{defect.bbox.width} × {defect.bbox.height}px</td>
                        {editMode && (<td><button onClick={() => deleteDefect(index)} style={{ background: '#c62828', color: 'white', padding: '5px 10px', fontSize: '0.8rem', border: 'none' }}>✕</button></td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
      
      {editMode && (
        <button onClick={closeEditMode} style={{ marginTop: '20px', background: '#334340', width: '300px', display: 'block', margin: '20px auto' }}>Закрыть режим редактирования</button>
      )}

      {zoomedImage && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.9)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 9999, cursor: 'pointer' }} onClick={() => setZoomedImage(null)}>
          <img src={zoomedImage} alt="Zoomed" style={{ maxWidth: '90%', maxHeight: '90%' }} />
          <button style={{ position: 'absolute', top: '20px', right: '20px', background: '#C0A961', color: 'white', border: 'none', fontSize: '1.5rem', width: '40px', height: '40px', borderRadius: '50%', cursor: 'pointer' }} onClick={() => setZoomedImage(null)}>✕</button>
        </div>
      )}
    </div>
  )
}

const VideoResults = ({ results, navigate, setResults, currentUser }) => {
  const [showDetails, setShowDetails] = useState(true)
  const [zoomedImage, setZoomedImage] = useState(null)
  const [currentFrame, setCurrentFrame] = useState(-1)
  const [editMode, setEditMode] = useState(true)
  const [editedResults, setEditedResults] = useState(null)
  const [newDefectClass, setNewDefectClass] = useState('Смежные дефекты (брызги/дуги)')
  const [showAddDefect, setShowAddDefect] = useState(false)
  const [selectingPosition, setSelectingPosition] = useState(false)
  const [firstClick, setFirstClick] = useState(null)
  const [firstClickPercent, setFirstClickPercent] = useState(null)
  const [secondClickPercent, setSecondClickPercent] = useState(null)
  const [newDefectX, setNewDefectX] = useState(100)
  const [newDefectY, setNewDefectY] = useState(100)
  const [newDefectW, setNewDefectW] = useState(50)
  const [newDefectH, setNewDefectH] = useState(50)
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    setEditedResults(JSON.parse(JSON.stringify(results)))
  }, [results])

  if (!editedResults) return null

  const { frames } = editedResults

  const deleteDefect = (index) => {
    const newResults = { ...editedResults }
    newResults.defects = newResults.defects.filter((_, i) => i !== index)
    newResults.total_defects = newResults.defects.length
    recalculateStats(newResults)
    setEditedResults(newResults)
    setHasChanges(true)
  }

  const changeDefectClass = (index, newClass) => {
    const newResults = { ...editedResults }
    newResults.defects[index].class_name = newClass
    newResults.defects[index].class = CLASS_MAPPING[newClass] || 'adj'
    recalculateStats(newResults)
    setEditedResults(newResults)
    setHasChanges(true)
  }

  const recalculateStats = (res) => {
    const classStats = {}
    res.defects.forEach(d => {
      if (!classStats[d.class_name]) {
        classStats[d.class_name] = { count: 0, totalConfidence: 0 }
      }
      classStats[d.class_name].count++
      classStats[d.class_name].totalConfidence += d.confidence
    })
    
    for (const name in classStats) {
      classStats[name].avg_confidence = classStats[name].count > 0 
        ? Math.round((classStats[name].totalConfidence / classStats[name].count) * 1000) / 1000 
        : 0
    }
    
    res.class_stats = classStats
    updateQuality(res)
  }

  const updateQuality = (res) => {
    const defects = res.defects
    if (!defects || defects.length === 0) { res.quality = 'Шов годен'; return }
    
    const hasGood = defects.some(d => d.class === 'good')
    const hasNon = defects.some(d => d.class === 'non')
    const hasInt = defects.some(d => d.class === 'int')
    
    if (defects.every(d => d.class === 'good')) res.quality = 'Шов годен'
    else if (hasGood && defects.length === 1) res.quality = 'Шов годен'
    else if (hasNon || hasInt) res.quality = 'Шов бракованный и не подлежит исправлению'
    else res.quality = 'Шов бракованный, необходимо исправить дефекты'
  }

  const handleImageClick = (e) => {
    if (!selectingPosition) return
    
    const rect = e.target.getBoundingClientRect()
    const scaleX = e.target.naturalWidth / rect.width
    const scaleY = e.target.naturalHeight / rect.height
    
    const x = Math.round((e.clientX - rect.left) * scaleX)
    const y = Math.round((e.clientY - rect.top) * scaleY)
    const xPercent = ((e.clientX - rect.left) / rect.width) * 100
    const yPercent = ((e.clientY - rect.top) / rect.height) * 100
    
    if (!firstClick) {
      setFirstClick({ x, y })
      setFirstClickPercent({ x: xPercent, y: yPercent })
    } else {
      const x1 = Math.min(firstClick.x, x)
      const y1 = Math.min(firstClick.y, y)
      const x2 = Math.max(firstClick.x, x)
      const y2 = Math.max(firstClick.y, y)
      
      setNewDefectX(Math.round((x1 + x2) / 2))
      setNewDefectY(Math.round((y1 + y2) / 2))
      setNewDefectW(x2 - x1)
      setNewDefectH(y2 - y1)
      setSecondClickPercent({ x: xPercent, y: yPercent })
      setFirstClick(null)
      setFirstClickPercent(null)
      setSelectingPosition(false)
      setTimeout(() => setSecondClickPercent(null), 1500)
    }
  }

  const addDefect = () => {
    const newResults = { ...editedResults }
    
    const newDefect = {
      class: CLASS_MAPPING[newDefectClass] || 'adj',
      class_name: newDefectClass,
      confidence: 0.95,
      bbox: { width: newDefectW, height: newDefectH },
      center: { x: newDefectX, y: newDefectY },
      frames_count: frames.length
    }
    
    newResults.defects = [...(newResults.defects || []), newDefect]
    newResults.total_defects = newResults.defects.length
    recalculateStats(newResults)
    setEditedResults(newResults)
    setShowAddDefect(false)
    setFirstClickPercent(null)
    setSecondClickPercent(null)
    setHasChanges(true)
  }

  const getFrameNumbers = (defect) => {
    if (defect.frames_count && defect.frames_count === frames.length) {
      return frames.map((_, i) => i + 1).join(', ')
    }
    
    const frameNumbers = []
    frames.forEach((frame, frameIdx) => {
      if (frame.defects) {
        const found = frame.defects.some(d => 
          d.class === defect.class && 
          Math.abs(d.center.x - defect.center.x) < 100 && 
          Math.abs(d.center.y - defect.center.y) < 100
        )
        if (found) frameNumbers.push(frameIdx + 1)
      }
    })
    return frameNumbers.length > 0 ? frameNumbers.join(', ') : '—'
  }

  const totalDefects = editedResults.total_defects || 0
  const classStats = editedResults.class_stats || {}
  const quality = editedResults.quality || 'Не определено'
  const defects = editedResults.defects || []

  const getCurrentImage = () => {
    if (currentFrame === -1) return editedResults.confirmed_frame || null
    return frames[currentFrame]?.annotated_image || null
  }

  const getCurrentLabel = () => {
    if (currentFrame === -1) return 'Подтверждённые дефекты'
    return `Кадр ${currentFrame + 1} / ${frames.length}`
  }

  const currentImage = getCurrentImage()

  const closeEditMode = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/save-video-results', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...editedResults,
          operator_name: currentUser?.full_name || 'Оператор не определён',
          edited: hasChanges
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setResults(editedResults)
        setEditMode(false)
        alert('Результат сохранен в БД. ID шва: ' + data.weld_id)
      } else {
        alert('Ошибка при сохранении')
      }
    } catch (err) {
      alert('Ошибка: ' + err.message)
    }
  }

  return (
    <div className="results-page">
      <h2>Результаты анализа видео</h2>
      
      {editMode && (
        <div style={{ padding: '8px 15px', borderRadius: '7px', marginBottom: '15px', textAlign: 'center', color: '#2e7d32', border: '2px solid #2e7d32', fontSize: '0.95rem' }}>
          Режим редактирования. Внесите изменения и нажмите "Закрыть режим редактирования"
        </div>
      )}
      
      <div className="result-single" style={{ position: 'relative', display: 'inline-block', width: '100%', marginBottom: '20px' }}>
        {currentImage ? (
          <>
            <img 
              src={`data:image/jpeg;base64,${currentImage}`} 
              alt={getCurrentLabel()} 
              onClick={selectingPosition ? handleImageClick : () => setZoomedImage(`data:image/jpeg;base64,${currentImage}`)}
              style={{ cursor: selectingPosition ? 'crosshair' : 'pointer', width: '100%', display: 'block' }} 
            />
            {firstClickPercent && (
              <div style={{
                position: 'absolute', left: `${firstClickPercent.x}%`, top: `${firstClickPercent.y}%`,
                width: '14px', height: '14px', backgroundColor: '#2e7d32', border: '2px solid white',
                borderRadius: '50%', transform: 'translate(-50%, -50%)', pointerEvents: 'none', zIndex: 10,
                boxShadow: '0 0 4px rgba(0,0,0,0.5)'
              }} />
            )}
            {secondClickPercent && (
              <div style={{
                position: 'absolute', left: `${secondClickPercent.x}%`, top: `${secondClickPercent.y}%`,
                width: '14px', height: '14px', backgroundColor: '#2e7d32', border: '2px solid white',
                borderRadius: '50%', transform: 'translate(-50%, -50%)', pointerEvents: 'none', zIndex: 10,
                boxShadow: '0 0 4px rgba(0,0,0,0.5)'
              }} />
            )}
          </>
        ) : (
          <div style={{ width: '100%', height: '300px', backgroundColor: '#eee', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Нет изображения</div>
        )}
        
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', marginTop: '15px', gap: '20px' }}>
          <button onClick={() => setCurrentFrame(prev => Math.max(-1, prev - 1))} disabled={currentFrame === -1} style={{ background: 'none', border: 'none', color: currentFrame === -1 ? '#ccc' : '#334340', fontSize: '2rem', cursor: currentFrame === -1 ? 'default' : 'pointer', padding: '0', width: 'auto' }}>‹</button>
          <span style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{getCurrentLabel()}</span>
          <button onClick={() => setCurrentFrame(prev => Math.min(frames.length - 1, prev + 1))} disabled={currentFrame === frames.length - 1} style={{ background: 'none', border: 'none', color: currentFrame === frames.length - 1 ? '#ccc' : '#334340', fontSize: '2rem', cursor: currentFrame === frames.length - 1 ? 'default' : 'pointer', padding: '0', width: 'auto' }}>›</button>
        </div>
      </div>
      
      <div className="defects-list">
        <h3>Обнаруженные дефекты</h3>
        <p>Всего дефектов: {totalDefects}</p>
        <p>Качество шва: {quality}</p>
        
        {Object.keys(classStats).length > 0 ? (
          <table>
            <thead><tr><th>Тип дефекта</th><th>Количество</th><th>Средняя уверенность</th></tr></thead>
            <tbody>
              {Object.entries(classStats).map(([name, stats]) => {
                const avgConf = stats.avg_confidence ? (stats.avg_confidence * 100).toFixed(1) : '0.0'
                return (<tr key={name}><td>{name}</td><td>{stats.count}</td><td>{avgConf}%</td></tr>)
              })}
            </tbody>
          </table>
        ) : (<p>Дефектов не обнаружено</p>)}
      </div>
      
      {editMode && (
        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          {!showAddDefect ? (
            <button onClick={() => setShowAddDefect(true)} style={{ background: '#839958', width: '300px' }}>+ Добавить дефект</button>
          ) : (
            <div style={{ background: 'white', padding: '15px', borderRadius: '7px', maxWidth: '400px', margin: '0 auto' }}>
              <p style={{ marginBottom: '10px' }}>Выберите вид дефекта:</p>
              <select value={newDefectClass} onChange={(e) => setNewDefectClass(e.target.value)} style={{ width: '100%', marginBottom: '10px' }}>
                {DEFECT_CLASSES.map(cls => (<option key={cls} value={cls}>{cls}</option>))}
              </select>
              
              <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '0.8rem' }}>X центра:</label>
                  <input type="number" value={newDefectX} onChange={(e) => setNewDefectX(Number(e.target.value))} style={{ width: '100%', padding: '5px' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '0.8rem' }}>Y центра:</label>
                  <input type="number" value={newDefectY} onChange={(e) => setNewDefectY(Number(e.target.value))} style={{ width: '100%', padding: '5px' }} />
                </div>
              </div>
              <button 
                onClick={(e) => { e.stopPropagation(); setSelectingPosition(true); setFirstClick(null); setFirstClickPercent(null); setSecondClickPercent(null); }}
                style={{ width: '100%', marginBottom: '10px', background: '#334340', fontSize: '0.9rem' }}
              >
                Выделить область на фото
              </button>
              {selectingPosition && (
                <p style={{ fontSize: '0.8rem', color: '#839958', marginBottom: '10px' }}>
                  {firstClick ? 'Кликните второй раз чтобы задать конец области' : 'Кликните на фото чтобы задать начало области'}
                </p>
              )}
              
              <div style={{ display: 'flex', gap: '10px', marginBottom: '10px' }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '0.8rem' }}>Ширина:</label>
                  <input type="number" value={newDefectW} onChange={(e) => setNewDefectW(Number(e.target.value))} style={{ width: '100%', padding: '5px' }} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: '0.8rem' }}>Высота:</label>
                  <input type="number" value={newDefectH} onChange={(e) => setNewDefectH(Number(e.target.value))} style={{ width: '100%', padding: '5px' }} />
                </div>
              </div>
              
              <p style={{ fontSize: '0.9rem', opacity: 0.7, marginBottom: '10px' }}>Уверенность: 95%</p>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button onClick={addDefect} style={{ flex: 1, background: '#2e7d32' }}>Добавить</button>
                <button onClick={() => { setShowAddDefect(false); setFirstClick(null); setFirstClickPercent(null); setSecondClickPercent(null); setSelectingPosition(false); }} style={{ flex: 1, background: '#999' }}>Отмена</button>
              </div>
            </div>
          )}
        </div>
      )}

      {defects.length > 0 && (
        <div style={{ marginTop: '20px' }}>
          <button onClick={() => setShowDetails(!showDetails)} style={{ width: '100%', textAlign: 'left', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Детальная информация</span>
            <span>{showDetails ? '▲' : '▼'}</span>
          </button>
          
          {showDetails && (
            <div style={{ marginTop: '20px' }}>
              <table>
                <thead><tr><th>Кадры</th><th>Тип</th><th>Уверенность</th><th>Позиция (x, y)</th><th>Размер (w × h)</th>{editMode && <th>Действия</th>}</tr></thead>
                <tbody>
                  {defects.map((defect, index) => (
                    <tr key={index}>
                      <td>{getFrameNumbers(defect)}</td>
                      <td>{editMode ? (<select value={defect.class_name} onChange={(e) => changeDefectClass(index, e.target.value)} style={{ padding: '5px', fontSize: '0.9rem' }}>{DEFECT_CLASSES.map(cls => (<option key={cls} value={cls}>{cls}</option>))}</select>) : defect.class_name}</td>
                      <td>{(defect.confidence * 100).toFixed(1)}%</td>
                      <td>{defect.center.x}, {defect.center.y}</td>
                      <td>{defect.bbox.width} × {defect.bbox.height}px</td>
                      {editMode && (<td><button onClick={() => deleteDefect(index)} style={{ background: '#c62828', color: 'white', padding: '5px 10px', fontSize: '0.8rem', border: 'none' }}>✕</button></td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      
      {editMode && (
        <button onClick={closeEditMode} style={{ marginTop: '20px', background: '#334340', width: '300px', display: 'block', margin: '20px auto' }}>Закрыть режим редактирования</button>
      )}

      {zoomedImage && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.9)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 9999, cursor: 'pointer' }} onClick={() => setZoomedImage(null)}>
          <img src={zoomedImage} alt="Zoomed" style={{ maxWidth: '90%', maxHeight: '90%' }} />
          <button style={{ position: 'absolute', top: '20px', right: '20px', background: '#C0A961', color: 'white', border: 'none', fontSize: '1.5rem', width: '40px', height: '40px', borderRadius: '50%', cursor: 'pointer' }} onClick={() => setZoomedImage(null)}>✕</button>
        </div>
      )}
    </div>
  )
}

export default Results