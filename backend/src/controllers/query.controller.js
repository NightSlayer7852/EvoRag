const modelServiceClient = require('../services/modelServiceClient');
const logger = require('../utils/logger');

exports.handleQuery = async (req, res, next) => {
  const { query } = req.body || {};
  logger.info(`[QueryCtrl] Received query: "${String(query || '').slice(0, 100)}"`);

  if (!query || typeof query !== 'string' || !query.trim()) {
    logger.warn('[QueryCtrl] Rejected — invalid or empty query');
    return res.status(400).json({ error: 'Query must be a non-empty string.' });
  }

  try {
    logger.debug('[QueryCtrl] Forwarding to model service...');
    const result = await modelServiceClient.postQuery(query);
    logger.success(`[QueryCtrl] Answer ready — used_rag=${result.used_rag} used_web=${result.used_web} confidence=${result.confidence_score}`);
    return res.json(result);
  } catch (error) {
    const status = error.status || 502;
    logger.error(`[QueryCtrl] Model service error (${status}): ${error.message}`);
    return res.status(status).json({ error: error.message || 'Model service request failed' });
  }
};

exports.handleHealth = async (req, res, next) => {
  logger.debug('[HealthCtrl] Health check initiated');
  try {
    const modelHealth = await modelServiceClient.getHealth();
    logger.success(`[HealthCtrl] Model service healthy — status: ${modelHealth.status}`);
    return res.json({
      status: 'ok',
      backend: 'healthy',
      modelService: modelHealth
    });
  } catch (error) {
    logger.warn(`[HealthCtrl] Model service unreachable: ${error.message}`);
    return res.status(502).json({
      status: 'degraded',
      backend: 'healthy',
      modelService: { status: 'unreachable', error: error.message }
    });
  }
};

exports.handleGcTrigger = async (req, res, next) => {
  logger.info('[GcCtrl] GC run triggered');
  try {
    const gcSummary = await modelServiceClient.postGcRun();
    logger.success(`[GcCtrl] GC completed — ${JSON.stringify(gcSummary?.summary || gcSummary)}`);
    return res.json(gcSummary);
  } catch (error) {
    const status = error.status || 502;
    logger.error(`[GcCtrl] GC run failed (${status}): ${error.message}`);
    return res.status(status).json({ error: error.message || 'GC run execution failed' });
  }
};
