# path aider\aider\api.py
import flask
import tiktoken
from flask import Flask, request, jsonify
from aider.commands import Commands
app = Flask(__name__)


class API:
    def __init__(self, io, coder):
        print("API is starting... 1")
        self.tokenizer = tiktoken.encoding_for_model(coder.main_model.name)
        self.app = app
        self.app.config['io'] = io
        self.app.config['coder'] = coder
    @app.route('/message', methods=['POST'])
    @staticmethod
    def api_message():
        print("API is handling message...")
        # Access class instance through Flask's application context
        api_instance = flask.current_app.config['api_instance']
        coder = flask.current_app.config['coder']

        args = request.json.get('args', '')

        coder.send_new_user_message(args)

        result = coder.partial_response_content

        return jsonify(result=result)

    @app.route('/add', methods=['POST'])
    @staticmethod
    def api_add():
        print("API is handling message...")
        # Access class instance through Flask's application context
        api_instance = flask.current_app.config['api_instance']
        io = flask.current_app.config['io']
        coder = flask.current_app.config['coder']

        args = request.json.get('args', '')
        commands = Commands(io, coder)
        result = commands.run(f'/add {args}')
        return jsonify(result=result)

    @app.route('/drop', methods=['POST'])
    @staticmethod
    def api_drop():
        print("API is handling message drop...")
        # Access class instance through Flask's application context
        api_instance = flask.current_app.config['api_instance']
        io = flask.current_app.config['io']
        coder = flask.current_app.config['coder']
        args = request.json.get('args', '')
        commands = Commands(io, coder)
        result = commands.run(f'/drop {args}')
        return jsonify(result=result)

if __name__ == "__main__":
    app.run(port=5000)
