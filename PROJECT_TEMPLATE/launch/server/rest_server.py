from flask import Flask, request, jsonify
from http import HTTPStatus

app = Flask(__name__)

@app.route('/api/v1/process', methods=['POST'])
def process_request():
	data = request.get_json(silent=True) or {}
	input_text = data.get("input")
	if not input_text:
		return jsonify({"error": "input required"}), HTTPStatus.BAD_REQUEST

	# 🔧 Replace with your AI agent call
	result = input_text[::-1]  # placeholder logic

	return jsonify({"result": result}), HTTPStatus.OK


@app.route('/health', methods=['GET'])
def health():
	return jsonify({"status": "ok"}), HTTPStatus.OK


if __name__ == "__main__":
	# 0.0.0.0 lets Docker expose the port
	app.run(host="0.0.0.0", port=8000, debug=True)