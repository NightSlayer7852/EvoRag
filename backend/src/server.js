require('dotenv').config();
const app = require('./app');
const logger = require('./utils/logger');
const { modelServiceUrl } = require('./config/db.config');

const PORT = process.env.PORT || 5000;

app.listen(PORT, () => {
  logger.info(`Backend server running on port ${PORT}`);
  logger.info(`Configured Model Service URL: ${modelServiceUrl}`);
});
