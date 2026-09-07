import React from 'react';

export default function DBStatusPanel({ onTriggerGc, isGcLoading, gcSummary, gcError, healthStatus }) {
  return (
    <div className="db-status-panel">
      <div className="panel-header">
        <div className="panel-title-group">
          <span className="pulse-dot green"></span>
          <h3 className="panel-title">System & Memory Maintenance</h3>
        </div>
        {healthStatus && (
          <div className="health-tag">
            <span className="health-backend">API: {healthStatus.backend}</span>
            <span className="health-divider">|</span>
            <span className="health-model">
              Model: {healthStatus.modelService?.status || 'unknown'}
            </span>
          </div>
        )}
      </div>

      <div className="panel-content">
        <p className="panel-desc">
          Trigger background garbage collection & storage compaction to move obsolete embeddings to cold storage.
        </p>

        <div className="gc-action-row">
          <button
            type="button"
            className="gc-trigger-btn"
            onClick={onTriggerGc}
            disabled={isGcLoading}
          >
            {isGcLoading ? (
              <>
                <span className="btn-spinner"></span> Running Compaction...
              </>
            ) : (
              '⚡ Run Garbage Collection'
            )}
          </button>
        </div>

        {gcError && (
          <div className="gc-error-msg">
            ⚠️ {gcError}
          </div>
        )}

        {gcSummary && (
          <div className="gc-metrics-grid">
            <div className="metric-card">
              <span className="metric-value">{gcSummary.obsolete_archived ?? 0}</span>
              <span className="metric-label">Obsolete Archived</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">{gcSummary.old_versions_archived ?? 0}</span>
              <span className="metric-label">Old Versions Archived</span>
            </div>
            <div className="metric-card">
              <span className="metric-value">{gcSummary.duplicates_removed ?? 0}</span>
              <span className="metric-label">Duplicates Removed</span>
            </div>
            <div className="metric-card metric-card-highlight">
              <span className="metric-value">{gcSummary.total_active_remaining ?? 0}</span>
              <span className="metric-label">Active Chunks Remaining</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
