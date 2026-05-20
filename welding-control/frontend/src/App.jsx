import React, { useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Upload from './pages/Upload'
import LiveCamera from './pages/LiveCamera'
import UploadVideo from './pages/UploadVideo'
import Results from './pages/Results'
import Report from './pages/Report'
import Login from './pages/Login'
import './App.css'

function App() {
  const [results, setResults] = useState(null)
  const [currentUser, setCurrentUser] = useState(null)

  if (!currentUser) {
    return <Login setCurrentUser={setCurrentUser} />
  }

  return (
    <Layout currentUser={currentUser} setCurrentUser={setCurrentUser}>
      <Routes>
        <Route path="/" element={<Home setResults={setResults} />} />
        <Route path="/upload" element={<Upload setResults={setResults} />} />
        <Route path="/live-camera" element={<LiveCamera setResults={setResults} />} />
        <Route path="/upload-video" element={<UploadVideo setResults={setResults} />} />
        <Route path="/results" element={<Results results={results} setResults={setResults} currentUser={currentUser} />} />
        <Route path="/report" element={<Report results={results} />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default App