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
      script: "gunicorn",
      args: "-w 4 --access-logfile - -b 127.0.0.1:5001 app:app",
      cwd: "./backend",
      interpreter: "../.venv/bin/python", 
      env: {
        PORT: 5001,
        FLASK_ENV: "production"
      }
    }
  ]
};
