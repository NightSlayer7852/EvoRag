const axios = require('axios');
const { modelServiceUrl } = require('../config/db.config');
const logger = require('../utils/logger');

const MODEL_SERVICE_URL = modelServiceUrl;

/**
 * Helper to normalize Axios errors into a clean object with status and message.
 */
function normalizeError(error) {
  if (error.response) {
    const status = error.response.status;
    const message = error.response.data?.detail || error.response.data?.message || error.response.statusText || 'Model service error';
    logger.error(`[ModelClient] HTTP ${status} from model service — ${message}`);
    return { status, message };
  } else if (error.request) {
    logger.error(`[ModelClient] No response from model service at ${MODEL_SERVICE_URL} — is FastAPI running?`);
    return { status: 502, message: 'Model service unreachable. Ensure FastAPI server is running.' };
  } else {
    logger.error(`[ModelClient] Request setup error: ${error.message}`);
    return { status: 500, message: error.message || 'Internal client error' };
  }
}

async function postQuery(query) {
  logger.debug(`[ModelClient] → POST ${MODEL_SERVICE_URL}/query | query: "${query.slice(0, 80)}${query.length > 80 ? '...' : ''}"`);
  const t = Date.now();
  try {
    const response = await axios.post(`${MODEL_SERVICE_URL}/query`, { query });
    logger.success(`[ModelClient] ← /query responded in ${Date.now() - t}ms | used_rag=${response.data.used_rag} used_web=${response.data.used_web} confidence=${response.data.confidence_score}`);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

async function getHealth() {
  logger.debug(`[ModelClient] → GET ${MODEL_SERVICE_URL}/health`);
  const t = Date.now();
  try {
    const response = await axios.get(`${MODEL_SERVICE_URL}/health`);
    logger.success(`[ModelClient] ← /health OK (${Date.now() - t}ms) | status=${response.data.status}`);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

async function postGcRun() {
  logger.debug(`[ModelClient] → POST ${MODEL_SERVICE_URL}/gc/run`);
  const t = Date.now();
  try {
    const response = await axios.post(`${MODEL_SERVICE_URL}/gc/run`);
    logger.success(`[ModelClient] ← /gc/run completed in ${Date.now() - t}ms`);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

module.exports = {
  postQuery,
  getHealth,
  postGcRun
};
