import React from 'react';

export default function SourceBadge({ usedRag, usedWeb, confidenceScore }) {
  if (!usedRag && !usedWeb && confidenceScore === undefined) {
    return null;
  }

  const formattedConfidence = confidenceScore !== undefined && confidenceScore !== null
    ? (confidenceScore <= 1 ? Math.round(confidenceScore * 100) : Math.round(confidenceScore))
    : null;

  return (
    <div className="source-badge-container">
      <span className="badge-label">Sources & Attribution:</span>
      <div className="badge-group">
        {usedRag && (
          <span className="badge badge-rag" title="Knowledge retrieved from active vector database">
            ⚡ RAG Store
          </span>
        )}
        {usedWeb && (
          <span className="badge badge-web" title="Knowledge augmented with live web search">
            🌐 Live Web Search
          </span>
        )}
        {formattedConfidence !== null && (
          <span className="badge badge-confidence" title="Pipeline evaluation confidence score">
            Confidence: {formattedConfidence}%
          </span>
        )}
      </div>
    </div>
  );
}
