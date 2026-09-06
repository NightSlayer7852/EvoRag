import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

export async function sendQuery(queryText) {
  const response = await axios.post(`${API_BASE_URL}/query`, { query: queryText });
  return response.data;
}
