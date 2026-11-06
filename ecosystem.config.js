module.exports = {
  apps: [
    {
      name: "lwi-backend",
      script: "venv/bin/python",
      args: "app.py", // Ganti dengan file utama Flask kamu (misal: run.py atau app.py)
      interpreter: "",
      env: {
        FLASK_ENV: "production",
        PORT: 5000
      }
    }
  ]
};