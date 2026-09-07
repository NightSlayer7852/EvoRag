import React from 'react';

export default function AnswerDisplay({ answer, isLoading, error }) {
  if (isLoading) {
    return (
      <div className="answer-card loading-card">
        <div className="loading-spinner"></div>
        <p className="loading-text">Analyzing query with LangGraph retrieval pipeline...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="answer-card error-card">
        <div className="error-icon">⚠️</div>
        <div className="error-body">
          <h4 className="error-title">Execution Error</h4>
          <p className="error-message">{error}</p>
        </div>
      </div>
    );
  }

  if (!answer) {
    return null;
  }

  return (
    <div className="answer-card success-card">
      <h3 className="answer-header">Synthesized Response</h3>
      <div className="answer-content">
        {answer.split('\n').map((paragraph, idx) => (
          <p key={idx}>{paragraph}</p>
        ))}
      </div>
    </div>
  );
}
