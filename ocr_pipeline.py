import requests
import json
import os
from binascii import b2a_hex

from collections import OrderedDict
from collections import defaultdict

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator


def determine_image_type (stream_first_4_bytes):
    file_type = None
    bytes_as_hex = b2a_hex(stream_first_4_bytes)
    if bytes_as_hex.startswith('ffd8'):
        file_type = '.jpeg'
    elif bytes_as_hex == '89504e47':
        file_type = '.png'
    elif bytes_as_hex == '47494638':
        file_type = '.gif'
    elif bytes_as_hex.startswith('424d'):
        file_type = '.bmp'
    return file_type


def save_image(lt_image, page_n, book, images_folder):
    result = None
    if lt_image.stream:
        file_stream = lt_image.stream.get_rawdata()
        if file_stream:
            file_ext = determine_image_type(file_stream[0:4])
            if file_ext:
                file_name = book + '_' + str(page_n) + file_ext
                if write_file(images_folder, file_name, file_stream, flags='wb'):
                    result = file_name
    return result


def write_file(folder, filename, filedata, flags='w'):
    result = False
    if os.path.isdir(folder):
        file_obj = open(os.path.join(folder, filename), flags)
        file_obj.write(filedata)
        file_obj.close()
        result = True
    return result


def write_image_file(layout, page_n, book, dir_name):

    page_image = layout._objs[-1]._objs[0]
    save_image(page_image, page_n, book, dir_name)
    return


def write_annotation_file(ocr_results, page_n, book, annotations_folder):

    def point_to_tuple(box):
        return tuple(OrderedDict(sorted(box.items())).values())

    def get_bbox_tuples(detection):
        return map(point_to_tuple, detection['rectangle'])

    ids = 1
    annotation = defaultdict(defaultdict)
    for box in ocr_results['detections']:
        box_id = 'T' + str(ids)
        bounding_rectangle = get_bbox_tuples(box)
        annotation['text'][box_id] = {
            "box_id": box_id,
            "category": "unlabeled",
            "contents": box['value'],
            "score": box['score'],
            "rectangle": bounding_rectangle,
            "source": {
                "type": "object",
                "$schema": "http://json-schema.org/draft-04/schema",
                "additionalProperties": False,
                "properties": [
                    {"book_source": "sb"},
                    {"page_n": 149}
                ]
            }
        }
        ids += 1

    file_ext = ".json"
    file_path = annotations_folder + '/' + book + '_' + str(page_n) + file_ext
    with open(file_path, 'wb') as f:
        json.dump(annotation, f)
    return


def query_vision_ocr(image_url, merge_boxes=True, include_merged_components=False, as_json=True):
    api_entry_point = 'http://10.12.2.9:8000/v1/ocr'
    header = {'Content-Type': 'application/json'}
    request_data = {
        'url': image_url,
        # 'maximumSizePixels': max_pix_size,
        'mergeBoxes': merge_boxes,
        'includeMergedComponents': include_merged_components
    }

    json_data = json.dumps(request_data)
    response = requests.post(api_entry_point, data=json_data, headers=header)
    json_response = json.loads(response.content.decode())

    if as_json:
        response = json_response
    return response


def process_book(pdf_file, page_range, line_overlap,
                 char_margin,
                 line_margin,
                 word_margin,
                 boxes_flow):
    source_dir = 'pdfs/'
    book_name = pdf_file.replace('.pdf', '')
    laparams = LAParams(line_overlap, char_margin, line_margin, word_margin, boxes_flow)

    with open(source_dir + pdf_file, 'r') as fp:
        parser = PDFParser(fp)
        document = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)

        with open('ocr_res.json', 'r') as f:
            ocr_detections = json.load(f)

        for page_n, page in enumerate(PDFPage.create_pages(document)):
            if not page_range or (page_range[0] <= page_n <= page_range[1]):
                interpreter.process_page(page)
                layout = device.get_result()
                # write_image_file(layout, page_n, pdf_file, 'page_images', book_name)
                write_image_file(layout, page_n, book_name, 'page_images')
                write_annotation_file(ocr_detections, page_n, book_name, 'annotations')
    return
