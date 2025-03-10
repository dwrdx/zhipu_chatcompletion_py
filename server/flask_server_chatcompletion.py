from flask import Flask, request, jsonify, session
from flask_session import Session  # Flask-Session extension
from zhipuai import ZhipuAI
import os
import json
# import tiktoken
from datetime import datetime

app = Flask(__name__)
# Replace with a real secret key
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_TYPE'] = 'filesystem'

# Flask-Session
Session(app)

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
zhipu_client = ZhipuAI(api_key=ZHIPU_API_KEY) # 填写您自己的APIKey


# Constants and Initializations
MAX_ALLOWED_TOKENS = 16384
MODEL_NAME = "glm-4"
BOT_RESPONSE_BUFFER = 500


def initialize_system_context():
    # Initialize system context messages for the conversation, using an example of Streamy™, authorized by mAInstream studIOs LLC (mainstreamstudios.ai)
    system_context = [
        {"role": "system", "content": "你的名字叫灵犀, 是一个大模型AI助手。"},
        {"role": "system", "content": "你会深入思考用户的情况，尽量给出最好的回复和反馈。"},
    ]
    return system_context

@app.before_request
def before_request():
    # Check if 'messages' is not in session or 'init_done' flag is False, then initialize it
    if 'messages' not in session or not session.get('init_done', False):
        session['messages'] = initialize_system_context()
        session['init_done'] = True  # Set the flag to True after initialization

@app.after_request
def after_request(response):
    session.modified = True
    return response

def get_token_count(text):
    return 5
    # return len(enc.encode(text))

def calculate_messages_tokens(messages):
    total_tokens = 0
    for message in messages:
        total_tokens += get_token_count(message['content'])
    return total_tokens

def save_conversation(user_name):
    # Use the user_name from the request to save the file
    filename = f"conversation_{user_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
    with open(filename, 'w') as f:
        json.dump(session['messages'], f, indent=4)
    session.pop('messages', None)  # Clear the messages in session after saving

# Helper function to add messages with the specified role
def add_message(role, content):
    session['messages'].append({"role": role, "content": content})

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    user_input = request.json.get('input')
    user_name = request.json.get('user_name', 'unknown_user')  # Get user_name from the request
    session['user_name'] = user_name  # Save it in the session
    session['messages'].append({"role": "user", "content": user_input})

    # Calculate the available token space for the response
    max_response_tokens = MAX_ALLOWED_TOKENS - calculate_messages_tokens(session['messages']) - BOT_RESPONSE_BUFFER

    try:  # Call the Chat completions API with appropriate parameters
        response = zhipu_client.chat.completions.create(
            model=MODEL_NAME,
            messages=session['messages'],  # Use the messages from the session
            # temperature=1,
            # max_tokens=max_response_tokens,
            # top_p=1,
            # frequency_penalty=1,
            # presence_penalty=1
        )
        # tokens_used = response['usage']['total_tokens']

        # if tokens_used + calculate_messages_tokens(session['messages']) > MAX_ALLOWED_TOKENS:
        #     print("Token limit exceeded by the bot's response.")
        #     return jsonify({"response": "Sorry, the token limit has been exceeded."})

        # Add the assistant's response to the session messages
        session['messages'].append({"role": "assistant", "content": response.choices[0].message.content})
        
        # Retrieve the latest message which is the bot's response
        bot_response = response.choices[0].message.content

    # except openai.error.OpenAIError as e:
    #     print(f"OpenAI Error: {e}.")
    #     return jsonify({"response": f"An OpenAI error occurred: {e}"})
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"response": f"An error occurred: {e}"})

    # Return the assistant's response
    return jsonify({"response": bot_response})

@app.route('/api/chat/end', methods=['POST'])
def end_chat():
    # Extract the user_name when the chat ends
    conversation_data = request.json
    user_name = conversation_data.get('user_name', 'unknown_user')
    save_conversation(user_name)
    return jsonify({"message": "Conversation saved."})

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=9000)
    finally:
        # Here we should not save the conversation because we don't have a user_name
        pass  
