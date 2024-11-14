from aider.api.app import create_app
import os

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv('AIDER_API_PORT', 5000))
    debug = os.getenv('AIDER_API_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, port=port)
