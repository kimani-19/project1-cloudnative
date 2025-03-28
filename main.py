import time
import os
from google.cloud import storage
from flask import Flask, request, redirect, send_file, Response
import io
from PIL import Image
os.makedirs('files', exist_ok = True)
import json
import google.generativeai as genai

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))



model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
#   generation_config=generation_config,
  # safety_settings = Adjust safety settings
  # See https://ai.google.dev/gemini-api/docs/safety-settings
)

PROMPT = " Give me a a one line title and description for this image, in a json format. "

def upload_to_gemini(path, mime_type=None):
  """Uploads the given file to Gemini.

  See https://ai.google.dev/gemini-api/docs/prompting_with_media
  """
  file = genai.upload_file(path, mime_type=mime_type)
  print(f"Uploaded file '{file.display_name}' as: {file.uri}")
  # print(file)
  return file



# print(response)
app = Flask(__name__)

storage_client=storage.Client()
Bucket_name = os.environ.get("BUCKET_NAME")

@app.get("/hello")
def hello():
    """Return a friendly HTTP greeting."""
    who = request.args.get("who", default="World")
    time.sleep(5)
    return f"Hello {who}!\n"

@app.route('/')
def index():
    index_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload Image</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body  class="container py-5" style="background-color: blue;">
        <h1 class="text-center text-primary">Image Upload Portal</h1>
        <h2 class="text-center">Upload an Image</h2>
        <form method="post" enctype="multipart/form-data" action="/upload" class="mb-4 text-center">
            <input type="file" name="form_file" accept="image/jpeg" class="form-control mb-2" required>
            <button class="btn btn-primary">Upload</button>
        </form>
        <h3 class="mt-4">Uploaded Images</h3>
        <ul class="list-group">
    """
    
    for file in list_files():
        index_html += f'<li class="list-group-item"><a href="/files/{file.name}">{file.name}</a></li>'
    
    index_html += """
        </ul>
    </body>
    </html>
    """
    return index_html

@app.route('/upload', methods=["POST"])
def upload():

    file = request.files['form_file']  # item name must match name in HTML form
    #file.save(os.path.join("./files", file.filename))
    bucket = storage_client.bucket(Bucket_name)
    blob_image = bucket.blob(file.filename)
    blob_image.upload_from_file(file_obj=file, rewind=True)
    file.save(os.path.join("",file.filename))
    response = model.generate_content([Image.open(file), PROMPT])
    print(response.text)
    index_1=response.text.index("{")
    index_2=response.text.index("}")
    response_string=response.text[index_1:index_2+1]
    print (response_string,type(response_string))
    json_response=json.loads(response_string)
    print(json_response)
    file_name = file.filename.split(".")[0]+".json"
    # Write JSON data to a file
    with open(file_name, "w") as json_file:
        json.dump(json_response, json_file, indent=4)
    blob_text = bucket.blob(file.filename.split(".")[0]+".json")
    blob_text.upload_from_filename(file.filename.split(".")[0]+".json")

    return redirect("/")

@app.route('/files')
def list_files():
    files = storage_client.list_blobs(Bucket_name)
    jpegs = []
    for file in files:
        if file.name.lower().endswith(".jpeg") or file.name.lower().endswith(".jpg"):
            jpegs.append(file)
    
    return jpegs

@app.route('/files/<filename>')
def get_file(filename):
    bucket = storage_client.bucket(Bucket_name)
    blob = bucket.blob(filename.split(".")[0]+".json")
    file_data = blob.download_as_bytes()
    file_data = json.loads(file_data.decode('utf-8'))
    print(file_data)
    html= f""" <body style="background-color: blue;">
        <img src='/images/{filename}'>
        <h1>Tiltle:{file_data['title']}</h1>
        <p>Description:{file_data['description']}</p>
    </body>""" 
    return html
#   return Response(io.BytesIO(file_data), mimetype='image/jpeg')

@app.route('/images/<imagename>')
def view_image(imagename):
    bucket = storage_client.bucket(Bucket_name)
    blob = bucket.blob(imagename)
    file_data = blob.download_as_bytes()
    return Response(io.BytesIO(file_data), mimetype='image/jpeg')

if __name__ == "__main__":
    # Development only: run "python main.py" and open http://localhost:8080
    # When deploying to Cloud Run, a production-grade WSGI HTTP server,
    # such as Gunicorn, will serve the app.
    app.run(host="localhost", port=8080, debug=True)
