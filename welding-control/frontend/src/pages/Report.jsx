import React, { useState, useEffect } from 'react'

const Report = ({ results }) => {
  const [reportType, setReportType] = useState(null)
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dailyReport, setDailyReport] = useState(null)
  const [weldId, setWeldId] = useState('')
  const [historyList, setHistoryList] = useState([])

  // Загрузка истории из БД
  const loadHistory = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/history?limit=100')
      const data = await response.json()
      if (data.history && data.history.length > 0) {
        setHistoryList(data.history)
        // Если нет выбранного ID, выбираем последний
        if (!weldId) {
          setWeldId(data.history[0].weld_id)
        }
      }
    } catch (err) {
      console.error('Ошибка загрузки истории:', err)
    }
  }

  useEffect(() => {
    if (reportType === 'single') {
      loadHistory()
    }
  }, [reportType])

  const loadDailyReport = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`/api/report/daily?date=${selectedDate}`)
      if (!response.ok) throw new Error('Ошибка при загрузке отчёта')
      const data = await response.json()
      setDailyReport(data)
    } catch (err) {
      setError('Ошибка: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const downloadDailyReport = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`http://localhost:8000/api/report/daily/download?date=${selectedDate}&format=pdf`)
      if (!response.ok) throw new Error('Ошибка при скачивании отчёта')
      
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `daily_report_${selectedDate}.pdf`
      link.click()
    } catch (err) {
      setError('Ошибка: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const downloadWeldReport = async () => {
    if (!weldId) {
      setError('Выберите или введите ID шва')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`http://localhost:8000/api/report/weld/${weldId}/pdf`)
      if (!response.ok) throw new Error('Ошибка при генерации отчёта')
      
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `weld_report_${weldId}.pdf`
      link.click()
    } catch (err) {
      setError('Ошибка: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!reportType) {
    return (
      <div className="report-page">
        <h2>Формирование отчёта</h2>
        {error && <div className="error-message">{error}</div>}
        
        <div style={{ textAlign: 'center' }}>
          <button onClick={() => setReportType('daily')} style={{ margin: '10px auto', display: 'block', width: '300px' }}>
            Отчёт за рабочий день
          </button>
          <button onClick={() => setReportType('single')} style={{ margin: '10px auto', display: 'block', width: '300px' }}>
            Отчёт сварочного шва
          </button>
        </div>
      </div>
    )
  }

  if (reportType === 'daily') {
    return (
      <div className="report-page">
        <h2>Отчёт за рабочий день</h2>
        {error && <div className="error-message">{error}</div>}
        
        <div className="report-form">
          <label>Выберите дату:</label>
          <input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} />
          
          <button onClick={loadDailyReport} disabled={loading}>
            {loading ? 'Загрузка...' : 'Показать отчёт'}
          </button>
          
          {dailyReport && (
            <div style={{ marginTop: '20px' }}>
              <h3>Отчёт за {dailyReport.date}</h3>
              {dailyReport.operators && (
                <div style={{ marginBottom: '15px' }}>
                  <h4>Операторы:</h4>
                  {Object.entries(dailyReport.operators).map(([name, stats]) => (
                    <p key={name}>• {name}: всего {stats.total} шв. (годных: {stats.good}, брак: {stats.defective})</p>
                  ))}
                </div>
              )}
              <p>Всего швов: {dailyReport.total_welds}</p>
              <p style={{ color: '#2e7d32' }}>Годных: {dailyReport.good_welds}</p>
              <p style={{ color: '#c62828' }}>Бракованных: {dailyReport.defective_welds}</p>
              
              <button onClick={downloadDailyReport} disabled={loading} style={{ marginTop: '20px' }}>
                {loading ? 'Скачивание...' : 'Подробный отчёт PDF'}
              </button>
            </div>
          )}
          
          <button onClick={() => { setReportType(null); setDailyReport(null) }} style={{ marginTop: '20px' }}>
            ← Назад
          </button>
        </div>
      </div>
    )
  }

  if (reportType === 'single') {
    return (
      <div className="report-page">
        <h2>Отчёт сварочного шва</h2>
        {error && <div className="error-message">{error}</div>}
        
        <div className="report-form">
          <label>Выберите ID шва из списка или введите вручную:</label>
          
          {historyList.length > 0 && (
            <div style={{ marginTop: '10px' }}>
              <label>Или выберите из списка:</label>
              <select value={weldId} onChange={(e) => setWeldId(e.target.value)}>
                <option value="">-- Выберите --</option>
                {historyList.map((item) => (
                  <option key={item.weld_id} value={item.weld_id}>
                    {item.weld_id} - {new Date(item.analysis_date).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </div>
          )}
          
          <label style={{ marginTop: '15px' }}>Или введите ID вручную:</label>
          <input
            type="text"
            placeholder="Например: WELD-20260507-ABC123"
            value={weldId}
            onChange={(e) => setWeldId(e.target.value)}
          />
          
          <button onClick={downloadWeldReport} disabled={loading} style={{ margin: '10px auto', display: 'block', width: '300px' }}>
            {loading ? 'Скачивание...' : 'Скачать PDF'}
          </button>
          
          <button onClick={loadHistory} style={{ margin: '5px auto', display: 'block', width: '300px', background: '#839958' }}>
            Обновить список
          </button>
          
          {historyList.length === 0 && (
            <p>Нет данных в базе. Выполните анализ или введите ID вручную.</p>
          )}
        </div>
        
        <button onClick={() => setReportType(null)} style={{ marginTop: '20px' }}>
          ← Назад
        </button>
      </div>
    )
  }
}

export default Report