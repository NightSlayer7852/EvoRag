import React, { useState } from 'react';

export default function QueryInput({ onSubmit, isLoading }) {
  const [inputQuery, setInputQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputQuery.trim() || isLoading) return;
    onSubmit(inputQuery.trim());
  };

  return (
    <form className="query-input-form" onSubmit={handleSubmit}>
      <div className="input-group">
        <input
          type="text"
          className="query-input-field"
          placeholder="Ask EvoRAG anything (e.g. What is quantum computing?)"
          value={inputQuery}
          onChange={(e) => setInputQuery(e.target.value)}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="query-submit-btn"
          disabled={isLoading || !inputQuery.trim()}
        >
          {isLoading ? (
            <span className="btn-spinner-text">Processing...</span>
          ) : (
            <span>Ask EvoRAG</span>
          )}
        </button>
      </div>
    </form>
  );
}
