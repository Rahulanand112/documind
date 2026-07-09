import React, { useRef, useState } from 'react'

export default function Sidebar({ documents, onUpload, onDelete, uploading }) {
  const fileInputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = (files) => {
    if (files && files[0]) {
      onUpload(files[0])
    }
  }

  return (
    <aside className="sidebar">
      <div className="section-label">Library</div>

      <div
        className={`upload-zone ${dragging ? 'dragging' : ''}`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFiles(e.dataTransfer.files)
        }}
      >
        {uploading ? (
          <span className="thinking-dots">Indexing document</span>
        ) : (
          <>Drop a PDF or .txt file here, or click to browse</>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      {documents.length === 0 ? (
        <p className="empty-note">
          Nothing indexed yet. Upload a document to start asking questions grounded in its content.
        </p>
      ) : (
        <ul className="doc-list">
          {documents.map((doc) => (
            <li key={doc.doc_id} className="doc-item">
              <span className="doc-name" title={doc.filename}>{doc.filename}</span>
              <button onClick={() => onDelete(doc.doc_id)} aria-label={`Remove ${doc.filename}`}>×</button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
