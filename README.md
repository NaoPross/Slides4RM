# Slides for ReMarkable

Convert slides (PDFs) to handouts to take notes with the ReMarkable tablet.

**NOTE:** I built this in an afternoon so it's a bit crappy, but it works well enough for me. I'll improve it when I find some time. Self host at your own risk.

To run this:

 1. Create a file `config.py`
 
 ```python3
 SECRET_KEY = b'secret_key' # Create a secret key
 SERVER_NAME = 'yourwebsite.com' # Set your domain name
 ```
 
 2. In dev mode you can use flask
 
 ```
 $ flask --debug --app slides4rm.py run
 ```
 
 for production run it with Docker or Podman
 
 ```
 $ podman build . --tag slides4rm
 $ podman run -it -p 80:8000 --name slides4rm localhost/slides4rm
 ```
 
 or set up `uwsgi` / `gunicorn` / ...

## Sample outputs

<div style="text-align:center">
<img src="./examples/VWL.png" style="width:48%"/>
<img src="./examples/MPC.png" style="width:48%"/>
</div>

## Web interface

<div style="text-align:center">
<img src="./examples/upload.png" style="width:48%"/>
<img src="./examples/process.png" style="width:48%"/>
</div>
