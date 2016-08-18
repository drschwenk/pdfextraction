import pdfparser.poppler as pdf
from collections import defaultdict
import glob
import numpy as np

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
                    line_props = {
                        'content': line.text,
                        'rectangle': line.bbox.as_tuple(),
                        'font_size': list(line.char_fonts)[0].size,
                        'font_color': list(line.char_fonts)[0].color.as_tuple()
                    }
                    if line_props['font_size'] == self.section_demarcations['lesson_size']:
                        self.current_lesson = line_props['content']
                    elif line_props['font_color'] == self.section_demarcations['topic_color']:
                        self.current_topic = line_props['content']
                    elif not sum(line_props['font_color']) and self.current_topic:
                        self.parsed_content[self.current_lesson][self.current_topic] += line_props['content'] + '\n'


class CK12QuizParser(object):

    def __init__(self):
        self.current_lesson = None
        self.current_topic = None
        self.parsed_content = defaultdict(lambda: defaultdict(str))
        self.color_demarcations = {
            'black': (1, 0, 0),
            'title_color': (0.0901947021484, 0.211761474609, 0.364700317383)
        }
        self.font_demarcations = {
            'standard_size': 12.0,
            'answer_choice': 10.8
        }
        self.stop_words = {
            'titles': [u'answers', u'quiz', u'answer', u'key']
        }
        self.titles = []

    def check_color(self, line_properties):
            for k, v in self.color_demarcations.items():
                if np.isclose(v, line_properties['color']).min():
                    return k
            else:
                return None

    def parse_pdf(self, file_path):
        doc = pdf.Document(file_path)
        for page in doc:
            self.extract_page_text(page)
        return self.parsed_content

    def extract_page_text(self, page):
        for flow in page:
            for block in flow:
                for line in block:
                    line_props = {
                        'content': line.text,
                        'rectangle': line.bbox.as_tuple(),
                        'font_size': list(line.char_fonts)[0].size,
                        'color': list(line.char_fonts)[0].color.as_tuple()
                    }
                    if self.check_color(line_props) == 'title_color':
                        title_text = line_props['content'].lower()
                        for sw in self.stop_words['titles']:
                            title_text = title_text.replace(sw, '')
                        self.titles.append(title_text.strip().encode('ascii', 'ignore'))
                    # self.sizes_seen.append(line_props['font_size'])
                    # self.colors_seen.append(line_props['font_color'])
                    # if line_props['font_size'] == self.section_demarcations['lesson_size']:
                    #     self.current_lesson = line_props['content']
                    # elif line_props['font_color'] == self.section_demarcations['topic_color']:
                    #     self.current_topic = line_props['content']
                    # elif not sum(line_props['font_color']) and self.current_topic:
                    #     self.parsed_content[self.current_lesson][self.current_topic] += line_props['content'] + '\n'

    def parse_pdf_collection(self, pdf_dir):
        for pdf_file in glob.glob(pdf_dir + '/*'):
        # for pdf_file in glob.glob(pdf_dir + '/*')[:3]:
            self.parse_pdf(pdf_file)
        return self.titles



