from flask import Flask, request, jsonify
from integrations.telegram import handle_callback

app = Flask(__name__)

@app.route('/telegram_webhook', methods=['POST'])
def telegram_webhook():
    update = request.get_json(force=True)
    try:
        result = handle_callback(update)
        return jsonify(result)
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
