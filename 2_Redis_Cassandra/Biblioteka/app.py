from flask import Flask, jsonify
from flask_cors import CORS
from flasgger import Swagger

from Biblioteka.routes.auth_routes import auth_bp
from Biblioteka.routes.books_routes import books_bp
from Biblioteka.routes.copies_routes import copies_bp
from Biblioteka.routes.users_routes import users_bp
from Biblioteka.routes.reservations_routes import reservations_bp
from Biblioteka.routes.branches_routes import branches_bp
from Biblioteka.routes.aggregate_routes import aggregate_bp
from Biblioteka.routes.logs_routes import logs_bp

# -------------------------------
# App Configuration
# -------------------------------
app = Flask(__name__)
CORS(app)

# -------------------------------
# Swagger Configuration
# -------------------------------
swagger = Swagger(app, template={
    "info": {
        "title": "📚 Biblioteka API",
        "description": "Interactive documentation for the library database",
        "version": "1.0.0",
        "contact": {
            "name": "Your Name",
            "email": "you@example.com"
        }
    },
    # Force section order
    "tags": [
        {"name": "Authentication", "description": "Login endpoints for readers and admins"},
        {"name": "Books", "description": "Endpoints for viewing and managing books"},
        {"name": "Reservations", "description": "Endpoints for creating and managing reservations"},
        {"name": "Users", "description": "Endpoints for managing library users"},
        {"name": "Copies", "description": "Endpoints for managing book copies"},
        {"name": "Branches", "description": "Endpoint for checking library name and number"},
        {"name": "Aggregations", "description": "Endpoints for aggregate functions"},
        {"name": "Logs", "description": "Endpoints for checking what the logs look like"}
    ],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Add 'Bearer <your JWT token>' here."
        }
    },
    "security": [{"Bearer": []}]
})

# -------------------------------
# Register Blueprints
# -------------------------------
app.register_blueprint(auth_bp)
app.register_blueprint(books_bp)
app.register_blueprint(reservations_bp)
app.register_blueprint(users_bp)
app.register_blueprint(branches_bp)
app.register_blueprint(copies_bp)
app.register_blueprint(aggregate_bp)
app.register_blueprint(logs_bp)

# -------------------------------
# Run Server
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)
