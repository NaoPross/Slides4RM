# Local modules
from config import SERVER_NAME, SECRET_KEY

# Standard library
import os
import subprocess
import pathlib
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# External dependencies
import colorlog as logging
from werkzeug.utils import secure_filename
from pdfminer import pdfparser, pdfdocument, pdfinterp, pdfpage
from flask import (Flask, request, flash, redirect, url_for, render_template,
                   stream_template, send_file)


# ┏━╸┏━┓┏┓╻┏━╸╻┏━╸╻ ╻┏━┓┏━┓╺┳╸╻┏━┓┏┓╻
# ┃  ┃ ┃┃┗┫┣╸ ┃┃╺┓┃ ┃┣┳┛┣━┫ ┃ ┃┃ ┃┃┗┫
# ┗━╸┗━┛╹ ╹╹  ╹┗━┛┗━┛╹┗╸╹ ╹ ╹ ╹┗━┛╹ ╹

app = Flask(__name__, template_folder='templates', static_folder='static')

if app.config['DEBUG']:
    UPLOAD_FOLDER = './debug/upload/'
    RENDER_FOLDER = './debug/render/'
else:
    UPLOAD_FOLDER = '/tmp/upload'
    RENDER_FOLDER = '/tmp/render'

MAX_FILE_SIZE = 50 * 1000 * 1000
ALLOWED_EXTENSIONS = ['.pdf']

LATEX = ['xelatex', '-interaction=batchmode', '-no-shell-escape', '-halt-on-error']
LATEX_TEMPLATE_FILE = './latex/template.tex'
LATEX_NITER=2

# ╻ ╻┏━╸╻  ┏━┓┏━╸┏━┓┏━┓
# ┣━┫┣╸ ┃  ┣━┛┣╸ ┣┳┛┗━┓
# ╹ ╹┗━╸┗━╸╹  ┗━╸╹┗╸┗━┛

# Read template
with pathlib.Path(LATEX_TEMPLATE_FILE).resolve().open('r') as f:
    LATEX_TEMPLATE = f.read()

# Create upload folders if the do not exist
for folder in map(lambda n: pathlib.Path(n), [UPLOAD_FOLDER, RENDER_FOLDER]):
    if not folder.exists():
        folder.mkdir(parents=True)


def render_latex(filename):
    pdffile = pathlib.Path(UPLOAD_FOLDER).joinpath(filename).resolve()
    texfile = pathlib.Path(RENDER_FOLDER) \
                .joinpath(pdffile.stem + '_ReMarkable') \
                .with_suffix('.tex') \
                .resolve()

    assert(pdffile.is_file())

    # Grab metadata from PDF
    npages = None
    aratio = None
    with pdffile.open('rb') as f:
        parser = pdfparser.PDFParser(f)
        pdf = pdfdocument.PDFDocument(parser)

        # get number of pages
        npages = pdfinterp.resolve1(pdf.catalog['Pages'])['Count']

        # get page aspect ratio
        page = next(pdfpage.PDFPage.create_pages(pdf))
        width = page.mediabox[2] - page.mediabox[0] 
        height = page.mediabox[3] - page.mediabox[1]
        aratio = width / height
        # print(f'aratio={aratio}, 16:9={16/9:.4f}, 4:3={4/3:.4f}')

    assert(npages is not None)
    assert(aratio is not None)

    # Prepare LaTeX template
    pdffile = shutil.move(pdffile, texfile.with_name(pdffile.name))
    with texfile.open('w') as f:
        width = '.8\paperwidth' # for 4/3
        if abs(aratio - 16/9) < .1:
            width = f'{36*4}mm'

        f.write(LATEX_TEMPLATE \
                .replace('SLIDESFILE', str(pdffile.name)) \
                .replace('SLIDESCOUNT', str(npages)) \
                .replace('TITLE', pdffile.name) \
                .replace('SLIDESWIDTH', width))

    def cleanup_tex():
        pdffile.unlink()
        texfile.unlink()
        for suff in ['.log', '.synctex.gz', '.aux']:
            aux = texfile.with_suffix(suff)
            if aux.is_file():
                aux.unlink()

    # Typeset LaTeX
    try:
        cmd = LATEX + [str(texfile)]
        for _ in range(LATEX_NITER):
            p = subprocess.run(cmd, check=True, cwd=texfile.parent)
    except subprocess.CalledProcessError: 
        cleanup_tex()
        return pdffile, False

    cleanup_tex()
    return texfile.with_suffix('.pdf'), True

# ┏━┓┏━┓╻ ╻╺┳╸┏━╸┏━┓
# ┣┳┛┃ ┃┃ ┃ ┃ ┣╸ ┗━┓
# ╹┗╸┗━┛┗━┛ ╹ ┗━╸┗━┛

app.config['SECRET_KEY'] = SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

if not app.config['DEBUG']:
    # Set hostname
    app.config['SERVER_NAME'] = SERVER_NAME
    # Fix for proxy
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )


@app.route('/')
def main():
    return redirect(url_for('upload'))


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        filenames = []
        for f in request.files.getlist('file[]'):
            filename = pathlib.Path(secure_filename(f.filename))
            if not filename.suffix in ALLOWED_EXTENSIONS:
                # TODO report error
                continue

            filenames.append(filename.name)
            filepath = pathlib.Path(UPLOAD_FOLDER).joinpath(filename).resolve()
            f.save(filepath)

        if not filenames:
            flash('No files were given or they cannot be processed.')
            return redirect(request.url)

        return redirect(url_for('process', filenames=filenames, nfiles=len(filenames)))

    return render_template("upload.html")


@app.route('/process')
def process():
    filenames = request.args.getlist('filenames')
    nfiles = request.args.get('nfiles')

    def generate():
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(render_latex, src) for src in filenames}
            for future in as_completed(futures):
                f, success = future.result()
                yield f.name, success

    return stream_template("process.html", pdfs=generate(), nfiles=nfiles)


@app.route('/download/<filename>')
def download(filename):
    if not filename:
        return "No file given", 400

    f = pathlib.Path(RENDER_FOLDER).joinpath(filename).resolve()
    if not f.is_file():
        return "file not found", 404

    # return send_file(f, mimetype='application/pdf', as_attachment=True)
    return send_file(f, mimetype='application/pdf')


