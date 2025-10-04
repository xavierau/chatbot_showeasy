import requests
import json
import uuid

# Assuming the FastAPI server is running at http://127.0.0.1:8000
BASE_URL = "http://127.0.0.1:8000"

def test_chat_endpoint():
    session_id = str(uuid.uuid4())
    user_id = "test_user"
    user_input = "Hello, how are you?"

    payload = {
        "user_input": user_input,
        "user_id": user_id,
        "session_id": session_id
    }

    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)

        # Check if the request was successful
        assert response.status_code == 200

        # Check the response content
        response_data = response.json()
        assert "response" in response_data
        print("Test passed!")
        print(f"Response: {response_data}")

    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {e}")
        print("Please make sure the FastAPI server is running.")

if __name__ == "__main__":
    test_chat_endpoint()
