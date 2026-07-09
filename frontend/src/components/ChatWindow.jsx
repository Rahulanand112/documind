import React, { useEffect, useRef } from 'react'

export default function ChatWindow({ messages, loading }) {
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  return (
    <div className="chat-scroll" ref={scrollRef}>
      {messages.length === 0 && (
        <div className="empty-state">
          <div className="glyph">§</div>
          <p>Upload a document on the left, then ask anything about it here.
          Every answer is grounded in your files, with sources cited below the response.</p>
        </div>
      )}

      {messages.map((msg, i) => (
        <div key={i} className={`msg ${msg.role}`}>
          {msg.role === 'user' ? (
            msg.text
          ) : (
            <>
              <div className="answer-text">{msg.text}</div>
              {msg.sources && msg.sources.length > 0 && (
                <div className="sources">
                  {msg.sources.map((s, j) => (
                    <span key={j} className="source-tag">
                      {s.filename}{s.page ? ` · p.${s.page}` : ''}
                    </span>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      ))}

      {loading && (
        <div className="msg assistant">
          <div className="answer-text thinking-dots">Reading your documents</div>
        </div>
      )}
    </div>
  )
}
