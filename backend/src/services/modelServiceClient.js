const axios = require('axios');
const { modelServiceUrl } = require('../config/db.config');

const MODEL_SERVICE_URL = modelServiceUrl;

/**
 * Helper to normalize Axios errors into a clean object with status and message.
 */
function normalizeError(error) {
  if (error.response) {
    const status = error.response.status;
    const message = error.response.data?.detail || error.response.data?.message || error.response.statusText || 'Model service error';
    return { status, message };
  } else if (error.request) {
    return { status: 502, message: 'Model service unreachable. Ensure FastAPI server is running.' };
  } else {
    return { status: 500, message: error.message || 'Internal client error' };
  }
}

async function postQuery(query) {
  try {
    const response = await axios.post(`${MODEL_SERVICE_URL}/query`, { query });
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

async function getHealth() {
  try {
    const response = await axios.get(`${MODEL_SERVICE_URL}/health`);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

async function postGcRun() {
  try {
    const response = await axios.post(`${MODEL_SERVICE_URL}/gc/run`);
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
