const express = require('express');
const queryRoutes = require('./routes/query.routes');

const app = express();

app.use(express.json());
app.use('/api', queryRoutes);

module.exports = app;
