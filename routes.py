from flask import jsonify

def register_routes(app):
    @app.route('/users', methods=['GET'])
    def get_users():
        return jsonify({"message": "List of users"})
