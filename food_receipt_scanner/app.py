import os

from flask import Flask, jsonify, render_template, request

from . import config, db
from .agent import answer
from .ocr import extract_text, parse_receipt

app = Flask(__name__)
db.init_db()


def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("image")
    if not file or not _allowed(file.filename):
        return jsonify({"error": "please upload a valid image (png/jpg/webp)"}), 400

    os.makedirs(config.UPLOAD_DIR, exist_ok=True)
    path = os.path.join(config.UPLOAD_DIR, file.filename)
    file.save(path)

    try:
        text = extract_text(path)
        parsed = parse_receipt(text)
    except Exception as exc:
        return jsonify({"error": f"OCR failed: {exc}"}), 500

    if not parsed:
        return jsonify({"error": "could not parse receipt text"}), 500

    receipt_id = db.insert_receipt(
        parsed["store"], parsed["date"], parsed["total"],
        parsed["items"], parsed["raw_text"], path,
    )

    return jsonify({
        "receipt_id": receipt_id,
        "store": parsed["store"],
        "date": parsed["date"],
        "total": parsed["total"],
        "items": parsed["items"],
    })


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = data.get("question", "")
    if not question:
        return jsonify({"error": "question is required"}), 400
    return jsonify({"answer": answer(question)})


@app.route("/receipts")
def receipts():
    return jsonify(db.recent_receipts())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
