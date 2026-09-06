// Qdrant + Cold-storage DB connection configs
module.exports = {
  qdrantUrl: process.env.QDRANT_URL || 'http://localhost:6333',
  coldStorageUri: process.env.COLD_STORAGE_URI || ''
};
