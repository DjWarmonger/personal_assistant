from flask import Flask, request, jsonify
from http import HTTPStatus

import sys
from pathlib import Path

# Reuse path setup from chat.py
project_root = Path(__file__).parent.parent.parent.absolute()
if str(project_root) not in sys.path:
	sys.path.insert(0, str(project_root))

# Add launcher directory to path
launcher_dir = Path(__file__).parent.absolute()
if str(launcher_dir) not in sys.path:
	sys.path.insert(0, str(launcher_dir))

from chat import chat

app = Flask(__name__)

@app.route('/api/v1/process', methods=['POST'])
def process_request():
	data = request.get_json(silent=True) or {}
	input_text = data.get("input")
	if not input_text:
		return jsonify({"error": "input required"}), HTTPStatus.BAD_REQUEST

	try:
		# Replace template placeholder with chat() call
		result = chat(loop=False, user_prompt=input_text)
		return jsonify({"result": result}), HTTPStatus.OK
	except Exception as e:
		# Handle any errors from the chat function
		return jsonify({"error": f"Processing failed: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR


@app.route('/health', methods=['GET'])
def health():
	return jsonify({"status": "ok"}), HTTPStatus.OK


if __name__ == "__main__":
	# 0.0.0.0 lets Docker expose the port
	app.run(host="0.0.0.0", port=8000, debug=True) 