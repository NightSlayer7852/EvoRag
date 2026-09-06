const modelServiceClient = require('../services/modelServiceClient');

exports.handleQuery = async (req, res, next) => {
  try {
    const { query } = req.body;
    const result = await modelServiceClient.sendQuery(query);
    return res.json(result);
  } catch (error) {
    next(error);
  }
};
