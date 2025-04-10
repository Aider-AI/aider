import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from aider.server import create_app


class TestServer(unittest.TestCase):
    def setUp(self):
        # Create a mock coder
        self.mock_coder = MagicMock()
        self.mock_coder.run_stream.return_value = ["Hello", " from", " stream", " response"]
        self.mock_coder.run.return_value = "Hello from non-stream response"

        # Create a test client using the mock coder
        self.app = create_app(self.mock_coder)
        self.client = TestClient(self.app)

    def test_chat_streaming(self):
        # Test streaming API endpoint
        data = {"message": "Hello", "stream": True}

        response = self.client.post("/chat", json=data)
        self.assertEqual(response.status_code, 200)

        # Verify the coder's run_stream method was called with the correct args
        self.mock_coder.run_stream.assert_called_once_with(data["message"])

        # Check response content
        content = response.content.decode()
        self.assertTrue(len(content) > 0)
        # The response should contain the concatenated stream
        self.assertEqual("Hello from stream response", content)

    def test_chat_no_streaming(self):
        # Test non-streaming API endpoint
        data = {"message": "Hello", "stream": False}

        response = self.client.post("/chat", json=data)
        self.assertEqual(response.status_code, 200)

        # Verify the coder's run method was called with the correct args
        self.mock_coder.run.assert_called_once_with(with_message=data["message"])

        # Verify response structure
        response_json = response.json()
        self.assertIn("content", response_json)
        self.assertEqual(response_json["content"], "Hello from non-stream response")


if __name__ == "__main__":
    unittest.main()
