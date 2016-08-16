import pdfparser.poppler as pdf
from collections import defaultdict

# TODO color and font definitions for sections
# TODO detect headers and assemble topics

section_demarcations = {
    'topic_color': (0.811767578125, 0.3411712646484375, 0.149017333984375),
    'lesson_size': 22.3082,
    'chapter_size': 0
}


def parse_pdf(file_path):
    doc = pdf.Document(file_path)
    # print 'No of pages', doc.no_of_pages
    book_dict = {}
    for page in doc:
        book_dict.update(extract_page_text(page))
    return book_dict


def extract_page_text(page):
    page_dict = defaultdict(dict)
    box_index = 0
    for flow in page:
        for block in flow:
            for line in block:
                line_dict = {
                    'content': line.text,
                    'rectangle': line.bbox.as_tuple(),
                    'font_size': list(line.char_fonts)[0].size,
                    'font_color': list(line.char_fonts)[0].color.as_tuple()
                }
                if line_dict['font_size'] == section_demarcations['lesson_size']:
                    print 'lesson'
                elif line_dict['font_color'] == section_demarcations['topic_color']:
                    print 'topic'
                if sum(line_dict['font_color']) or True:
                    page_dict['P' + str(page.page_no)].update({'T' + str(box_index): line_dict})
                    box_index += 1
    return page_dict

