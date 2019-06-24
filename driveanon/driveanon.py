import io
import requests
from bs4 import BeautifulSoup

def _get_token(response):
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value
    return None

def _is_folder(response):
    if 'P3P' in response.headers:
        return True
    else:
        return False

def _get_response(blob_id):
    session = requests.Session()
    url = 'https://drive.google.com/open'
    response = session.get(url, params = { 'id' : blob_id })

    if _is_folder(response):
        return response

    url = "https://docs.google.com/uc?export=download"
    response = session.get(url, params = { 'id' : blob_id }, stream = True,)
    token = _get_token(response)
    if token:
        params = { 'id' : blob_id, 'confirm' : token }
        response = session.get(url, params = params, stream = True)
    return response

def open(blob_id):
    """ Read a file from Google Drive into memory. Returns an open (BytesIO) file-like object. """

    response = _get_response(blob_id)
    return io.BytesIO(response.content)

def save(blob_id, filename = None, overwrite = False):
    """ Save a file from Google Drive to disk."""

    # get response
    response = _get_response(blob_id)

    # parse filename
    if not filename:
        filename = response.headers['Content-Disposition'].split('=')[1].split('"')[1]

    # check if filename is a file
    from pathlib import Path
    p = Path(filename)
    if p.is_file() and not overwrite:
        raise FileExistsError('File exists: %s' % filename)

    # write file
    import builtins
    with builtins.open(filename, 'wb') as w:
        w.write(response.content)

    return filename

def request_folder_blob(folder_blob_id):
    url = "https://drive.google.com/drive/folders/%s" % folder_blob_id
    session = requests.Session()
    response = session.get(url, params = { 'usp' : 'sharing' })
    html_response = BeautifulSoup(response.text, 'html.parser')
    return html_response

def find_content_block(html_response, extension):
    content_block = []
    for element in html_response.find_all('script'):
        if extension in element.text:
            content_block.append(element)
    return content_block

def extract_file_indices(content_block, extension):
    # split up content up by common seperating character string
    all_elements = str(content_block[0]).split('\\x22')
    # extract indices for each extension occurance
    file_indices = [i for i, s in enumerate(all_elements) if extension in s]
    return file_indices, all_elements

def get_file_blobs(all_elements, file_indices):
    file_names = []
    blob_ids = []
    # iterate over indices of file names
    for ind in file_indices:
        # extract file name
        file_names.append(all_elements[ind])
        # extract blob id, which occurs 4 indices before the file name
        blob_ids.append(all_elements[ind-4])
    return file_names, blob_ids

def list_blobs(folder_blob_id,extension):
    html_response = request_folder_blob(folder_blob_id)
    content_block = find_content_block(html_response, extension)
    file_indices, all_elements = extract_file_indices(content_block, extension)
    file_names, file_blob_ids = get_file_blobs(all_elements, file_indices)
    return file_names, file_blob_ids
