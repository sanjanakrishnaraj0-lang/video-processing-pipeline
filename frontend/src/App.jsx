import { useState, useRef, useEffect } from 'react'
import axios from 'axios'
import { Upload, FileVideo, FileText, Image, CheckCircle, AlertCircle, Loader2, PlaySquare, ShieldAlert, BookOpen, GraduationCap } from 'lucide-react'
import './App.css'

const getFileIcon = (fileName) => {
  if (!fileName) return <FileText size={40} color="var(--accent)" />;
  const ext = fileName.substring(fileName.lastIndexOf('.')).toLowerCase();
  if (['.mp4', '.avi', '.mov', '.mkv', '.webm'].includes(ext)) {
    return <FileVideo size={40} color="var(--accent)" />;
  }
  if (['.jpg', '.jpeg', '.png'].includes(ext)) {
    return <Image size={40} color="var(--accent)" />;
  }
  return <FileText size={40} color="var(--accent)" />;
};

const isVideoFile = (fileObj, urlStr) => {
  if (fileObj) {
    const ext = fileObj.name.substring(fileObj.name.lastIndexOf('.')).toLowerCase();
    return ['.mp4', '.avi', '.mov', '.mkv', '.webm'].includes(ext);
  }
  if (urlStr) {
    const ext = urlStr.substring(urlStr.lastIndexOf('.')).toLowerCase();
    return ['.mp4', '.avi', '.mov', '.mkv', '.webm'].includes(ext) || urlStr.toLowerCase().includes('video');
  }
  return false;
};

function App() {
  const [file, setFile] = useState(null)
  const [videoUrl, setVideoUrl] = useState('')
  const [goldenStandard, setGoldenStandard] = useState('')
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
          const { data } = await axios.get(`http://localhost:8001/result/${videoId}`)
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
      const allowedExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.pdf', '.docx', '.doc', '.txt', '.xlsx', '.xls', '.csv', '.jpg', '.jpeg', '.png']
      const fileExt = droppedFile.name.substring(droppedFile.name.lastIndexOf('.')).toLowerCase()
      if (droppedFile.type.startsWith('video/') || droppedFile.type.startsWith('image/') || allowedExtensions.includes(fileExt)) {
        setFile(droppedFile)
        setStatus({ type: '', message: '' })
      } else {
        setStatus({ type: 'error', message: 'Unsupported file format. Please upload a video, document (PDF, DOCX, Excel, CSV, Text), or image (JPG, PNG).' })
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
    if (!file && !videoUrl.trim()) return

    setIsUploading(true)
    setUploadProgress(0)
    setStatus({ type: '', message: '' })
    setResultData(null)

    try {
      if (file) {
        const formData = new FormData()
        formData.append('file', file)
        formData.append('user_id', 'user_demo')
        if (goldenStandard) {
          formData.append('golden_standard', goldenStandard)
        }

        const { data } = await axios.post('http://localhost:8001/upload/generic', formData, {

          headers: { 'Content-Type': 'multipart/form-data' },
          onUploadProgress: (progressEvent) => {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            setUploadProgress(percentCompleted)
          }
        })

        if (data.status === 'success') {
          setVideoId(data.job_id)
          setIsProcessing(true)
          setStatus({ 
            type: 'success', 
            message: 'Video uploaded successfully! The AI is now analyzing it...' 
          })
        }
      } else {
        const { data } = await axios.post('http://localhost:8001/upload-url', {
          video_url: videoUrl,
          user_id: 'user_demo',
          golden_standard: goldenStandard || null
        })

        if (data.status === 'success') {
          setVideoId(data.job_id)
          setIsProcessing(true)
          setStatus({ 
            type: 'success', 
            message: 'Video URL submitted successfully! The AI is now analyzing it...' 
          })
        }
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
    setVideoUrl('')
    setVideoId(null)
    setResultData(null)
    setGoldenStandard('')
    setStatus({ type: '', message: '' })
  }

  return (
    <div className="app-container">
      <header className="header animate-fade-in">
        <h1>Kovon AI</h1>
        <p>Upload a training video, resume, or report for dynamic AI analysis</p>
      </header>

      {!resultData ? (
        <div className="glass upload-card animate-fade-in" style={{ animationDelay: '0.1s' }}>
          
          {file ? (
            <div className="selected-file">
              {getFileIcon(file.name)}
              <div className="file-info">
                <span className="file-name">{file.name}</span>
                <span className="file-size">{formatFileSize(file.size)}</span>
              </div>
              {!isUploading && !isProcessing && (
                <button 
                  onClick={() => setFile(null)} 
                  className="btn-remove"
                >
                  ✕
                </button>
              )}
            </div>
          ) : (
            <div 
              className={`upload-area ${isDragging ? 'active' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="upload-icon" size={48} />
              <div className="upload-text">
                <h3>Drag & Drop your file here</h3>
                <p>or click to browse from your computer</p>
                <small style={{ opacity: 0.6, display: 'block', marginTop: '8px' }}>
                  Supports PDF, DOCX, Excel, CSV, Text, Images, and Videos
                </small>
              </div>
              <input 
                type="file" 
                className="file-input" 
                style={{ display: 'none' }}
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept="video/*,image/*,application/pdf,.docx,.doc,.txt,.xlsx,.xls,.csv"
              />
            </div>
          )}

          {!file && !isProcessing && (
            <>
              <div className="or-divider">— OR —</div>

              <div className="url-input-container">
                <input 
                  type="text" 
                  className="url-input"
                  placeholder="Paste S3 Video URL here..." 
                  value={videoUrl}
                  onChange={(e) => setVideoUrl(e.target.value)}
                  disabled={isUploading}
                />
              </div>
            </>
          )}

          {(file || videoUrl.trim()) && !isProcessing && (
            <div className="select-standard-container">
              <select 
                className="select-standard"
                value={goldenStandard}
                onChange={(e) => setGoldenStandard(e.target.value)}
                disabled={isUploading}
              >
                {isVideoFile(file, videoUrl) ? (
                  <>
                    <option value="">Select a Golden Reference Standard (Video, optional)</option>
                    <option value="plumbing">Plumbing Golden Standard</option>
                    <option value="electrical">Electrical Golden Standard</option>
                    <option value="building_plumbing">Building Plumbing Golden Standard</option>
                  </>
                ) : (
                  <>
                    <option value="">Select a Golden Reference Standard (Resume, optional)</option>
                    <option value="general">General Resume Standard</option>
                    <option value="software_engineer">Software Engineer Golden Standard</option>
                  </>
                )}
              </select>
            </div>
          )}

          {isUploading && uploadProgress > 0 && (
            <div className="progress-wrap">
              <div className="progress-label">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${uploadProgress}%` }}></div>
              </div>
            </div>
          )}

          {!isProcessing && (
            file ? (
              <button 
                className="btn-primary" 
                onClick={handleUpload}
                disabled={isUploading}
              >
                {isUploading ? (
                  <><Loader2 className="animate-spin" size={20} /> Uploading...</>
                ) : (
                  <><PlaySquare size={20} /> Analyze Upload</>
                )}
              </button>
            ) : (
              <button 
                className="btn-primary" 
                onClick={handleUpload}
                disabled={isUploading || !videoUrl.trim()}
              >
                {isUploading ? (
                  <><Loader2 className="animate-spin" size={20} /> Uploading...</>
                ) : (
                  <><PlaySquare size={20} /> Analyze URL</>
                )}
              </button>
            )
          )}

          {isProcessing && (
            <div className="processing-status">
               <Loader2 className="animate-spin icon-large" size={32} color="var(--accent)" />
               <p>AI is currently processing your upload...</p>
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
        (() => {
          const detectedType = resultData.detected_agent_type || 
            (resultData.skill_score !== undefined ? 'video' : 
             resultData.overall_score !== undefined ? 'resume' : 
             resultData.summary !== undefined ? 'report' : 'video');

          return (
            <div className="dashboard-container animate-fade-in">
              <div className="dashboard-header">
                <h2>Analysis Results — {detectedType.toUpperCase()}</h2>
                <button className="btn-secondary" onClick={resetUpload}>Analyze Another File</button>
              </div>

              {detectedType === 'video' && (
                <div className="dashboard-grid">
                  <div className="glass card score-card">
                    <div className="card-header">
                      <GraduationCap size={24} color="var(--accent)" />
                      <h3>Skill Score</h3>
                    </div>
                    <div className="score-value">{resultData.skill_score || 0}/100</div>
                  </div>

                  <div className="glass card">
                    <div className="card-header">
                      <ShieldAlert size={24} color="var(--error)" />
                      <h3>Safety Violations</h3>
                    </div>
                    <ul className="violation-list">
                      {(resultData.safety_violations || []).map((v, i) => (
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
                      {(resultData.missing_steps || []).map((f, i) => (
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
                      {(resultData.mcqs || []).map((mcq, idx) => (
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
              )}

              {detectedType === 'resume' && (
                <div className="dashboard-grid">
                  <div className="glass card score-card">
                    <div className="card-header">
                      <GraduationCap size={24} color="var(--accent)" />
                      <h3>Candidate Score</h3>
                    </div>
                    <div className="score-value">{resultData.overall_score || 0}/100</div>
                  </div>

                  <div className="glass card">
                    <div className="card-header">
                      <CheckCircle size={24} color="var(--success)" />
                      <h3>Recommendation</h3>
                    </div>
                    <div className="recommendation-value" style={{ fontSize: '1.2rem', fontWeight: 'bold', marginTop: '15px', color: 'var(--success)' }}>
                      {resultData.hire_recommendation}
                    </div>
                    <div style={{ marginTop: '15px' }}>
                      <strong>Experience:</strong> {resultData.experience_years} years <br />
                      <strong>Education:</strong> {resultData.education_level}
                    </div>
                  </div>

                  <div className="glass card">
                    <div className="card-header">
                      <GraduationCap size={24} color="var(--accent)" />
                      <h3>Technical Skills</h3>
                    </div>
                    <div className="skills-container" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '15px' }}>
                      {(resultData.technical_skills || []).map((s, i) => (
                        <span key={i} className="badge" style={{ padding: '6px 12px', background: 'rgba(255,255,255,0.08)', borderRadius: '15px', fontSize: '0.9rem' }}>{s}</span>
                      ))}
                    </div>
                  </div>

                  <div className="glass card">
                    <div className="card-header">
                      <BookOpen size={24} color="var(--success)" />
                      <h3>Soft Skills</h3>
                    </div>
                    <div className="skills-container" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '15px' }}>
                      {(resultData.soft_skills || []).map((s, i) => (
                        <span key={i} className="badge" style={{ padding: '6px 12px', background: 'rgba(255,255,255,0.08)', borderRadius: '15px', fontSize: '0.9rem' }}>{s}</span>
                      ))}
                    </div>
                  </div>

                  <div className="glass card">
                    <div className="card-header">
                      <CheckCircle size={24} color="var(--success)" />
                      <h3>Key Strengths</h3>
                    </div>
                    <ul className="feedback-list" style={{ marginTop: '10px' }}>
                      {(resultData.strengths || []).map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="glass card">
                    <div className="card-header">
                      <ShieldAlert size={24} color="var(--error)" />
                      <h3>Red Flags / Concerns</h3>
                    </div>
                    <ul className="violation-list" style={{ marginTop: '10px' }}>
                      {(resultData.red_flags || []).map((rf, i) => (
                        <li key={i}>{rf}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              {detectedType === 'report' && (
                <div className="dashboard-grid">
                  <div className="glass card score-card">
                    <div className="card-header">
                      <GraduationCap size={24} color="var(--accent)" />
                      <h3>Confidence Score</h3>
                    </div>
                    <div className="score-value">{resultData.confidence_score || 0}%</div>
                  </div>

                  <div className="glass card">
                    <div className="card-header">
                      <CheckCircle size={24} color="var(--success)" />
                      <h3>Sentiment Analysis</h3>
                    </div>
                    <div className="recommendation-value" style={{ fontSize: '1.5rem', fontWeight: 'bold', marginTop: '20px', color: 'var(--accent)', textTransform: 'capitalize' }}>
                      {resultData.sentiment}
                    </div>
                  </div>

                  <div className="glass card full-width">
                    <div className="card-header">
                      <BookOpen size={24} color="var(--accent)" />
                      <h3>Executive Summary</h3>
                    </div>
                    <p style={{ marginTop: '15px', lineHeight: '1.6', fontSize: '1.05rem', color: '#ccc' }}>
                      {resultData.summary}
                    </p>
                  </div>

                  <div className="glass card">
                    <div className="card-header">
                      <GraduationCap size={24} color="var(--accent)" />
                      <h3>Key Findings</h3>
                    </div>
                    <ul className="feedback-list" style={{ marginTop: '10px' }}>
                      {(resultData.key_findings || []).map((kf, i) => (
                        <li key={i}>{kf}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="glass card">
                    <div className="card-header">
                      <ShieldAlert size={24} color="var(--error)" />
                      <h3>Identified Risks</h3>
                    </div>
                    <ul className="violation-list" style={{ marginTop: '10px' }}>
                      {(resultData.risks || []).map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="glass card full-width">
                    <div className="card-header">
                      <CheckCircle size={24} color="var(--success)" />
                      <h3>Recommended Actions</h3>
                    </div>
                    <ul className="feedback-list" style={{ marginTop: '10px' }}>
                      {(resultData.recommendations || []).map((rec, i) => (
                        <li key={i}>{rec}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          );
        })()
      )}
    </div>
  )
}

export default App