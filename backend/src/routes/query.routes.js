const express = require('express');
const router = express.Router();
const queryController = require('../controllers/query.controller');

// POST /query endpoint
router.post('/query', queryController.handleQuery);

module.exports = router;
