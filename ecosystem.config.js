module.exports = {
  apps: [
    {
      name: "medsimplify-frontend",
      script: "server.js",
      cwd: "./frontend",
      env: {
        PORT: 80, // Default web port so it loads as domain/ 
        NODE_ENV: "production"
      }
    },
    {
      name: "medsimplify-backend",
      script: "../.venv/bin/gunicorn",
      args: "-w 4 -b 127.0.0.1:5001 app:app",
      cwd: "./backend",
      interpreter: "python3", 
      env: {
        PORT: 5001,
        FLASK_ENV: "production"
      }
    }
  ]
};
