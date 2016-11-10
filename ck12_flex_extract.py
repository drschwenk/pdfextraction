import glob
import json
import functools
import string
import re
import pdfparser.poppler as pdf_poppler
from collections import defaultdict
from collections import OrderedDict
from copy import deepcopy
import PIL.Image as Image
import numpy as np
import fuzzywuzzy.fuzz
import jsonschema
import ck12_schema
import warnings
import klepto

from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager
from pdfminer.pdfinterp import PDFPageInterpreter
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LTFigure


class QuestionTypeParser(object):
    def __init__(self, overlap_tol=None, blank_threshold=None):
        self.numeric_starters = [str(n) + '.' for n in range(41)]
        self.numeric_starters += [str(n) + ')' for n in range(41)]
        self.letter_starters = [char + ')' for char in string.ascii_uppercase[:12]]
        self.letter_starters += [char + ')' for char in string.ascii_lowercase[:12]]
        self.current_question_number = 0
        self.parsed_questions = OrderedDict()
        self.overlap_tol = overlap_tol
        self.blank_thresh = blank_threshold
        self.blank_signifier = ' '
        self.last_added_depth = 3

    @classmethod
    def start_x(cls, box):
        return box['rectangle'][0]

    @classmethod
    def start_y(cls, box):
        return box['rectangle'][1]

    @classmethod
    def end_x(cls, box):
        return box['rectangle'][2]

    @classmethod
    def end_y(cls, box):
        return box['rectangle'][3]

    @classmethod
    def height(cls, box):
        return QuestionTypeParser.end_y(box) - QuestionTypeParser.start_y(box)

    @classmethod
    def width(cls, box):
        return QuestionTypeParser.end_x(box) - QuestionTypeParser.start_x(box)

    def clean_box(self, box):
        if 'color' in box.keys():
            box_copy = deepcopy(box)
            del box_copy['color']
            del box_copy['font_size']
            return box_copy
        else:
            return box

    def get_last_added(self, ordered_prop_dict):
        return functools.reduce(lambda x, _: list(x.items())[-1][1], range(self.last_added_depth), ordered_prop_dict)

    def merge_boxes(self, sorted_box_groups):
        min_x = min(map(lambda x: QuestionTypeParser.start_x(x), sorted_box_groups))
        max_x = max(map(lambda x: QuestionTypeParser.end_x(x), sorted_box_groups))
        min_y = min(map(lambda x: QuestionTypeParser.start_y(x), sorted_box_groups))
        max_y = max(map(lambda x: QuestionTypeParser.end_y(x), sorted_box_groups))
        combined_raw_words = self.blank_signifier.join(map(lambda x: x['rawText'], sorted_box_groups))
        combined_words = self.blank_signifier.join(map(lambda x: x['processedText'], sorted_box_groups))
        combined_rect = [min_x, min_y, max_x, max_y]
        new_box = {
            'correct': sorted_box_groups[0]['correct'],
            'rawText': combined_raw_words,
            'processedText': combined_words,
            'idStructural': sorted_box_groups[0]['idStructural'],
            'rectangle': combined_rect}
        return new_box

    def append_box_to_last_element(self, box):
        last_val = self.get_last_added(self.parsed_questions)
        combined_box = self.merge_boxes([last_val, box])
        start_type, starting_chars = self.check_starting_chars(combined_box['processedText'])
        if start_type == 'numeric start':
            self.make_question_component(combined_box, starting_chars)
        elif start_type in ['letter dot start', 'letter start']:
            self.make_answer_choice(combined_box, starting_chars)

    def detect_blank(self, current_box, parsed_questions):
        search_depth = 1
        last_box_seen = {}
        while 'rectangle' not in last_box_seen.keys() and search_depth < 5:
            search_depth += 1
            last_box_seen = list(QuestionTypeParser.get_last_added(parsed_questions, search_depth).values())[0]

        large_gap = (QuestionTypeParser.start_x(current_box) - QuestionTypeParser.end_x(
            last_box_seen)) > self.blank_thresh
        same_line = self.check_for_same_line(current_box, last_box_seen)
        return same_line and large_gap

    def check_for_same_line(self, current_box, last_box_seen):
        boxes_y_coords = [[QuestionTypeParser.start_y(current_box), QuestionTypeParser.end_y(current_box)],
                          [QuestionTypeParser.start_y(last_box_seen), QuestionTypeParser.end_y(last_box_seen)]]
        ordered_boxes = sorted(boxes_y_coords)
        overlap = max(0, min(ordered_boxes[0][1], ordered_boxes[1][1]) - max(ordered_boxes[0][0], ordered_boxes[1][0]))
        larger_box_width = max(QuestionTypeParser.height(current_box), QuestionTypeParser.height(last_box_seen))
        return overlap / float(larger_box_width) > self.overlap_tol

    def check_starting_chars(self, box_text, is_correct=False):
        if box_text[:2] in self.numeric_starters and not is_correct:
            return 'numeric start', box_text[:2]
        elif box_text[:3] in self.numeric_starters and not is_correct:
            return 'numeric start', box_text[:3]
        elif box_text[:2] in self.letter_starters:
            return 'letter start', box_text[:2]
        else:
            return False, None

    def make_question_component(self, box, structural_id):
        question_id = 'q' + str(self.current_question_number).zfill(2)
        self.parsed_questions[question_id] = OrderedDict()
        # order of property fields is important for get last values
        property_fields = [["id", question_id],
                           ["idStructural", structural_id],
                           ["beingAsked", self.clean_box(box)]]

        for field in property_fields:
            self.parsed_questions[question_id][field[0]] = field[1]
        self.last_added_depth = 2

    def make_answer_choice(self, box, structural_id):
        choice_id = structural_id.replace('.', '').replace(')', '')
        question_id = 'q' + str(self.current_question_number).zfill(2)
        if 'answerChoices' not in self.parsed_questions[question_id].keys():
            self.parsed_questions[question_id]['answerChoices'] = OrderedDict()
        self.parsed_questions[question_id]['answerChoices'][choice_id] = self.clean_box(box)
        self.parsed_questions[question_id]['answerChoices'][choice_id]['idStructural'] = structural_id
        self.last_added_depth = 3

    def make_correct_answer(self, box, structural_id):
        question_id = 'q' + str(self.current_question_number).zfill(2)
        if 'correctAnswer' not in self.parsed_questions[question_id].keys():
            self.parsed_questions[question_id]['correctAnswer'] = {}
            self.parsed_questions[question_id]['correctAnswer']['idStructural'] = structural_id
            self.parsed_questions[question_id]['correctAnswer']['processedText'] = box['processedText']
        else:
            self.parsed_questions[question_id]['correctAnswer']['processedText'] += ' ' + box['processedText']
        self.last_added_depth = 2

    def scan_boxes(self, text_boxes):
        for idx, box in enumerate(text_boxes):
            box_text = box['processedText']
            start_type, starting_chars = self.check_starting_chars(box_text, box['correct'])
            box['idStructural'] = starting_chars
            if start_type == 'numeric start':
                self.current_question_number += 1
                self.make_question_component(box, starting_chars)
            if start_type in ['letter dot start', 'letter start']:
                self.make_answer_choice(box, starting_chars)
            if len(box_text) > 2 and not box['correct'] and not start_type:
                self.append_box_to_last_element(box)
            if box['correct']:
                last_start_type, last_starter = self.check_starting_chars(self.get_last_added(self.parsed_questions)['processedText'])
                if last_start_type != 'letter start' or last_starter == 'd)':
                    self.make_correct_answer(box, starting_chars)


class CK12QuizParser(object):

    def __init__(self):
        self.q_parser = None
        self.parsed_content = {
            'title': '',
            'nonDiagramQuestions': []
        }
        self.color_demarcations = {
            'title_color': (0.0901947021484, 0.211761474609, 0.364700317383),
            'black_text': (0, 0, 0),
            'red_answer': (1, 0, 0)
        }
        self.font_demarcations = {
            'standard_size': 12.0,
            'answer_choice': 10.8
        }
        self.stop_words = {
            'titles': [u'answers', u'quiz', u'answer', u'key', '-']
        }
        self.page_dim = 800
        self.titles = []

    def check_color(self, line_properties):
            for k, v in self.color_demarcations.items():
                if np.isclose(v, line_properties['color']).min():
                    return k
            else:
                return None

    def parse_pdf(self, file_path):
        page_n = 0
        self.q_parser = QuestionTypeParser()
        doc = pdf_poppler.Document(file_path)
        for page in doc:
            self.extract_page_text(page, page_n)
            page_n += 1
        sorted_boxes = sorted(self.parsed_content['nonDiagramQuestions'],
                              key=lambda x: (x['rectangle'][1], x['rectangle'][0]))
        self.q_parser.scan_boxes(sorted_boxes)
        self.parsed_content['nonDiagramQuestions'] = self.q_parser.parsed_questions
        return self.parsed_content

    def extract_page_text(self, page, page_n):
        title_text = ''
        for flow in page:
            for block in flow:
                for line in block:
                    line_props = {
                        'rawText': line.text,
                        'processedText': line.text.lower().strip().replace('\t', ' ').encode('ascii', 'ignore'),
                        'rectangle': list(line.bbox.as_tuple()),
                        'font_size': list(line.char_fonts)[0].size,
                        'color': max(list(line.char_fonts)[0].color.as_tuple(), list(line.char_fonts)[-1].color.as_tuple()),
                        'correct': False
                    }
                    line_props['rectangle'][1] += self.page_dim * page_n
                    line_props['rectangle'][3] += self.page_dim * page_n
                    if self.check_color(line_props) == 'title_color':
                        title_line_text = line_props['processedText']
                        for sw in self.stop_words['titles']:
                            title_line_text = title_line_text.replace(sw, '')
                        title_text += title_line_text
                    else:
                        if self.check_color(line_props) == 'red_answer':
                            line_props['correct'] = True
                        self.parsed_content['nonDiagramQuestions'].append(line_props)
        self.parsed_content['title'] += title_text.strip().encode('ascii', 'ignore')

    def classify_question(self, parsed_question):
        q_type = 'None'
        if 'true or false' in parsed_question['beingAsked']['processedText']:
            q_type = 'True or False'
            parsed_question['beingAsked']['processedText'] = \
                parsed_question['beingAsked']['processedText'].replace('true or false: ', '')
        if '__' in parsed_question['beingAsked']['processedText'] and q_type == 'None':
            q_type = 'Fill in the Blank'
        if parsed_question['beingAsked'] and 'answerChoices' not in parsed_question.keys() and q_type == 'None':
            q_type = 'Short Answer'
        if 'answerChoices' in parsed_question.keys() and len(parsed_question['answerChoices']) == 4:
            q_type = 'Multiple Choice'
        if 'answerChoices' in parsed_question.keys() and len(parsed_question['answerChoices']) == 2:
            q_type = 'True or False'
        return q_type

    @classmethod
    def sanitize_parsed_quiz(cls, question):
        q_components = [question['beingAsked']] + [question['correctAnswer']]
        pck = 'processedText'
        sik = 'idStructural'
        for component in q_components:
            if component and component != '_MISSING_' and component[sik]:
                component[pck] = component[pck].replace(component[sik], '').strip()
                if 'rectangle' in component.keys():
                    del component['rectangle']
                    del component['correct']
        if 'answerChoices' in question.keys():
            for component in question['answerChoices'].values():
                component[pck] = component[pck].replace(component[sik], '').strip()
                if 'rectangle' in component.keys():
                    del component['rectangle']
                    del component['correct']
        else:
            question['answerChoices'] = {}

        if 'idStructural' in question['beingAsked'].keys():
            del question['beingAsked']['idStructural']
        if 'idStructural' in question['correctAnswer'].keys():
            del question['correctAnswer']['idStructural']

    def refine_parsed_page(self, parsed_page):
        for qid, question in parsed_page['nonDiagramQuestions'].items():
            question['type'] = self.classify_question(question)
            if 'correctAnswer' not in question.keys() and 'answerChoices' in question.keys():
                question['correctAnswer'] = {}
                for ac_id, answer_choice in question['answerChoices'].items():
                    if answer_choice['correct']:
                        question['correctAnswer']['idStructural'] = answer_choice['idStructural']
                        question['correctAnswer']['processedText'] = answer_choice['processedText']
            if 'answerChoices' not in question.keys() and question['type'] == 'True or False':
                question['answerChoices'] = {
                    'a': {
                        'idStructural': 'a.',
                        'processedText': 'true',
                        'rawText': 'a. true'
                        },
                    'b': {
                        'idStructural': 'b.',
                        'processedText': 'false',
                        'rawText': 'b. false'
                        }
                }
            if 'correctAnswer' not in question.keys():
                question['correctAnswer'] = '_MISSING_'

            CK12QuizParser.sanitize_parsed_quiz(question)
        del parsed_page['title']
        parsed_page['questions'] = {'nonDiagramQuestions': parsed_page.pop('nonDiagramQuestions'), 'diagramQuestions': {}}


class FlexbookParser(object):

    def __init__(self, rasterized_pages_dir=None, figure_dest_dir=None):
        self.current_lesson = None
        self.current_topic = None
        self.current_topic_number = 1
        self.parsed_content = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.last_figure_caption_seen = None
        self.sections_to_ignore = ['References', 'Lesson Review Questions']
        self.captions_starters = ['MEDIA ', 'FIGURE ']
        self.treat_as_list = ['Lesson Vocabulary', 'Lesson Objectives', 'Vocabulary']
        self.strings_to_ignore = ['www.ck12.org']
        self.line_sep_tol = 6
        self.list_separator = '\n'
        self.line_separator = ' '
        self.page_vertical_dim = None
        self.file_paths = {
            'rasterized_page_dir': rasterized_pages_dir,
            'cropped_fig_dest_dir': figure_dest_dir
        }
        self.section_demarcations = {
            'topic_color': (0.811767578125, 0.3411712646484375, 0.149017333984375),
            'lesson_size': 22.3082,
            'chapter_size': 0
        }

    def reset_flex_parser(self):
        self.parsed_content = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    def normalize_text(self, text):
        text = text.encode('ascii', 'ignore').lstrip().strip()
        return text

    def make_page_layouts(self, pdf_file, page_range, line_overlap,
                          char_margin,
                          line_margin,
                          word_margin,
                          boxes_flow):
        stored_layouts = klepto.archives.dir_archive('persist_pdf_layouts', serialized=True, cached=False)
        db_key = pdf_file.split('/')[-1] + '_' + str(page_range[0]) + '_' + str(page_range[1])
        # this will break image size when extracting figs
        if db_key in stored_layouts.keys() and False:
            page_layouts = stored_layouts[db_key]
        else:
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
                        if not self.page_vertical_dim:
                            self.page_vertical_dim = page.mediabox[-1]
            stored_layouts[db_key] = page_layouts
        return page_layouts

    def parse_pdf(self, file_path, page_ranges=None, extracting_answer_key=False):
        doc = pdf_poppler.Document(file_path)
        page_layouts = self.make_page_layouts(file_path, page_ranges, word_margin=0.1, line_overlap=0.5,
                                              char_margin=2.0, line_margin=0.5, boxes_flow=0.5)

        if not page_ranges:
            page_ranges = [0, doc.no_of_pages()]
        for idx, page in enumerate(doc):
            if page_ranges[0] < idx <= page_ranges[1]:
                page_figures = []
                for layout_ob in page_layouts[idx - page_ranges[0]]:
                    if isinstance(layout_ob, LTFigure):
                        page_figures.append(layout_ob.bbox)
                self.extract_page_text(idx, page, page_figures, file_path.split('/')[-1], extracting_answer_key)
        return self.filter_categories()

    def filter_categories(self):
        for k, v in self.parsed_content.items():
            if k.split(' ')[-1] in self.sections_to_ignore:
                del self.parsed_content[k]
            for topic in v.keys():
                if topic in self.sections_to_ignore:
                    del v[topic]
        return self.parsed_content

    def crop_and_extract_figure(self, page_n, fig_n, rectangle, extract_images=False):
        page_image_filename = 'pg_' + str(page_n + 1).zfill(4) + '.pdf.png'
        image_path = self.file_paths['rasterized_page_dir'] + page_image_filename
        cropped_image_path = self.file_paths['cropped_fig_dest_dir'] + self.current_lesson + '_' + self.current_topic + \
                             '_' + str(page_n + 1).zfill(4) + '_fig_' + fig_n + '.png'
        cropped_image_path = cropped_image_path.replace(' ', '_')
        if extract_images:
            page_image = Image.open(image_path)
            scale_factor = float(page_image.size[1]) / float(self.page_vertical_dim)
            scaled_box = [co * scale_factor for co in rectangle]
            temp = page_image.size[1] - scaled_box[3]
            scaled_box[3] = page_image.size[1] - scaled_box[1]
            scaled_box[1] = temp
            crop = page_image.crop(scaled_box)
            crop.save(cropped_image_path)
        return cropped_image_path

    @classmethod
    def compute_box_center(cls, box_rectangle):
        x1, y1, x2, y2 = box_rectangle
        return np.array([(x2 + x1) / float(2), (y2 + y1) / float(2)])

    @classmethod
    def compute_centers_separation(cls, text_box_center, image_box_center):
        return np.linalg.norm(text_box_center - image_box_center)

    def find_matching_image(self, caption_bbox, page_image_bboxes):
        closest_image = None
        min_dist = None
        caption_center = FlexbookParser.compute_box_center(caption_bbox)
        for image in page_image_bboxes:
            compare_image = list(deepcopy(image))
            compare_image[1] = self.page_vertical_dim - compare_image[1]
            compare_image[3] = self.page_vertical_dim - compare_image[3]
            image_center = FlexbookParser.compute_box_center(compare_image)
            separation = FlexbookParser.compute_centers_separation(caption_center, image_center)
            if not min_dist:
                min_dist = separation
                closest_image = image
            elif separation < min_dist:
                min_dist = separation
                closest_image = image
        return closest_image

    def near_last_figure_caption(self, line):
        if not self.last_figure_caption_seen:
            return False
        separation = line['rectangle'][1] - self.last_figure_caption_seen['rectangle'][3]
        if separation < self.line_sep_tol:
            self.last_figure_caption_seen = line
            return True
        else:
            return False

    def extract_page_text(self, idx, page, page_figures, book_name, extracting_answer_key):
        for flow in page:
            for block in flow:
                for line in block:
                    line_props = {
                        'content': self.normalize_text(line.text),
                        'rectangle': line.bbox.as_tuple(),
                        'font_size': list(line.char_fonts)[0].size,
                        'font_color': list(line.char_fonts)[0].color.as_tuple()
                    }
                    if 760 < line_props['rectangle'][3] or line_props['rectangle'][3] < 50 or not line_props['content']:
                        continue
                    if line_props['content'] and line_props['content'] not in self.strings_to_ignore:
                        if line_props['font_size'] == self.section_demarcations['lesson_size']:
                            self.current_lesson = line_props['content'].translate(string.maketrans("", ""), string.punctuation.replace('.', ''))
                            self.last_figure_caption_seen = None
                            self.current_topic_number = 1
                            self.parsed_content[self.current_lesson]['hidden'] = {"source": str(idx + 2) + '_' + book_name}

                        elif np.isclose(line_props['font_color'], self.section_demarcations['topic_color'], rtol=1e-04, atol=1e-04).min():
                            self.current_topic = line_props['content'].translate(string.maketrans("", ""), string.punctuation.replace('.', ''))
                            self.parsed_content[self.current_lesson][self.current_topic]['orderID'] = \
                                't_' + str(self.current_topic_number).zfill(2)
                            self.last_figure_caption_seen = None
                            self.current_topic_number += 1
                            self.parsed_content[self.current_lesson][self.current_topic]['text'].append('')
                        elif 'FIGURE ' in line_props['content']:
                            figure_number = line_props['content'].replace('FIGURE ', '')
                            new_figure_content = {}
                            new_figure_content['caption'] = line_props['content']
                            self.last_figure_caption_seen = line_props
                            nearest_image_bbox = self.find_matching_image(line_props['rectangle'], page_figures)
                            new_figure_content['rectangle'] = nearest_image_bbox
                            figure_file_name = self.crop_and_extract_figure(idx, figure_number, nearest_image_bbox, False)
                            new_figure_content['file_name'] = figure_file_name
                            self.parsed_content[self.current_lesson][self.current_topic]['figures'].append(new_figure_content)

                        elif not sum(line_props['font_color']) and self.current_topic:
                            if self.current_topic in self.treat_as_list:
                                self.parsed_content[self.current_lesson][self.current_topic]['text'][0] += line_props['content'] + self.list_separator
                            else:
                                if self.near_last_figure_caption(line_props):
                                    self.parsed_content[self.current_lesson][self.current_topic]['figures'][-1]['caption'] += self.line_separator + line_props['content']
                                elif self.parsed_content[self.current_lesson][self.current_topic]['text']:
                                    self.parsed_content[self.current_lesson][self.current_topic]['text'][0] += line_props['content'] + self.line_separator


class WorkbookParser(FlexbookParser):
    def __init__(self):
        super(WorkbookParser, self).__init__()
        self.sections_to_keep = ['True or False', 'Multiple Choice', 'Matching', 'Fill in the Blank']
        self.section_demarcations = {
            'topic_color': (0.811767578125, 0.3411712646484375, 0.149017333984375),
            'answer_lesson_size': 12.9115,
            'lesson_size': 22.3082,
            'ak_str': ' Worksheet Answer Key'
        }

        self.line_separator = '\n'
        self.wb_q_parser = WorkbookQuestionParser

    def extract_page_text(self, idx, page, page_figures, book_name, extracting_ans_key):
        for flow in page:
            for block in flow:
                for line in block:

                    line_props = {
                        'content': self.normalize_text(line.text),
                        'rectangle': line.bbox.as_tuple(),
                        'font_size': list(line.char_fonts)[0].size,
                        'font_color': list(line.char_fonts)[0].color.as_tuple()
                    }
                    if 760 < line_props['rectangle'][3] or line_props['rectangle'][3] < 50 or not line_props['content']:
                        continue
                    if line_props['content'] and line_props['content'] not in self.strings_to_ignore:
                        if line_props['font_size'] == self.section_demarcations['lesson_size']:
                            self.current_lesson = line_props['content'].translate(string.maketrans("", ""), string.punctuation.replace('.', ''))
                            self.last_figure_caption_seen = None
                            self.current_topic_number = 1
                        elif np.isclose(line_props['font_color'], self.section_demarcations['topic_color'], rtol=1e-04, atol=1e-04).min():
                            if line_props['font_size'] == self.section_demarcations['answer_lesson_size'] and extracting_ans_key:
                                found_lesson_number = re.findall("Lesson [0-9]+\.[1-9]+", line_props['content'])
                                if found_lesson_number:
                                    self.current_lesson = found_lesson_number[0]
                                    self.last_figure_caption_seen = None
                                    self.current_topic_number = 1
                            else:
                                self.current_topic = line_props['content']
                                self.parsed_content[self.current_lesson][self.current_topic]['orderID'] = \
                                    't_' + str(self.current_topic_number).zfill(2)
                                self.last_figure_caption_seen = None
                                self.current_topic_number += 1
                                self.parsed_content[self.current_lesson][self.current_topic]['text'].append('')

                        elif not sum(line_props['font_color']) and self.current_topic \
                                and self.parsed_content[self.current_lesson][self.current_topic]['text']:
                                self.parsed_content[self.current_lesson][self.current_topic]['text'][0] += line_props['content'] + self.line_separator

    def filter_categories(self):
        for k, v in self.parsed_content.items():
            if k.split(' ')[-1] in self.sections_to_ignore:
                del self.parsed_content[k]

    def flatten_lesson_types(self, section):
        section_questions = {}
        section_q_number = 0
        for question_type, questions in section.items():
            for question in questions.values():
                section_q_number += 1
                qid = 'q' + str(section_q_number).zfill(2)
                question['id'] = qid
                section_questions[qid] = question
        return {"nonDiagramQuestions": section_questions, "diagramQuestions": {}}

    def parse_answers(self):
        parsed_answer_sections = defaultdict(dict)
        for current_lesson, lesson in self.parsed_content.items():
            for section, content in lesson.items():
                section_type = section
                if section_type in self.sections_to_keep:
                    concat_content_str = ' '.join(content['text'])
                    answer_section_parser = self.wb_q_parser.get_type_specific_parser(section_type, True)
                    initial_parse = answer_section_parser.assemble_section(concat_content_str)
                    answer_section_parser.scan_answer_lines(initial_parse)
                    answer_section_parser.format_correct_answers(section_type)
                    parsed_answer_sections[current_lesson][section] = answer_section_parser.parsed_questions
        return parsed_answer_sections

    def parse_questions(self):
        parsed_question_sections = {}
        for k, v in self.parsed_content.items():
            parsed_question_sections[k] = {}
            for section, content in v.items():
                section_type = section.split(': ')[-1]
                if section_type in self.sections_to_keep:
                    concat_content_str = ' '.join(content['text'])
                    question_section_parser = self.wb_q_parser.get_type_specific_parser(section_type)
                    initial_parse = question_section_parser.assemble_section(concat_content_str)
                    question_section_parser.scan_lines(initial_parse)
                    question_section_parser.format_questions(section_type)
                    parsed_question_sections[k][section] = question_section_parser.parsed_questions
        return parsed_question_sections

    @classmethod
    def join_questions_w_answer_keys(cls, parsed_questions, parsed_answers):
        ans_key_set = set([re.findall("[0-9]+\.[1-9]+", ts)[0] for ts in parsed_answers.keys()])
        quest_key_set = set([re.findall("[0-9]+\.[1-9]+", ts)[0] for ts in parsed_questions.keys()])

        assert ans_key_set == quest_key_set
        for lesson, sections in parsed_questions.items():
            for section_name, section in sections.items():
                lesson_n, q_type = section_name.split(': ')
                for q_id, question in section.items():
                    try:
                        question['correctAnswer'] = parsed_answers[lesson_n][q_type][q_id]['correctAnswer']
                    except KeyError as e:
                        pass
                        print e
                        print lesson_n, q_type

    def restructure_parsed_content(self, workbook):
        return {k: {'questions': v} for k, v in workbook.items()}

    def parse_worksheet_pdf(self, file_path, question_pages, answer_pages):
        super(WorkbookParser, self).parse_pdf(file_path, question_pages)
        parsed_questions = self.parse_questions()

        self.reset_flex_parser()

        super(WorkbookParser, self).parse_pdf(file_path, answer_pages, True)
        parsed_answers = self.parse_answers()
        WorkbookParser.join_questions_w_answer_keys(parsed_questions, parsed_answers)
        flattened_workbook = {k: self.flatten_lesson_types(v) for k, v in parsed_questions.items()}
        # return parsed_questions, parsed_answers
        return self.restructure_parsed_content(flattened_workbook)


class WorkbookQuestionParser(QuestionTypeParser):
    def __init__(self):
        super(WorkbookQuestionParser, self).__init__()
        self.letter_starters = [char + '.' for char in string.ascii_lowercase[:12]]
        self.strings_to_ignore = ['Name___________________ Class______________ Date________',
                                  'Write true if the statement is true or false if the statement is false.',
                                  'Match each definition with the correct term.',
                                  'Fill in the blank with the appropriate term.',
                                  'Fill in the blank with the term that best completes the sentence.',
                                  'Circle the letter of the correct choice.']

    @classmethod
    def get_type_specific_parser(cls, section_type, answer_key=False):
        if section_type == 'Multiple Choice' and answer_key:
            return MultipleChoiceAKParser()
        elif section_type == 'Multiple Choice':
            return MultipleChoiceParser()
        elif section_type == 'Matching':
            return MatchingParser()
        elif section_type == 'True or False':
            return TrueFalseParser()
        elif section_type in ['Fill in the Blank', 'Fill in the Blanks']:
            return FillInBlankParser()

    def clean_box(self, box):
        box = {
            "rawText": box
        }
        return box

    def make_answer_component(self, box, structural_id):
        question_id = 'q' + str(self.current_question_number).zfill(2)
        self.parsed_questions[question_id] = OrderedDict()
        # order of property fields is important for get last values
        property_fields = [["id", question_id],
                           ["idStructural", structural_id],
                           ["correctAnswer", self.clean_box(box)]]

        for field in property_fields:
            self.parsed_questions[question_id][field[0]] = field[1]
        self.last_added_depth = 2

    def scan_lines(self, text_boxes):
        for idx, box_text in enumerate(text_boxes):
            start_type, starting_chars = self.check_starting_chars(box_text)
            if start_type == 'numeric start':
                self.current_question_number += 1
                self.make_question_component(box_text, starting_chars)
            if start_type in ['letter dot start', 'letter start']:
                self.make_answer_choice(box_text, starting_chars)
            if len(box_text) > 2 and not start_type:
                self.append_box_to_last_element(box_text)

    def scan_answer_lines(self, text_boxes):
        for idx, box_text in enumerate(text_boxes):
            start_type, starting_chars = self.check_starting_chars(box_text)
            if start_type == 'numeric start':
                self.current_question_number += 1
                self.make_answer_component(box_text, starting_chars)

            if len(box_text) > 2 and not start_type:
                self.append_box_to_last_element(box_text)

    def create_answer_choices(self):
        return {}

    def format_questions(self, section_type):
        for question in self.parsed_questions.values():
            question['type'] = section_type
            q_components = [question['beingAsked']]

            rck = 'rawText'
            pck = 'processedText'
            sik = 'idStructural'
            for component in q_components:
                if component and question[sik]:
                    component[pck] = component[rck].replace(question[sik], '').strip()
            if 'answerChoices' in question.keys():
                for cid, choice in question['answerChoices'].items():
                    if choice and choice[sik]:
                        choice[pck] = choice[rck].replace(choice[sik], '').strip()
            else:
                question['answerChoices'] = self.create_answer_choices()

    def format_correct_answers(self, section_type):
        for question in self.parsed_questions.values():
            question['type'] = section_type
            q_components = [question['correctAnswer']]
            rck = 'rawText'
            pck = 'processedText'
            sik = 'idStructural'
            for component in q_components:
                if component and question[sik]:
                    component[pck] = component[rck].replace(question[sik], '').strip()


class MultipleChoiceParser(WorkbookQuestionParser):
    def __init__(self):
        super(MultipleChoiceParser, self).__init__()
        self.numeric_starters = [str(n) + '. ' for n in range(15)]

    def assemble_section(self, section_str):
        questions = []
        lines = section_str.split('\n')
        for line in lines:
            if line in self.strings_to_ignore:
                continue
            start_type, starting_chars = self.check_starting_chars(line)
            if start_type in ['numeric start', 'letter start']:
                questions.append(line)
            else:
                for idx, q in enumerate(questions):
                    if len(q) < 3:
                        questions[idx] = ' '.join([q, line])
                        break
        return questions


class MultipleChoiceAKParser(WorkbookQuestionParser):

    def __init__(self):
        super(MultipleChoiceAKParser, self).__init__()

    def assemble_section(self, section_str):
        questions = []
        lines = section_str.split('\n')
        for line in lines:
            if line in self.strings_to_ignore:
                continue
            start_type, starting_chars = self.check_starting_chars(line)
            if start_type in ['numeric start', 'letter start']:
                questions.append(line)
            else:
                for idx, q in enumerate(questions):
                    if len(q) < 3:
                        questions[idx] = ' '.join([q, line])
                        break
        return questions


class TrueFalseParser(WorkbookQuestionParser):
    def __init__(self):
        super(TrueFalseParser, self).__init__()

    def assemble_section(self, section_str):
        questions = []
        lines = section_str.split('\n')
        for line in lines:
            if line in self.strings_to_ignore:
                continue
            line = line.replace('_______ ', '').replace('_____ ', '').replace('__ ', '')
            start_type, starting_chars = self.check_starting_chars(line)
            if start_type in ['numeric start']:
                questions.append(line)
            else:
                for idx, q in enumerate(questions):
                    if starting_chars and int(starting_chars.replace('.', ' ').replace(')', ' ')) < 10:
                        char_limit = 3
                    else:
                        char_limit = 4
                    if len(q) < char_limit:
                        questions[idx] = q + line
                        break
        return questions

    def create_answer_choices(self):
        tf_answer_choices = {
            'a': {
                'idStructural': 'a.',
                'processedText': 'true',
                'rawText': 'a. true',
                },
            'b': {
                'idStructural': 'b.',
                'processedText': 'false',
                'rawText': 'b. false'
                }
        }
        return tf_answer_choices


class FillInBlankParser(WorkbookQuestionParser):

    def __init__(self):
        super(FillInBlankParser, self).__init__()

    def assemble_section(self, section_str):
        questions = []
        lines = section_str.split('\n')
        for line in lines:
            if line in self.strings_to_ignore:
                continue
            start_type, starting_chars = self.check_starting_chars(line)
            if starting_chars in self.numeric_starters:
                questions.append(line)
            else:
                appended = False
                for idx, q in enumerate(questions):
                    _, starting_chars = self.check_starting_chars(q)
                    if int(starting_chars.replace('.', ' ').replace(')', ' ')) < 10:
                        char_limit = 3
                    else:
                        char_limit = 4
                    if len(q) < char_limit:
                        questions[idx] = q + ' ' + line
                        appended = True
                        break
                if not appended and questions:
                    questions[-1] = ' '.join([questions[-1], line])
        return questions


class MatchingParser(WorkbookQuestionParser):
    def __init__(self):
        super(MatchingParser, self).__init__()

    def assemble_section(self, section_str):
        questions = []
        lines = section_str.split('\n')
        for line in lines:
            if line in self.strings_to_ignore:
                continue
            line = line.replace('_____ ', '').replace('__ ', '')
            start_type, starting_chars = self.check_starting_chars(line)
            if start_type in ['numeric start', 'letter start']:
                questions.append(line)
            else:
                for idx, q in enumerate(questions):
                    if len(q) < 3:
                        questions[idx] = q + line
                        break
        return questions

    def scan_lines(self, text_boxes):
        question_half = text_boxes[:len(text_boxes) / 2]
        answer_half = text_boxes[len(text_boxes) / 2:]
        for idx, box_text in enumerate(question_half):
            start_type, starting_chars = self.check_starting_chars(box_text)
            if start_type == 'numeric start':
                self.current_question_number += 1
                self.make_question_component(box_text, starting_chars)
                for ac in answer_half:
                    _, answer_starting_chars = self.check_starting_chars(ac)
                    self.make_answer_choice(ac, answer_starting_chars)
            if len(box_text) > 2 and not start_type:
                self.append_box_to_last_element(box_text)


class QuizTestParser(WorkbookParser):
    def __init__(self):
        super(QuizTestParser, self).__init__()
        self.sections_to_keep = ['True or False', 'Multiple Choice', 'Matching', 'Fill in the Blanks', 'Fill in the Blank']
        self.sections_to_ignore = ['Short Answer']
        self.section_demarcations = {
            'topic_color': (0.811767578125, 0.3411712646484375, 0.149017333984375),
            'answer_lesson_size': 12.9115,
            'lesson_size': 22.3082,
            'ak_str': ' Worksheet Answer Key'
        }
        self.strings_to_ignore.append('Name___________________ Class______________ Date________')
        self.question_sections = ['Lesson Quiz', 'Chapter Test']
        self.answer_sections = ['Answer Key', 'Lesson Quiz Answer Key']
        self.line_separator = '\n'
        self.wb_q_parser = WorkbookQuestionParser
        self.lesson_n_pattern = re.compile('\s[0-9]+?\.[0-9]*\s')
        self.numeric_starters = [str(n) + '.' for n in range(41)]
        self.numeric_starters += [str(n) + ')' for n in range(41)]

    def extract_page_text(self, idx, page, page_figures, book_name, extracting_ans_key):
        for flow in page:
            for block in flow:
                for line in block:
                    line_props = {
                        'content': self.normalize_text(line.text),
                        'rectangle': line.bbox.as_tuple(),
                        'font_size': list(line.char_fonts)[0].size,
                        'font_color': list(line.char_fonts)[0].color.as_tuple()
                    }
                    if 760 < line_props['rectangle'][3] or line_props['rectangle'][3] < 50 or not line_props['content']:
                        continue
                    if line_props['content'] and line_props['content'] not in self.strings_to_ignore:
                        if line_props['font_size'] == self.section_demarcations['lesson_size']:
                            self.current_lesson = line_props['content'].translate(string.maketrans("", ""),
                                                                                  string.punctuation.replace('.', ''))
                            self.last_figure_caption_seen = None
                            self.current_topic_number = 1
                        elif np.isclose(line_props['font_color'], self.section_demarcations['topic_color'], rtol=1e-04,
                                        atol=1e-04).min():
                            if line_props['font_size'] == self.section_demarcations['answer_lesson_size'] and extracting_ans_key:
                                found_lesson_number = re.findall("Lesson [0-9]+\.[1-9]+", line_props['content'])
                                if found_lesson_number:
                                    self.current_lesson = found_lesson_number[0]
                                    self.last_figure_caption_seen = None
                                    self.current_topic_number = 1
                            else:
                                self.current_topic = self.lesson_n_pattern.sub(' ', line_props['content'])
                                self.parsed_content[self.current_lesson][self.current_topic]['orderID'] = \
                                    't_' + str(self.current_topic_number).zfill(2)
                                self.last_figure_caption_seen = None
                                self.current_topic_number += 1
                                self.parsed_content[self.current_lesson][self.current_topic]['text'].append('')
                        elif not sum(line_props['font_color']) and self.current_topic \
                                and self.parsed_content[self.current_lesson][self.current_topic]['text']:
                            self.parsed_content[self.current_lesson][self.current_topic]['text'][0] += line_props['content'] + self.line_separator

    def parse_quiz_pdf(self, file_path, question_pages):
        super(WorkbookParser, self).parse_pdf(file_path, question_pages)
        parsed_questions, parsed_answers = self.parse_questions_and_answers()

        self.join_questions_w_answer_keys(parsed_questions, parsed_answers)
        flattened_workbook = {k: self.flatten_lesson_types(v) for k, v in parsed_questions.items()}
        return self.restructure_parsed_content(flattened_workbook)

    def parse_answer_key_string(self, concat_section_string):
        parsed_answers = defaultdict(dict)
        current_q_number = None
        for text_bit in concat_section_string.replace(self.line_separator, ' ').split():
            if text_bit in self.numeric_starters:
                current_q_number = text_bit
            else:
                parsed_answers[current_q_number] = text_bit
        return parsed_answers

    def parse_questions_and_answers(self):
        parsed_question_sections = {}
        parsed_answer_sections = {}
        for k, v in self.parsed_content.items():
            parsed_question_sections[k] = {}
            parsed_answer_sections[k] = {}
            for section, content in v.items():
                concat_content_str = ' '.join(content['text'])
                content_lines = concat_content_str.split(self.line_separator)
                if section in self.question_sections:
                    questions_by_type = defaultdict(list)
                    current_q_type = 'orphaned'
                    for text_line in content_lines:
                        if text_line in self.strings_to_ignore + self.sections_to_ignore:
                            current_q_type = 'orphaned'
                            continue
                        elif text_line in self.sections_to_keep:
                            current_q_type = text_line
                        else:
                            questions_by_type[current_q_type].append(text_line)
                    if 'orphaned' in questions_by_type.keys():
                        del questions_by_type['orphaned']
                    for section_type, q_sect in questions_by_type.items():
                        concat_content_str = self.line_separator.join(q_sect)
                        question_section_parser = self.wb_q_parser.get_type_specific_parser(section_type)
                        initial_parse = question_section_parser.assemble_section(concat_content_str)
                        question_section_parser.scan_lines(initial_parse)
                        question_section_parser.format_questions(section_type)
                        parsed_question_sections[k][section_type] = question_section_parser.parsed_questions

                elif section in self.answer_sections:
                    concat_content_str = ' '.join(content['text'])
                    ak_parser = self.wb_q_parser.get_type_specific_parser('Fill in the Blank')
                    initial_parse = ak_parser.assemble_section(concat_content_str)
                    joined_parse = ' '.join(initial_parse)
                    # parsed_answer_sections[k][section] = self.parse_answer_key_string(concat_content_str)
                    parsed_answer_sections[k][section] = self.parse_answer_key_string(joined_parse)
        return parsed_question_sections, parsed_answer_sections

    def join_questions_w_answer_keys(self, parsed_questions, parsed_answers):
        ans_key_set = set([re.findall("[0-9]+\.[1-9]+", ts)[0] for ts in parsed_answers.keys()])
        quest_key_set = set([re.findall("[0-9]+\.[1-9]+", ts)[0] for ts in parsed_questions.keys()])
        assert ans_key_set == quest_key_set
        for lesson, content in parsed_questions.items():
            for q_type, questions in content.items():
                for qid, question in questions.items():
                    if parsed_answers[lesson].values():
                        correct_answer = parsed_answers[lesson].values()[0][question['idStructural'].strip()]
                        question['correctAnswer'] = {
                                "processedText": correct_answer,
                                "rawText": correct_answer}


class TextbookParser(FlexbookParser):

    def __init__(self, overlap_tol=None, blank_threshold=None):
        super(TextbookParser, self).__init__(overlap_tol, blank_threshold)

    def restructure_parsed_content(self, pdf_path):
        local_path = '../flexbook_image_extraction/figures/'
        s3_uri = 'https://s3.amazonaws.com/ai2-vision-textbook-dataset/ck12/flexbooks/extracted-figures/'

        for lesson, subcontent in self.parsed_content.items():
            for concept, content in subcontent.items():
                if concept == 'hidden':
                    continue
                content['text'] = content['text'][0]
                for fig in content['figures']:
                    fig['image_uri'] = fig['file_name'].replace(local_path, s3_uri)
                    del fig['rectangle']
                    del fig['file_name']
                content['content'] = {}
                content['content']['text'] = content.pop('text')
                content['content']['figures'] = content.pop('figures')
        self.parsed_content = {k: {'topics': v} for k, v in self.parsed_content.items()}
        for k, v in self.parsed_content.items():
            v['hidden'] = v['topics'].pop('hidden')

    def parse_pdf(self, pdf_path, page_ranges=None):
        super(TextbookParser, self).parse_pdf(pdf_path, page_ranges)
        self.restructure_parsed_content(pdf_path)
        return self.parsed_content


class GradeSchoolFlexbookParser(TextbookParser):
    def __init__(self, rasterized_pages_dir=None, figure_dest_dir=None):
        super(GradeSchoolFlexbookParser, self).__init__(rasterized_pages_dir, figure_dest_dir)
        self.line_sep_tol = 10
        self.section_demarcations = {
            'topic_color': (0.811767578125, 0.3411712646484375, 0.149017333984375),
            'lesson_size': 22.3082,
            'topic_size': 10.7596
        }

    def extract_page_text(self, idx, page, page_figures, book_name, extracting_answer_key):
        for flow in page:
            for block in flow:
                for line in block:
                    line_props = {
                        'content': self.normalize_text(line.text),
                        'rectangle': line.bbox.as_tuple(),
                        'font_size': list(line.char_fonts)[0].size,
                        'font_color': list(line.char_fonts)[0].color.as_tuple()
                    }
                    if 760 < line_props['rectangle'][3] or line_props['rectangle'][3] < 50 or not line_props['content']:
                        continue
                    # print line_props
                    if line_props['content'] and line_props['content'] not in self.strings_to_ignore:
                        if line_props['font_size'] == self.section_demarcations['lesson_size']:
                            self.current_lesson = line_props['content'].translate(string.maketrans("", ""), string.punctuation.replace('.', ''))
                            self.last_figure_caption_seen = None

                        elif 'FIGURE ' in line_props['content']:
                            figure_number = line_props['content'].replace('FIGURE ', '')
                            new_figure_content = {}
                            new_figure_content['caption'] = line_props['content']
                            self.last_figure_caption_seen = line_props
                            nearest_image_bbox = self.find_matching_image(line_props['rectangle'], page_figures)
                            new_figure_content['rectangle'] = nearest_image_bbox
                            figure_file_name = self.crop_and_extract_figure(idx, figure_number, nearest_image_bbox)
                            new_figure_content['file_name'] = figure_file_name
                            self.parsed_content[self.current_lesson][self.current_topic]['figures'].append(new_figure_content)

                        elif np.isclose(line_props['font_color'], self.section_demarcations['topic_color'], rtol=1e-04, atol=1e-04).min() \
                                or line_props['font_size'] == self.section_demarcations['topic_size']:
                            self.current_topic = line_props['content']
                            self.last_figure_caption_seen = None
                            self.parsed_content[self.current_lesson][self.current_topic]['text'].append('')

                        elif not sum(line_props['font_color']) and self.current_topic:
                            if self.current_topic in self.treat_as_list:
                                self.parsed_content[self.current_lesson][self.current_topic]['text'][0] += line_props['content'] + self.list_separator
                            else:
                                if self.near_last_figure_caption(line_props):
                                    self.parsed_content[self.current_lesson][self.current_topic]['figures'][-1]['caption'] += self.line_separator + line_props['content']
                                elif self.parsed_content[self.current_lesson][self.current_topic]['text']:
                                    self.parsed_content[self.current_lesson][self.current_topic]['text'][0] += line_props['content'] + self.line_separator


class LessonParser(TextbookParser):

    def __init__(self, overlap_tol=None, blank_threshold=None):
        super(LessonParser, self).__init__(overlap_tol, blank_threshold)
        self.section_demarcations = {
            'topic_color': (0.811767578125, 0.3411712646484375, 0.149017333984375),
            'lesson_size': 26.8989,
            'topic_size': 10.7596
        }
        self.strings_to_ignore.append('MEDIA')

    def extract_page_text(self, idx, page, page_figures, book_name, extracting_answer_key):
        for flow in page:
            for block in flow:
                for line in block:
                    line_props = {
                        'content': self.normalize_text(line.text),
                        'rectangle': line.bbox.as_tuple(),
                        'font_size': list(line.char_fonts)[0].size,
                        'font_color': list(line.char_fonts)[0].color.as_tuple()
                    }
                    if 760 < line_props['rectangle'][3] or line_props['rectangle'][3] < 50 or not line_props['content']:
                        continue
                    # print line_props
                    if line_props['content'] and line_props['content'] not in self.strings_to_ignore:
                        if line_props['font_size'] >= self.section_demarcations['lesson_size'] and len(line_props['content']) > 1:
                            if not self.current_lesson:
                                self.current_lesson = line_props['content'].translate(string.maketrans("", ""), string.punctuation.replace('.', ''))
                                self.last_figure_caption_seen = None
                                self.current_topic_number = 1
                            else:
                                self.current_lesson += ' ' + line_props['content'].translate(string.maketrans("", ""), string.punctuation.replace('.', ''))

                        elif 'FIGURE ' in line_props['content']:
                            figure_number = line_props['content'].replace('FIGURE ', '')
                            new_figure_content = {}
                            new_figure_content['caption'] = line_props['content']
                            self.last_figure_caption_seen = line_props
                            nearest_image_bbox = self.find_matching_image(line_props['rectangle'], page_figures)
                            new_figure_content['rectangle'] = nearest_image_bbox
                            figure_file_name = self.crop_and_extract_figure(idx, figure_number, nearest_image_bbox, True)
                            new_figure_content['file_name'] = figure_file_name
                            self.parsed_content[self.current_lesson][self.current_topic]['figures'].append(new_figure_content)

                        elif np.isclose(line_props['font_color'], self.section_demarcations['topic_color'], rtol=1e-04, atol=1e-04).min() \
                                or line_props['font_size'] == self.section_demarcations['topic_size']:
                            self.current_topic = line_props['content'].translate(string.maketrans("", ""), string.punctuation.replace('.', ''))
                            self.parsed_content[self.current_lesson][self.current_topic]['orderID'] = \
                                't_' + str(self.current_topic_number).zfill(2)
                            self.last_figure_caption_seen = None
                            self.current_topic_number += 1
                            self.parsed_content[self.current_lesson][self.current_topic]['text'].append('')

                        elif not sum(line_props['font_color']) and self.current_topic:
                            if self.current_topic in self.treat_as_list:
                                self.parsed_content[self.current_lesson][self.current_topic]['text'][0] += line_props['content'] + self.list_separator
                            else:
                                if self.near_last_figure_caption(line_props):
                                    self.parsed_content[self.current_lesson][self.current_topic]['figures'][-1]['caption'] += self.line_separator + line_props['content']
                                elif self.parsed_content[self.current_lesson][self.current_topic]['text']:
                                    self.parsed_content[self.current_lesson][self.current_topic]['text'][0] += line_props['content'] + self.line_separator
        self.parsed_content[self.current_lesson]['hidden'] = {"source": str(1) + '_' + book_name}


class CK12DataSetAssembler(object):

    def __init__(self):
        self.ck12_dataset = None
        self.char_match_thresh = 85
        self.schema = ck12_schema.ck12_schema

    def join_content_and_questions(self, flexbook, workbook):
        if 'questions' not in flexbook.values()[0].keys():
            self.check_and_match_topics(flexbook, workbook)
            joined_flexbook = {k: v.update(**workbook[k]) for k, v in flexbook.items()}
            self.ck12_dataset = self.jsonify(joined_flexbook)
            return flexbook
        else:
            for lesson, content in workbook.items():
                if lesson not in flexbook.keys():
                    continue
                renumber_offset = len(flexbook[lesson]['questions']['nonDiagramQuestions'])
                for old_qn, question in content['questions']['nonDiagramQuestions'].items():
                    new_q_n = 'q' + str(int(old_qn[1:]) + renumber_offset).zfill(2)
                    flexbook[lesson]['questions']['nonDiagramQuestions'][new_q_n] = question
            return flexbook

    def handle_special_cases(self, key):
        if key == 'three rnas':
            return 'rna'
        else:
            return None

    def check_and_match_topics(self, flexbook, workbook):
        fb_keys = set(flexbook.keys())
        wb_keys = set(workbook.keys())

        if fb_keys != wb_keys:
            fb_keys_missing = fb_keys.difference(wb_keys)
            print 'topic mismatch, attempting to match keys: ' + str(fb_keys_missing)
            if list(fb_keys)[0][0].isdigit() and list(wb_keys)[0][0].isdigit():
                print 'by number'
                for wb_topic in wb_keys:
                    for fb_topic in fb_keys_missing:
                        wb_lesson_number = re.findall("[0-9]+\.[1-9]+", wb_topic)[0]
                        fb_lesson_number = re.findall("[0-9]+\.[1-9]+", fb_topic)[0]
                        if wb_lesson_number == fb_lesson_number:
                            workbook[fb_topic] = workbook.pop(wb_topic)

            else:
                print 'by title'
                for wb_topic in wb_keys:
                    for fb_topic in fb_keys_missing:
                        char_match = fuzzywuzzy.fuzz.ratio(wb_topic, fb_topic)
                        if char_match > self.char_match_thresh:
                            if wb_topic in ['oceancontinent convergent plate boundaries', 'oceanocean convergent plate boundaries',
                                            'continentcontinent convergent plate boundaries']:
                                continue
                            workbook[fb_topic] = workbook.pop(wb_topic)

        wb_keys = set(workbook.keys())
        fb_keys_missing = fb_keys.difference(wb_keys)
        print
        print fb_keys_missing
        if fb_keys != wb_keys:
            for wb_topic in wb_keys:
                for fb_topic in fb_keys_missing:
                    special_fix = self.handle_special_cases(wb_topic)
                    if special_fix == fb_topic:
                        workbook[special_fix] = workbook.pop(wb_topic)
            wb_keys = set(workbook.keys())
            fb_keys_missing = fb_keys.difference(wb_keys)
            print fb_keys_missing
            if fb_keys != wb_keys:
                for fb_topic in fb_keys_missing:
                    print 'removing ' + fb_topic
                    flexbook.pop(fb_topic)
            # print fb_keys.difference(wb_keys)
        # assert fb_keys == wb_keys

    def validate_schema(self, dataset_json):
        try:
            validator = jsonschema.Draft4Validator(self.schema)
            for error in sorted(validator.iter_errors(dataset_json), key=str):
                print error.message
        except jsonschema.ValidationError as e:
            warnings.warn("Error in schema --%s-", e.message)

    def validate_dataset(self, dataset_json):
        for subject, flexbook in dataset_json.items():
            print 'validating schema for ' + str(subject)
            print '\n'
            self.validate_schema(flexbook)
            print '\n' * 2
            print 'checking answer choice counts'
            for lesson_name, lesson in flexbook.items():
                pass
                self.check_ac_counts(lesson, subject, lesson_name)

    def check_ac_counts(self, lesson_content, subject, lesson_name):
            for qid, question in lesson_content['questions']['nonDiagramQuestions'].items():
                if question['type'] == 'Multiple Choice':
                    if len(question['answerChoices']) != 4:
                        print subject, lesson_name
                        print qid + ' mc error'
                if question['type'] == 'True or False':
                    if len(question['answerChoices']) != 2:
                        print subject, lesson_name
                        print qid + ' tf error'

    def jsonify(self, dataset_w_collections):
        return json.loads(json.dumps(dataset_w_collections))

    def write_file(self):
        with open('./ck12_dataset_draft_1.json', 'w') as f:
            json.dump(self.ck12_dataset, f, indent=4, sort_keys=True)


class VocabDefinitionParser(FlexbookParser):

    def __init__(self, rasterized_pages_dir=None, figure_dest_dir=None):
        super(VocabDefinitionParser, self).__init__(rasterized_pages_dir, figure_dest_dir)
        self.line_sep_tol = 10
        self.current_word = None
        self.parsed_content = defaultdict(str)
        self.section_demarcations = {
            'vocab_size': 10.9091,
            'indent_thresh': 60
        }

    def match_word_to_def(self):
        pass

    def extract_page_text(self, idx, page, page_figures, book_name, extracting_answer_key):
        for flow in page:
            for block in flow:
                for line in block:
                    line_props = {
                        'content': self.normalize_text(line.text),
                        'rectangle': line.bbox.as_tuple(),
                        'font_size': list(line.char_fonts)[0].size,
                        'font_color': list(line.char_fonts)[0].color.as_tuple()
                    }
                    if 760 < line_props['rectangle'][3] or line_props['rectangle'][3] < 50 or not line_props['content']:
                        continue
                    # print line_props
                    if line_props['content'] and line_props['font_size'] == self.section_demarcations['vocab_size']:
                            if line_props['rectangle'][0] < self.section_demarcations['indent_thresh']:
                                self.current_word = line_props['content']
                            elif self.current_word:
                                self.parsed_content[self.current_word] += line_props['content'] + self.line_separator

    def filter_categories(self):
        return self.parsed_content


def refine_parsed_quizzes(parsed_quizzes):
    quiz_parser = CK12QuizParser()
    for quiz in parsed_quizzes.values():
        quiz_parser.refine_parsed_page(quiz)


def parse_pdf_collection(pdf_dir):
    quiz_content = {}
    for pdf_file in glob.glob(pdf_dir + '/*'):
        quiz_parser = CK12QuizParser()
        try:
            parsed_quiz = quiz_parser.parse_pdf(pdf_file)
            if parsed_quiz['title'] in quiz_content.keys():
                parsed_quiz['title'] += ' second version'
            quiz_content[parsed_quiz['title']] = parsed_quiz
        except (IndexError, KeyError) as e:
            print pdf_file
    refined_parsed_content = deepcopy(quiz_content)
    refine_parsed_quizzes(refined_parsed_content)
    return refined_parsed_content
