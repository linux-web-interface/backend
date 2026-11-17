from flask import Flask, Blueprint
from flask_cors import CORS
from api.browse_routes import browseBp


app = Flask(__name__)
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": ["http://localhost:5173", r"http://[a-zA-Z0-9-]+\.local(?::\d+)?"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    }
)

app.register_blueprint(browseBp, url_prefix="/api")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
