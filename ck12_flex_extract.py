import pdfparser.poppler as pdf
from collections import defaultdict

# TODO color and font definitions for sections
# TODO detect headers and assemble topics


class CK12FlexbookParser(object):

    def __init__(self):
        self.current_lesson = None
        self.current_topic = None
        self.parsed_content = defaultdict(lambda: defaultdict(str))
        self.section_demarcations = {
            'topic_color': (0.811767578125, 0.3411712646484375, 0.149017333984375),
            'lesson_size': 22.3082,
            'chapter_size': 0
        }

    def parse_pdf(self, file_path):
        doc = pdf.Document(file_path)
        print 'No of pages', doc.no_of_pages
        for page in doc:
            self.extract_page_text(page)
        return self.parsed_content

    def extract_page_text(self, page):
        for flow in page:
            for block in flow:
                for line in block:
                    line_dict = {
                        'content': line.text,
                        'rectangle': line.bbox.as_tuple(),
                        'font_size': list(line.char_fonts)[0].size,
                        'font_color': list(line.char_fonts)[0].color.as_tuple()
                    }
                    if line_dict['font_size'] == self.section_demarcations['lesson_size']:
                        self.current_lesson = line_dict['content']
                    elif line_dict['font_color'] == self.section_demarcations['topic_color']:
                        self.current_topic = line_dict['content']
                    elif not sum(line_dict['font_color']) and self.current_topic:
                        self.parsed_content[self.current_lesson][self.current_topic] += line_dict['content'] + '\n'
