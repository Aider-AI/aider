from flask import Flask, request, jsonify
from aider.coders import Coder
from aider.io import InputOutput

def create_app():
    app = Flask(__name__)

    @app.route('/chat', methods=['POST'])
    def chat():
        data = request.json
        message = data.get('message')
        files = data.get('files', [])

        io = InputOutput(pretty=False)
        coder = Coder.create(io=io)

        for file in files:
            coder.add_rel_fname(file)

        response = coder.run(with_message=message)

        return jsonify({
            'response': response,
            'edited_files': list(coder.aider_edited_files)
        })

    return app
