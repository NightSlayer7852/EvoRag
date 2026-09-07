const express = require('express');
const cors = require('cors');
const queryRoutes = require('./routes/query.routes');
const logger = require('./utils/logger');

const app = express();

const FRONTEND_ORIGIN = process.env.FRONTEND_ORIGIN || '*';

app.use(cors({ origin: FRONTEND_ORIGIN }));
app.use(express.json());

// Request logging middleware
app.use((req, res, next) => {
  logger.info(`${req.method} ${req.originalUrl || req.url}`);
  next();
});

// API Routes
app.use('/api', queryRoutes);

// Global error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled server error:', err);
  const status = err.status || 500;
  return res.status(status).json({
    error: status === 500 ? 'Internal Server Error' : (err.message || 'An error occurred')
  });
});

module.exports = app;
