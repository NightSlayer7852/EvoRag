import axios from 'axios';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

console.info('[EvoRAG] API client initialised — backend:', BACKEND_URL);

function normalizeError(error) {
  if (error.response) {
    const message = error.response.data?.error || error.response.data?.message || `Server error (${error.response.status})`;
    console.error('[EvoRAG API] ✗ HTTP', error.response.status, '—', message, error.response.data);
    return { message };
  } else if (error.request) {
    const message = 'Cannot connect to backend server. Make sure Node.js backend is running at ' + BACKEND_URL;
    console.error('[EvoRAG API] ✗ Network error — no response received. Target:', BACKEND_URL);
    return { message };
  } else {
    console.error('[EvoRAG API] ✗ Request error:', error.message);
    return { message: error.message || 'An unexpected error occurred' };
  }
}

export async function submitQuery(queryText) {
  console.log(`[EvoRAG API] → POST /query | query: "${queryText.slice(0, 80)}${queryText.length > 80 ? '...' : ''}"`);
  const t = Date.now();
  try {
    const response = await axios.post(`${BACKEND_URL}/query`, { query: queryText });
    console.log(`[EvoRAG API] ← /query ${Date.now() - t}ms | used_rag=${response.data.used_rag} used_web=${response.data.used_web} confidence=${response.data.confidence_score}`);
    console.debug('[EvoRAG API] Full response:', response.data);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function checkHealth() {
  console.log('[EvoRAG API] → GET /health');
  const t = Date.now();
  try {
    const response = await axios.get(`${BACKEND_URL}/health`);
    console.log(`[EvoRAG API] ← /health ${Date.now() - t}ms | backend=${response.data.backend} model=${response.data.modelService?.status}`);
    return response.data;
  } catch (error) {
    console.warn('[EvoRAG API] ✗ Health check failed:', error.message);
    throw normalizeError(error);
  }
}

export async function triggerGc() {
  console.log('[EvoRAG API] → POST /gc/run');
  const t = Date.now();
  try {
    const response = await axios.post(`${BACKEND_URL}/gc/run`);
    console.log(`[EvoRAG API] ← /gc/run ${Date.now() - t}ms`, response.data);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}
