const express = require('express');
const router = express.Router();
const queryController = require('../controllers/query.controller');

router.post('/query', queryController.handleQuery);
router.get('/health', queryController.handleHealth);
router.post('/gc/run', queryController.handleGcTrigger);

module.exports = router;
