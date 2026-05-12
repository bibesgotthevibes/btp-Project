const fs = require('fs');
let code = fs.readFileSync('frontend/server.js', 'utf8');

code = code.replace(
  "app.use(\n  '/api',\n  createProxyMiddleware({",
  "app.use(\n  '/api', (req, res, next) => { req.url = req.originalUrl; next(); },\n  createProxyMiddleware({"
);

fs.writeFileSync('frontend/server.js', code);
