const express = require('express');
const cors = require('cors');
const queryRoutes = require('./routes/query.routes');
const logger = require('./utils/logger');

const app = express();

const FRONTEND_ORIGIN = process.env.FRONTEND_ORIGIN || '*';
const allowedOrigins = FRONTEND_ORIGIN.split(',').map(o => o.trim());

app.use(cors({
  origin: allowedOrigins.includes('*') ? '*' : allowedOrigins
}));
app.use(express.json());

// Request logging middleware with response time tracking
app.use((req, res, next) => {
  const start = Date.now();
  const { method, originalUrl, url, body } = req;
  const path = originalUrl || url;

  if (method !== 'GET' && body && Object.keys(body).length) {
    logger.debug(`${method} ${path} — body:`, JSON.stringify(body).slice(0, 200));
  } else {
    logger.info(`${method} ${path}`);
  }

  res.on('finish', () => {
    const ms = Date.now() - start;
    logger.http(method, path, res.statusCode, ms);
  });

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
