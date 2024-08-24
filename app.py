from flask import Flask, request, render_template, redirect, url_for, flash, send_from_directory, make_response
import os
import subprocess
import difflib

app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'uploads'
CORRECTED_FOLDER = 'corrected'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CORRECTED_FOLDER'] = CORRECTED_FOLDER

# Ensure upload and corrected folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CORRECTED_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Run linter and auto-corrector
            lint_output = run_linter(file_path)
            corrected_code, changes = auto_correct_code(file_path)
            save_corrected_code(filename, corrected_code)

            return render_template(
                'result.html', 
                original_code=open(file_path).read(), 
                corrected_code=corrected_code,
                lint_output=lint_output, 
                changes=changes, 
                download_url=url_for('download_file', filename=filename)
            )

    return render_template('index.html')

def run_linter(file_path):
    """Run Pylint on the provided file and return the output."""
    result = subprocess.run(['pylint', file_path], capture_output=True, text=True)
    return result.stdout + result.stderr

def auto_correct_code(file_path):
    """Perform auto-correction on the provided file and return the corrected code and changes."""
    # Using Black for code formatting
    result = subprocess.run(['black', file_path], capture_output=True, text=True)
    if result.returncode != 0:
        flash('Error correcting code: ' + result.stderr)
        return '', 'No changes made.'

    with open(file_path, 'r') as file:
        original_code = file.readlines()
    
    corrected_file_path = os.path.join(app.config['CORRECTED_FOLDER'], os.path.basename(file_path))
    with open(corrected_file_path, 'r') as file:
        corrected_code = file.readlines()

    changes = ''.join(difflib.unified_diff(original_code, corrected_code, fromfile='Original', tofile='Corrected'))
    return ''.join(corrected_code), changes

def save_corrected_code(filename, corrected_code):
    """Save the corrected code to the corrected folder."""
    corrected_file_path = os.path.join(app.config['CORRECTED_FOLDER'], filename)
    with open(corrected_file_path, 'w') as f:
        f.write(corrected_code)

@app.route('/download/<filename>')
def download_file(filename):
    """Send the corrected file to the user for download."""
    response = make_response(send_from_directory(app.config['CORRECTED_FOLDER'], filename, as_attachment=True))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/xdownload/<filename>')
def xdownload_file(filename):
    """Send the corrected file to the user for download."""
    return send_from_directory(app.config['CORRECTED_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run()
