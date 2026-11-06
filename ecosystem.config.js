module.exports = {
  apps: [
    {
      name: "lwi-backend",
      script: "gunicorn",
      args: "--bind 127.0.0.1:5000 app:app", 
      interpreter: "./venv/bin/python",
      env: {
        NODE_ENV: "production",
      },
    },
  ],
};