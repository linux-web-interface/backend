module.exports = {
  apps: [
    {
      name: "lwi-backend",
      script: "venv/bin/python",
      args: "app.py",
      interpreter: "",
      cwd: "/opt/lwi-be",
      instances: 1,
      autorestart: true,
      env: {
        FLASK_ENV: "production",
        PORT: 5000,
      },
    },
    {
      name: "lwi-scanner",
      script: "venv/bin/python",
      args: "-m workers.scanner_worker",
      interpreter: "",
      cwd: "/opt/lwi-be",
      instances: 1,
      autorestart: false,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
  ],
};
