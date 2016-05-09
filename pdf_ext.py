import sys
import os
from binascii import b2a_hex

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter

from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator


def make_page_layouts(pdf_file, page_range, line_overlap,
                      char_margin,
                      line_margin,
                      word_margin,
                      boxes_flow):
    laparams = LAParams(line_overlap, char_margin, line_margin, word_margin, boxes_flow)
    page_layouts = []
    with open(pdf_file, 'r') as fp:
        parser = PDFParser(fp)
        document = PDFDocument(parser)
        rsrcmgr = PDFResourceManager()
        device = PDFPageAggregator(rsrcmgr, laparams=laparams)
        interpreter = PDFPageInterpreter(rsrcmgr, device)
        for page_n, page in enumerate(PDFPage.create_pages(document)):
            if not page_range:
                interpreter.process_page(page)
                layout = device.get_result()
                page_layouts.append(layout)
            elif page_range[0] <= page_n <= page_range[1]:
                interpreter.process_page(page)
                layout = device.get_result()
                page_layouts.append(layout)
    return page_layouts


def write_image_file(layout, page_n, dir_name):
    page_image = layout._objs[-1]._objs[0]
    save_image(page_image, page_n, dir_name)
    return


def write_annotation_file(layout, page_n, dir_name):

    pass


def determine_image_type (stream_first_4_bytes):
    """Find out the image file type based on the magic number comparison of the first 4 (or 2) bytes"""
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


def save_image (lt_image, page_number, images_folder):
    """Try to save the image data from this LTImage object, and return the file name, if successful"""
    result = None
    if lt_image.stream:
        file_stream = lt_image.stream.get_rawdata()
        if file_stream:
            file_ext = determine_image_type(file_stream[0:4])
            if file_ext:
                file_name = ''.join([str(page_number), '_', lt_image.name, file_ext])
                if write_file(images_folder, file_name, file_stream, flags='wb'):
                    result = file_name
    return result


def write_file (folder, filename, filedata, flags='w'):
    """Write the file data to the folder and filename combination
    (flags: 'w' for write text, 'wb' for write binary, use 'a' instead of 'w' for append)"""
    result = False
    if os.path.isdir(folder):
        try:
            file_obj = open(os.path.join(folder, filename), flags)
            file_obj.write(filedata)
            file_obj.close()
            result = True
        except IOError:
            pass
    return result

