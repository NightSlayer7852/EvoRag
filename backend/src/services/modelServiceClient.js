const axios = require('axios');

const MODEL_SERVICE_URL = process.env.MODEL_SERVICE_URL || 'http://localhost:8000';

async function sendQuery(query) {
  const response = await axios.post(`${MODEL_SERVICE_URL}/query`, { query });
  return response.data;
}

module.exports = {
  sendQuery
};
