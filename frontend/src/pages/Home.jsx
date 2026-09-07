import React, { useState, useEffect } from 'react';
import QueryInput from '../components/QueryInput';
import AnswerDisplay from '../components/AnswerDisplay';
import SourceBadge from '../components/SourceBadge';
import DBStatusPanel from '../components/DBStatusPanel';
import { submitQuery, triggerGc, checkHealth } from '../api/queryApi';

export default function Home() {
  const [answerResult, setAnswerResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const [gcSummary, setGcSummary] = useState(null);
  const [isGcLoading, setIsGcLoading] = useState(false);
  const [gcError, setGcError] = useState(null);

  const [healthStatus, setHealthStatus] = useState(null);

  useEffect(() => {
    async function fetchHealth() {
      try {
        const data = await checkHealth();
        setHealthStatus(data);
      } catch (err) {
        setHealthStatus({ status: 'unreachable', backend: 'offline', modelService: { status: 'offline' } });
      }
    }
    fetchHealth();
  }, []);

  const handleSubmit = async (queryText) => {
    setIsLoading(true);
    setError(null);
    setAnswerResult(null);

    try {
      const result = await submitQuery(queryText);
      setAnswerResult(result);
    } catch (err) {
      setError(err.message || 'Failed to generate answer from EvoRAG service');
    } finally {
      setIsLoading(false);
    }
  };

  const handleGcTrigger = async () => {
    setIsGcLoading(true);
    setGcError(null);

    try {
      const summary = await triggerGc();
      setGcSummary(summary);
    } catch (err) {
      setGcError(err.message || 'Failed to execute garbage collection job');
    } finally {
      setIsGcLoading(false);
    }
  };

  return (
    <div className="home-container">
      <header className="app-header">
        <div className="logo-badge">AI Knowledge Engine</div>
        <h1 className="main-title">EvoRAG</h1>
        <p className="subtitle">
          Self-Updating Knowledge Assistant with Hybrid Vector Search & Live Web Synthesis
        </p>
      </header>

      <main className="main-content">
        <DBStatusPanel
          onTriggerGc={handleGcTrigger}
          isGcLoading={isGcLoading}
          gcSummary={gcSummary}
          gcError={gcError}
          healthStatus={healthStatus}
        />

        <section className="search-section">
          <QueryInput onSubmit={handleSubmit} isLoading={isLoading} />
        </section>

        <section className="results-section">
          {answerResult && !isLoading && (
            <SourceBadge
              usedRag={answerResult.used_rag}
              usedWeb={answerResult.used_web}
              confidenceScore={answerResult.confidence_score}
            />
          )}

          <AnswerDisplay
            answer={answerResult?.answer}
            isLoading={isLoading}
            error={error}
          />
        </section>
      </main>

      <footer className="app-footer">
        <p>EvoRAG Architecture — React + Express Orchestration + LangGraph Engine</p>
      </footer>
    </div>
  );
}
