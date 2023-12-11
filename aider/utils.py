from pathlib import Path

# Set of image file extensions
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}

from .dump import dump  # noqa: F401

def is_image_file(file_name):
    """
    Check if the given file name has an image file extension.
    
    :param file_name: The name of the file to check.
    :return: True if the file is an image, False otherwise.
    """
    file_name = str(file_name)  # Convert file_name to string
    return any(file_name.endswith(ext) for ext in IMAGE_EXTENSIONS)


def safe_abs_path(res):
    "Gives an abs path, which safely returns a full (not 8.3) windows path"
    res = Path(res).resolve()
    return str(res)


def show_messages(messages, title=None, functions=None):
    if title:
        print(title.upper(), "*" * 50)

    for msg in messages:
        role = msg["role"].upper()
        content = msg.get("content")
        if isinstance(content, list):  # Handle list content (e.g., image messages)
            for item in content:
                if isinstance(item, dict) and "image_url" in item:
                    print(role, "Image URL:", item["image_url"]["url"])
        elif isinstance(content, str):  # Handle string content
            for line in content.splitlines():
                print(role, line)
        content = msg.get("function_call")
        if content:
            print(role, content)

    if functions:
        dump(functions)

def is_gpt4_with_openai_base_url(model_name, client):
    """
    Check if the model_name starts with 'gpt-4' and the client base URL includes 'api.openai.com'.
    
    :param model_name: The name of the model to check.
    :param client: The OpenAI client instance.
    :return: True if conditions are met, False otherwise.
    """
    if client is None or not hasattr(client, 'base_url'):
        return False
    return model_name.startswith("gpt-4") and "api.openai.com" in client.base_url.host
