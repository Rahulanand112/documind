import React, { useEffect, useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import { uploadDocument, fetchDocuments, deleteDocument, askQuestion } from './api.js'

export default function App() {
  const [documents, setDocuments] = useState([])
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [uploading, setUploading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadDocuments = async () => {
    try {
      const data = await fetchDocuments()
      setDocuments(data.documents || [])
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => {
    loadDocuments()
  }, [])

  const handleUpload = async (file) => {
    setUploading(true)
    setError(null)
    try {
      await uploadDocument(file)
      await loadDocuments()
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (docId) => {
    try {
      await deleteDocument(docId)
      await loadDocuments()
    } catch (e) {
      setError(e.message)
    }
  }

  const handleAsk = async (e) => {
    e.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    // Send prior turns as history so follow-up questions (e.g. "what about
    // his projects?") can be understood in context by the backend.
    const historyForRequest = messages.map(({ role, text }) => ({ role, text }))

    setMessages((prev) => [...prev, { role: 'user', text: question }])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const result = await askQuestion(question, historyForRequest)
      setMessages((prev) => [...prev, { role: 'assistant', text: result.answer, sources: result.sources }])
    } catch (e) {
      setError(e.message)
      setMessages((prev) => [...prev, { role: 'assistant', text: `Something went wrong: ${e.message}`, sources: [] }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand">DocuMind <span className="mark">/rag</span></div>
        <div className="tagline">Ask questions, get answers grounded in your own documents — with sources cited.</div>
      </header>

      <div className="main-layout">
        <Sidebar
          documents={documents}
          onUpload={handleUpload}
          onDelete={handleDelete}
          uploading={uploading}
        />

        <div className="chat-column">
          {error && <div className="status-banner error" style={{ margin: '16px 40px 0' }}>{error}</div>}
          <ChatWindow messages={messages} loading={loading} />
          <form className="chat-input-bar" onSubmit={handleAsk}>
            <input
              type="text"
              placeholder="Ask something about your documents..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={documents.length === 0}
            />
            <button type="submit" disabled={loading || documents.length === 0}>
              Ask
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
