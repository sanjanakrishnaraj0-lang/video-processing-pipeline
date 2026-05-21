import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import { Upload, FileVideo, CheckCircle, AlertCircle, Loader2, PlaySquare, ShieldAlert, BookOpen, GraduationCap } from 'lucide-react'
import './App.css'

function App() {
  const [file, setFile] = useState(null)
  const [isDragging, setIsDragging] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [status, setStatus] = useState({ type: '', message: '' })
  const [isUploading, setIsUploading] = useState(false)
  const [videoId, setVideoId] = useState(null)
  const [resultData, setResultData] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const fileInputRef = useRef(null)

  // Polling logic for video processing result
  useEffect(() => {
    let interval;
    if (videoId && isProcessing) {
      interval = setInterval(async () => {
        try {
          const { data } = await axios.get(`http://localhost:8000/result/${videoId}`)
          if (data.status === 'complete') {
            setResultData(data.data)
            setIsProcessing(false)
            setStatus({ type: 'success', message: 'Analysis complete!' })
          } else if (data.status === 'error') {
            setIsProcessing(false)
            setStatus({ type: 'error', message: data.message || 'Error processing video.' })
          }
        } catch (error) {
          console.error("Polling error:", error)
        }
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [videoId, isProcessing]);

  const handleDragOver = (e) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFile = e.dataTransfer.files[0]
      if (droppedFile.type.startsWith('video/')) {
        setFile(droppedFile)
        setStatus({ type: '', message: '' })
      } else {
        setStatus({ type: 'error', message: 'Please upload a video file.' })
      }
    }
  }

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setFile(e.target.files[0])
      setStatus({ type: '', message: '' })
    }
  }

  const handleUpload = async () => {
    if (!file) return

    setIsUploading(true)
    setUploadProgress(0)
    setStatus({ type: '', message: '' })
    setResultData(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_id', 'user_demo')

      const { data } = await axios.post('http://localhost:8000/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          setUploadProgress(percentCompleted)
        }
      })

      if (data.status === 'success') {
        setVideoId(data.video_id)
        setIsProcessing(true)
        setStatus({ 
          type: 'success', 
          message: 'Video uploaded successfully! The AI is now analyzing it...' 
        })
      }
      
    } catch (error) {
      console.error('Upload error:', error)
      setStatus({ 
        type: 'error', 
        message: error.response?.data?.detail || 'An error occurred during upload.' 
      })
    } finally {
      setIsUploading(false)
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const resetUpload = () => {
    setFile(null)
    setVideoId(null)
    setResultData(null)
    setStatus({ type: '', message: '' })
  }

  return (
    <div className="app-container">
      <header className="header animate-fade-in">
        <h1>Kovon AI</h1>
        <p>Upload training videos for automated safety and skill analysis</p>
      </header>

      {!resultData ? (
        <div className="glass upload-card animate-fade-in" style={{ animationDelay: '0.1s' }}>
          {!file ? (
            <div 
              className={`upload-area ${isDragging ? 'active' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="upload-icon" size={48} />
              <div className="upload-text">
                <h3>Drag & Drop your video here</h3>
                <p>or click to browse from your computer</p>
              </div>
              <input 
                type="file" 
                className="file-input" 
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept="video/*"
              />
            </div>
          ) : (
            <div className="selected-file">
              <FileVideo size={40} color="var(--accent)" />
              <div className="file-info">
                <span className="file-name">{file.name}</span>
                <span className="file-size">{formatFileSize(file.size)}</span>
              </div>
              {!isUploading && !isProcessing && (
                <button 
                  onClick={() => setFile(null)} 
                  style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                >
                  ✕
                </button>
              )}
            </div>
          )}

          {isUploading && (
            <div className="progress-container">
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
              </div>
            </div>
          )}

          {!isProcessing && (
            <button 
              className="btn-primary" 
              onClick={handleUpload}
              disabled={!file || isUploading}
            >
              {isUploading ? (
                <><Loader2 className="animate-spin" size={20} /> Uploading...</>
              ) : (
                <><PlaySquare size={20} /> Analyze Video</>
              )}
            </button>
          )}

          {isProcessing && (
            <div className="processing-status">
               <Loader2 className="animate-spin icon-large" size={32} color="var(--accent)" />
               <p>AI is currently processing your video...</p>
               <small>This may take up to a minute</small>
            </div>
          )}

          {status.message && (
            <div className={`status-message status-${status.type} animate-fade-in`}>
              {status.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
              {status.message}
            </div>
          )}
        </div>
      ) : (
        <div className="dashboard-container animate-fade-in">
          <div className="dashboard-header">
            <h2>Analysis Results</h2>
            <button className="btn-secondary" onClick={resetUpload}>Analyze Another Video</button>
          </div>

          <div className="dashboard-grid">
            <div className="glass card score-card">
              <div className="card-header">
                <GraduationCap size={24} color="var(--accent)" />
                <h3>Skill Score</h3>
              </div>
              <div className="score-value">{resultData.skill_score || resultData.skill_gap_analysis?.overall_score || 0}/100</div>
            </div>

            <div className="glass card">
              <div className="card-header">
                <ShieldAlert size={24} color="var(--error)" />
                <h3>Safety Violations</h3>
              </div>
              <ul className="violation-list">
                {(resultData.safety_violations || resultData.safety_analysis?.violations_detected || []).map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </div>

            <div className="glass card full-width">
              <div className="card-header">
                <AlertCircle size={24} color="var(--warning, #f59e0b)" />
                <h3>Missing Steps / Feedback</h3>
              </div>
              <ul className="feedback-list">
                {(resultData.missing_steps || resultData.skill_gap_analysis?.feedback || []).map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>

            <div className="glass card full-width">
              <div className="card-header">
                <BookOpen size={24} color="var(--success)" />
                <h3>Generated MCQs</h3>
              </div>
              <div className="mcq-list">
                {(resultData.mcqs || resultData.mcq_questions || []).map((mcq, idx) => (
                  <div key={idx} className="mcq-item">
                    <h4>Q{idx + 1}: {mcq.question}</h4>
                    <ul>
                      {mcq.options.map((opt, oIdx) => (
                        <li key={oIdx} className={opt === mcq.answer ? 'correct-answer' : ''}>
                          {opt} {opt === mcq.answer && '✓'}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
