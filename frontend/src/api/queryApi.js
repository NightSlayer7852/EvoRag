import axios from 'axios';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

function normalizeError(error) {
  if (error.response) {
    const message = error.response.data?.error || error.response.data?.message || `Server error (${error.response.status})`;
    return { message };
  } else if (error.request) {
    return { message: 'Cannot connect to backend server. Make sure Node.js backend is running at ' + BACKEND_URL };
  } else {
    return { message: error.message || 'An unexpected error occurred' };
  }
}

export async function submitQuery(queryText) {
  try {
    const response = await axios.post(`${BACKEND_URL}/query`, { query: queryText });
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function checkHealth() {
  try {
    const response = await axios.get(`${BACKEND_URL}/health`);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}

export async function triggerGc() {
  try {
    const response = await axios.post(`${BACKEND_URL}/gc/run`);
    return response.data;
  } catch (error) {
    throw normalizeError(error);
  }
}
