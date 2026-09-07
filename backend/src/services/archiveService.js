// Note: Direct cold-archive DB operations are managed within the Python model service (model/app/services/archive_service.py).
// This backend acts strictly as an orchestration client forwarding requests to model/.
class ArchiveService {}

module.exports = new ArchiveService();
