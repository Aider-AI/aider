import os
from pathlib import Path
import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_restx import Api, Resource, fields
from aider.coders import Coder
from aider.io import InputOutput
from aider.models import Model
from dotenv import load_dotenv, set_key, find_dotenv
from queue import Queue

def create_app():
    # Load environment variables from aider.env file in the user's home directory
    dotenv_path = os.path.join(str(Path.home()), 'aider.env')
    load_dotenv(dotenv_path)

    app = Flask(__name__)
    app.config['ENV_FILE'] = dotenv_path
    api = Api(app, version='1.0', title='Aider API',
              description='API for Aider - AI pair programming in your terminal',
              doc='/swagger')  # Move Swagger UI to /swagger

    # Set up Aider configuration from environment variables
    app.config['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')
    app.config['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')
    app.config['AIDER_MODEL'] = os.getenv('AIDER_MODEL', 'gpt-3.5-turbo')
    app.config['AIDER_API_PORT'] = int(os.getenv('AIDER_API_PORT', '5000'))
    app.config['AIDER_API_DEBUG'] = os.getenv('AIDER_API_DEBUG', 'False').lower() == 'true'

    # Create a queue for storing the latest question and response
    app.config['QUESTION_QUEUE'] = Queue(maxsize=1)
    app.config['RESPONSE_QUEUE'] = Queue(maxsize=1)

    chat_model = api.model('ChatInput', {
        'message': fields.String(required=True, description='The message to send to the AI'),
        'files': fields.List(fields.String, description='List of files to include in the chat')
    })

    chat_response = api.model('ChatResponse', {
        'response': fields.String(description='The AI response'),
        'edited_files': fields.List(fields.String, description='List of files edited by the AI')
    })

    question_response = api.model('QuestionResponse', {
        'question': fields.String(description='The latest question from the AI'),
        'response': fields.String(description='The latest response from the AI')
    })

    user_response = api.model('UserResponse', {
        'response': fields.String(required=True, description='The user\'s response to the AI\'s question')
    })

    @app.route('/')
    @app.route('/index')
    def home():
        return render_template('home.html')

    @app.route('/swagger')
    def swagger():
        return render_template('swagger.html')

    @app.route('/config')
    def config():
        current_config = {
            'api_provider': 'openai' if app.config['OPENAI_API_KEY'] else 'anthropic',
            'openai_api_key': app.config['OPENAI_API_KEY'],
            'openai_model': app.config['AIDER_MODEL'] if app.config['OPENAI_API_KEY'] else '',
            'anthropic_api_key': app.config['ANTHROPIC_API_KEY'],
            'anthropic_model': app.config['AIDER_MODEL'] if app.config['ANTHROPIC_API_KEY'] else '',
            'aider_api_port': app.config['AIDER_API_PORT'],
            'aider_api_debug': str(app.config['AIDER_API_DEBUG'])
        }
        return render_template('index.html', config=current_config)

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404

    @app.route('/update_config', methods=['POST'])
    def update_config():
        api_provider = request.form.get('api_provider')
        openai_api_key = request.form.get('openai_api_key')
        openai_model = request.form.get('openai_model')
        anthropic_api_key = request.form.get('anthropic_api_key')
        anthropic_model = request.form.get('anthropic_model')
        aider_api_port = request.form.get('aider_api_port')
        aider_api_debug = request.form.get('aider_api_debug')

        env_file = app.config['ENV_FILE']
        if api_provider == 'openai':
            set_key(env_file, 'OPENAI_API_KEY', openai_api_key)
            set_key(env_file, 'AIDER_MODEL', openai_model)
            set_key(env_file, 'ANTHROPIC_API_KEY', '')
            app.config['OPENAI_API_KEY'] = openai_api_key
            app.config['AIDER_MODEL'] = openai_model
            app.config['ANTHROPIC_API_KEY'] = ''
        else:
            set_key(env_file, 'ANTHROPIC_API_KEY', anthropic_api_key)
            set_key(env_file, 'AIDER_MODEL', anthropic_model)
            set_key(env_file, 'OPENAI_API_KEY', '')
            app.config['ANTHROPIC_API_KEY'] = anthropic_api_key
            app.config['AIDER_MODEL'] = anthropic_model
            app.config['OPENAI_API_KEY'] = ''

        set_key(env_file, 'AIDER_API_PORT', aider_api_port)
        set_key(env_file, 'AIDER_API_DEBUG', aider_api_debug)
        app.config['AIDER_API_PORT'] = int(aider_api_port)
        app.config['AIDER_API_DEBUG'] = aider_api_debug.lower() == 'true'

        # Reload environment variables
        load_dotenv(env_file)

        return redirect(url_for('config'))

    @app.route('/index')
    def index():
        return render_template('home.html')

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
            model = Model(app.config['AIDER_MODEL'])
            
            # Set the API keys as environment variables
            os.environ['OPENAI_API_KEY'] = app.config['OPENAI_API_KEY']
            os.environ['ANTHROPIC_API_KEY'] = app.config['ANTHROPIC_API_KEY']
            
            coder = Coder.create(
                io=io,
                main_model=model
            )

            for file in files:
                coder.add_rel_fname(file)

            response = coder.run(with_message=message)

            # Store the latest question and response
            if app.config['QUESTION_QUEUE'].full():
                app.config['QUESTION_QUEUE'].get()
            app.config['QUESTION_QUEUE'].put(message)

            if app.config['RESPONSE_QUEUE'].full():
                app.config['RESPONSE_QUEUE'].get()
            app.config['RESPONSE_QUEUE'].put(response)

            return {
                'response': response,
                'edited_files': list(coder.aider_edited_files)
            }

    @api.route('/change_directory')
    class ChangeDirectory(Resource):
        change_dir_model = api.model('ChangeDirectoryInput', {
            'new_directory': fields.String(required=True, description='The new working directory path')
        })

        @api.expect(change_dir_model)
        def post(self):
            """Change the local working directory"""
            data = request.json
            new_directory = data.get('new_directory')

            try:
                os.chdir(new_directory)
                return {'message': f'Changed working directory to {new_directory}', 'success': True}, 200
            except FileNotFoundError:
                return {'message': f'Directory not found: {new_directory}', 'success': False}, 404
            except PermissionError:
                return {'message': f'Permission denied: {new_directory}', 'success': False}, 403
            except Exception as e:
                return {'message': f'Error changing directory: {str(e)}', 'success': False}, 500

    @api.route('/latest')
    class Latest(Resource):
        @api.marshal_with(question_response)
        def get(self):
            """Get the latest question and response"""
            question = app.config['QUESTION_QUEUE'].queue[0] if not app.config['QUESTION_QUEUE'].empty() else None
            response = app.config['RESPONSE_QUEUE'].queue[0] if not app.config['RESPONSE_QUEUE'].empty() else None
            return {'question': question, 'response': response}

    @api.route('/respond')
    class Respond(Resource):
        @api.expect(user_response)
        @api.marshal_with(chat_response)
        def post(self):
            """Send a response to the AI's question"""
            data = request.json
            user_response = data.get('response')

            io = InputOutput(pretty=False)
            model = Model(app.config['AIDER_MODEL'])
            
            coder = Coder.create(
                io=io,
                main_model=model
            )

            response = coder.run(with_message=user_response)

            if app.config['RESPONSE_QUEUE'].full():
                app.config['RESPONSE_QUEUE'].get()
            app.config['RESPONSE_QUEUE'].put(response)

            return {
                'response': response,
                'edited_files': list(coder.aider_edited_files)
            }

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
