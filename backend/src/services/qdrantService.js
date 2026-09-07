// Note: Active vector DB operations are managed within the Python model service (model/app/services/qdrant_service.py).
// This backend acts strictly as an orchestration client forwarding requests to model/.
class QdrantService {}

module.exports = new QdrantService();
