from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
from aider.coders import Coder
from aider.io import InputOutput

app = Flask(__name__)
api = Api(app, version='1.0', title='Aider API',
          description='API for Aider - AI pair programming in your terminal')

chat_model = api.model('ChatInput', {
    'message': fields.String(required=True, description='The message to send to the AI'),
    'files': fields.List(fields.String, description='List of files to include in the chat')
})

chat_response = api.model('ChatResponse', {
    'response': fields.String(description='The AI response'),
    'edited_files': fields.List(fields.String, description='List of files edited by the AI')
})

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
        coder = Coder.create(io=io)

        for file in files:
            coder.add_rel_fname(file)

        response = coder.run(with_message=message)

        return {
            'response': response,
            'edited_files': list(coder.aider_edited_files)
        }

if __name__ == '__main__':
    app.run(debug=True)
