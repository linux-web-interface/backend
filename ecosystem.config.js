module.exports = {
  apps: [
    {
      name: "lwi-backend",
      script: "venv/bin/python",
      args: "app.py",
      interpreter: "",
      env: {
        FLASK_ENV: "production",
        PORT: 5000
      }
    }
  ]
};