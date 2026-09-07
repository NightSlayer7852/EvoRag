const modelServiceClient = require('../services/modelServiceClient');

exports.handleQuery = async (req, res, next) => {
  try {
    const { query } = req.body || {};
    if (!query || typeof query !== 'string' || !query.trim()) {
      return res.status(400).json({ error: 'Query must be a non-empty string.' });
    }

    const result = await modelServiceClient.postQuery(query);
    return res.json(result);
  } catch (error) {
    const status = error.status || 502;
    return res.status(status).json({ error: error.message || 'Model service request failed' });
  }
};

exports.handleHealth = async (req, res, next) => {
  try {
    const modelHealth = await modelServiceClient.getHealth();
    return res.json({
      status: 'ok',
      backend: 'healthy',
      modelService: modelHealth
    });
  } catch (error) {
    return res.status(502).json({
      status: 'degraded',
      backend: 'healthy',
      modelService: { status: 'unreachable', error: error.message }
    });
  }
};

exports.handleGcTrigger = async (req, res, next) => {
  try {
    const gcSummary = await modelServiceClient.postGcRun();
    return res.json(gcSummary);
  } catch (error) {
    const status = error.status || 502;
    return res.status(status).json({ error: error.message || 'GC run execution failed' });
  }
};
