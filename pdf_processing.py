import numpy as np
from wand.image import Image as WImage
from IPython.display import display
import PIL.Image as Image
import cv2

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


def make_png_stream(book_pdf):
    raw_pdf = WImage(book_pdf)
    page_png = raw_pdf.convert('png')
    y_height = int(page_png.size[1])
    png_blob = page_png.make_blob()
    return png_blob, y_height


def make_open_cv_img(page_stream, color_flag=1):
    img_array = np.asarray(bytearray(page_stream), dtype=np.uint8)
    return cv2.imdecode(img_array, color_flag)


def random_color():
    import random
    return random.randint(0,255), random.randint(0,255), random.randint(0,255)


def get_bbox_tuple(box, y_height):
    def shift_coord(coord, height):
        return coord[0],  height - coord[1]
    lower_right = tuple(map(lambda x: int(x), box.bbox[2:]))
    upper_left = tuple(map(lambda x: int(x), box.bbox[:2]))
    return shift_coord(lower_right, y_height), shift_coord(upper_left, y_height)


def display_page(raw_page_img, page_layout):
    page_png_stream, y_height = make_png_stream(raw_page_img)
    page_img = make_open_cv_img(page_png_stream)
    for box in page_layout._objs:
        lr, ul = get_bbox_tuple(box, y_height)
        try:
            # print box.get_text()
            pass
        except AttributeError:
            pass
        cv2.rectangle(page_img, ul, lr, color=random_color(), thickness=2)
    display(Image.fromarray(page_img, 'RGB'))


def draw_pdf_with_boxes(book_file, page_range, word_margin=0.1, line_overlap=0.5, char_margin=2.0,
                        line_margin=0.5, boxes_flow=0.5):
    if page_range:
        page_range = map(lambda x: x - 1, page_range)
        suffix = '[{}-{}]'.format(page_range[0], page_range[1])
        raw_multi_pdf = WImage(filename=book_file + suffix)
    else:
        raw_multi_pdf = WImage(filename=book_file)
        
    doc_page_layouts = make_page_layouts(book_file, page_range,
                                         line_overlap,
                                         char_margin,
                                         line_margin,
                                         word_margin,
                                         boxes_flow)
    page_images = raw_multi_pdf.sequence
    for page_n in range(len(page_images)):
        display_page(page_images[page_n], doc_page_layouts[page_n])
