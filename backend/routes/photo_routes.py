import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

photo_bp = Blueprint("photo_bp", __name__)

# Allowed extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Endpoint to upload photo
@photo_bp.route("/upload-photo", methods=["POST"])
def upload_photo():
    if "photo" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["photo"]

    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        # Make filename safe
        filename = secure_filename(file.filename)

        # Folder path: backend/static/assets
        upload_folder = os.path.join(current_app.root_path, "static", "assets")
        os.makedirs(upload_folder, exist_ok=True)

        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        # Return relative path for frontend to use
        return jsonify({
            "message": "File uploaded successfully",
            "file_path": f"/static/assets/{filename}"
        }), 200
    else:
        return jsonify({"error": "File type not allowed"}), 400
