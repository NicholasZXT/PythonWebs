import pandas as pd
from flask import Blueprint, request, current_app, jsonify

file_bp = Blueprint('file', __name__)


@file_bp.route('/file/upload', methods=['POST'])
def upload():
    file = request.files['file']
    print(f"received file {file.filename}...")
    file.save(file.filename)
    df = pd.read_excel(file)
    print(df.head())
    return "File saved successfully"


