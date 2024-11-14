import os
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_restx import Api, Resource, fields
from aider.coders import Coder
from aider.io import InputOutput
from dotenv import load_dotenv, set_key

def create_app():
    # Load environment variables from .env file
    load_dotenv()

    app = Flask(__name__)
    api = Api(app, version='1.0', title='Aider API',
              description='API for Aider - AI pair programming in your terminal')

    # Set up Aider configuration from environment variables
    openai_api_key = os.getenv('OPENAI_API_KEY')
    anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
    model = os.getenv('AIDER_MODEL')
    aider_api_port = int(os.getenv('AIDER_API_PORT', '5000'))
    aider_api_debug = os.getenv('AIDER_API_DEBUG', 'False').lower() == 'true'

    chat_model = api.model('ChatInput', {
        'message': fields.String(required=True, description='The message to send to the AI'),
        'files': fields.List(fields.String, description='List of files to include in the chat')
    })

    chat_response = api.model('ChatResponse', {
        'response': fields.String(description='The AI response'),
        'edited_files': fields.List(fields.String, description='List of files edited by the AI')
    })

    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/config')
    def config():
        return render_template('index.html')

    @app.route('/update_config', methods=['POST'])
    def update_config():
        api_provider = request.form.get('api_provider')
        openai_api_key = request.form.get('openai_api_key')
        openai_model = request.form.get('openai_model')
        anthropic_api_key = request.form.get('anthropic_api_key')
        anthropic_model = request.form.get('anthropic_model')
        aider_api_port = request.form.get('aider_api_port')
        aider_api_debug = request.form.get('aider_api_debug')

        env_file = '.env'
        if api_provider == 'openai':
            set_key(env_file, 'OPENAI_API_KEY', openai_api_key)
            set_key(env_file, 'AIDER_MODEL', openai_model)
            set_key(env_file, 'ANTHROPIC_API_KEY', '')
        else:
            set_key(env_file, 'ANTHROPIC_API_KEY', anthropic_api_key)
            set_key(env_file, 'AIDER_MODEL', anthropic_model)
            set_key(env_file, 'OPENAI_API_KEY', '')

        set_key(env_file, 'AIDER_API_PORT', aider_api_port)
        set_key(env_file, 'AIDER_API_DEBUG', aider_api_debug)

        return redirect(url_for('index'))

    @api.route('/chat')
    class Chat(Resource):
        @api.expect(chat_model)
        @api.marshal_with(chat_response)
        def post(self):
            """Send a message to the AI and get a response"""
            data = request.json
            message = data.get('message')
            files = data.get('files', [])

            io = InputOutput(pretty=False)
            coder = Coder.create(
                io=io,
                main_model=model,
                openai_api_key=openai_api_key,
                anthropic_api_key=anthropic_api_key
            )

            for file in files:
                coder.add_rel_fname(file)

            response = coder.run(with_message=message)

            return {
                'response': response,
                'edited_files': list(coder.aider_edited_files)
            }

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
