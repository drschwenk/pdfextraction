import glob
import string
import functools
import os
import pdfparser.poppler as pdf_poppler
from collections import defaultdict
from collections import OrderedDict
from copy import deepcopy
import PIL.Image as Image
import numpy as np

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
        self.numeric_starters = [str(n) + '.' for n in range(15)]
        self.numeric_starters += [str(n) + ')' for n in range(15)]
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
        if 'correct_answer' not in self.parsed_questions[question_id].keys():
            self.parsed_questions[question_id]['correct_answer'] = {}
            self.parsed_questions[question_id]['correct_answer']['idStructural'] = structural_id
            self.parsed_questions[question_id]['correct_answer']['processedText'] = box['processedText']
        else:
            self.parsed_questions[question_id]['correct_answer']['processedText'] += ' ' + box['processedText']
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
            q_type = 'True/False'
            parsed_question['beingAsked']['processedText'] = \
                parsed_question['beingAsked']['processedText'].replace('true or false: ', '')
        if '____' in parsed_question['beingAsked']['processedText'] and q_type == 'None':
            q_type = 'Fill-in-the-Blank'
        if parsed_question['beingAsked'] and 'answerChoices' not in parsed_question.keys() and q_type == 'None':
            q_type = 'Short Answer'
        if 'answerChoices' in parsed_question.keys() and len(parsed_question['answerChoices']) == 4:
            q_type = 'Multiple Choice'
        if 'answerChoices' in parsed_question.keys() and len(parsed_question['answerChoices']) == 2:
            q_type = 'True/False'
        return q_type

    @classmethod
    def sanitize_parsed_quiz(cls, question):
        q_components = [question['beingAsked']] + [question['correct_answer']]
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

    def refine_parsed_page(self, parsed_page):
        for qid, question in parsed_page['nonDiagramQuestions'].items():
            question['type'] = self.classify_question(question)
            if 'correct_answer' not in question.keys() and 'answerChoices' in question.keys():
                question['correct_answer'] = {}
                for ac_id, answer_choice in question['answerChoices'].items():
                    if answer_choice['correct']:
                        question['correct_answer']['idStructural'] = answer_choice['idStructural']
                        question['correct_answer']['processedText'] = answer_choice['processedText']
            if 'answerChoices' not in question.keys() and question['type'] == 'True/False':
                question['answerChoices'] = {
                    'a': {
                        'idStructural': 'a',
                        'processedText': 'true',
                        'rawText': 'a. true'
                        },
                    'b': {
                        'idStructural': 'b',
                        'processedText': 'false',
                        'rawText': 'b. false'
                        }
                }
            if 'correct_answer' not in question.keys():
                question['correct_answer'] = '_MISSING_'

            CK12QuizParser.sanitize_parsed_quiz(question)


class FlexbookParser(object):

    def __init__(self, rasterized_pages_dir=None, figure_dest_dir=None):
        self.current_lesson = None
        self.current_topic = None
        self.parsed_content = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        self.last_figure_caption_seen = None
        self.sections_to_ignore = ['References']
        self.captions_starters = ['MEDIA ', 'FIGURE ']
        self.treat_as_list = ['Lesson Vocabulary', 'Lesson Objectives']
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

    def normalize_text(self, text):
        text = text.encode('ascii', 'ignore').lstrip().strip()
        return text

    def make_page_layouts(self, pdf_file, page_range, line_overlap,
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
                    if not self.page_vertical_dim:
                        self.page_vertical_dim = page.mediabox[-1]
        return page_layouts

    def parse_pdf(self, file_path, page_ranges=None):
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
                self.extract_page_text(idx, page, page_figures)
        return self.filter_categories()

    def filter_categories(self):
        cleaned_content = {k: v for k, v in self.parsed_content.items() if
                           not sum([st in k for st in self.sections_to_ignore])}
        return cleaned_content

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

    def extract_page_text(self, idx, page, page_figures):
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
                            self.current_lesson = line_props['content']
                            self.last_figure_caption_seen = None

                        elif np.isclose(line_props['font_color'], self.section_demarcations['topic_color'], rtol=1e-04, atol=1e-04).min():
                            self.current_topic = line_props['content']
                            self.last_figure_caption_seen = None

                            self.parsed_content[self.current_lesson][self.current_topic]['text'].append('')
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

                        elif not sum(line_props['font_color']) and self.current_topic:
                            if self.current_topic in self.treat_as_list:
                                self.parsed_content[self.current_lesson][self.current_topic]['text'][0] += line_props['content'] + self.list_separator
                            else:
                                if self.near_last_figure_caption(line_props):
                                    self.parsed_content[self.current_lesson][self.current_topic]['figures'][-1]['caption'] += self.line_separator + line_props['content']
                                elif self.parsed_content[self.current_lesson][self.current_topic]['text']:
                                    self.parsed_content[self.current_lesson][self.current_topic]['text'][0] += line_props['content'] + self.line_separator


class GradeSchoolFlexbookParser(FlexbookParser):
    def __init__(self, rasterized_pages_dir=None, figure_dest_dir=None):
        super(GradeSchoolFlexbookParser, self).__init__(rasterized_pages_dir, figure_dest_dir)
        self.line_sep_tol = 10
        self.section_demarcations = {
            'topic_color': (0.811767578125, 0.3411712646484375, 0.149017333984375),
            'lesson_size': 22.3082,
            'topic_size': 10.7596
        }

    def extract_page_text(self, idx, page, page_figures):
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
                            self.current_lesson = line_props['content']
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


class WorkbookParser(FlexbookParser):
    def __init__(self):
        super(WorkbookParser, self).__init__()
        self.sections_to_ignore = ['Critical Reading', 'Critical Writing']
        self.line_separator = '\n'
        self.wb_q_parser = WorkbookQuestionParser

    def crop_and_extract_figure(self, page_n, fig_n, rectangle, extract_images=False):
        return None

    def flatten_lesson_types(self, section):
        section_questions = {}
        section_q_number = 0
        for question_type, questions in section.items():
            for question in questions.values():
                section_q_number += 1
                qid = 'q' + str(section_q_number).zfill(2)
                question['id'] = qid
                section_questions[qid] = question
        return {"nonDiagramQuestions": section_questions}

    def parse_questions(self):
        sections_to_keep = {}
        for k, v in self.parsed_content.items():
            sections_to_keep[k] = {}
            for section, content in v.items():
                section_type = section.split(': ')[-1]
                if section_type in ['True or False', 'Multiple Choice', 'Matching', 'Fill in the Blank']:
                    concat_content_str = ' '.join(content['text'])
                    question_section_parser = self.wb_q_parser.get_type_specific_parser(section_type)
                    initial_parse = question_section_parser.assemble_section(concat_content_str)
                    question_section_parser.scan_lines(initial_parse)
                    question_section_parser.format_questions(section_type)
                    sections_to_keep[k][section] = question_section_parser.parsed_questions
        flattened_book = {k: self.flatten_lesson_types(v) for k, v in sections_to_keep.items()}
        return flattened_book

    def parse_pdf(self, file_path, page_ranges=None):
        super(WorkbookParser, self).parse_pdf(file_path, page_ranges)
        return self.parse_questions()


class WorkbookQuestionParser(QuestionTypeParser):
    def __init__(self):
        super(WorkbookQuestionParser, self).__init__()
        self.letter_starters = [char + '.' for char in string.ascii_lowercase[:12]]
        self.sections_to_ignore = ['Critical Reading', 'Critical Writing']
        self.strings_to_ignore = ['Name___________________ Class______________ Date________',
                                  'Write true if the statement is true or false if the statement is false.',
                                  'Match each definition with the correct term.',
                                  'Fill in the blank with the appropriate term.',
                                  'Circle the letter of the correct choice.']

    @classmethod
    def get_type_specific_parser(cls, section_type):
        if section_type == 'Multiple Choice':
            return MultipleChoiceParser()
        elif section_type == 'Matching':
            return MatchingParser()
        elif section_type == 'True or False':
            return TrueFalseParser()
        elif section_type == 'Fill in the Blank':
            return FillInBlankParser()

    def clean_box(self, box):
        box = {
            "rawText": box
        }
        return box

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

    def create_answer_choices(self):
        return {}

    def format_questions(self, section_type):
        for question in self.parsed_questions.values():
            question['type'] = section_type
            q_components = [question['beingAsked']]#] + [question['correct_answer']]
            rck = 'rawText'
            pck = 'processedText'
            sik = 'idStructural'
            for component in q_components:
                if component and question[sik]:
                    component[pck] = component[rck].replace(question[sik], '').strip()
            if 'answerChoices' in question.keys():
                for component in question['answerChoices'].values():
                    component[pck] = component[rck].replace(component['idStructural'], '').strip()
            else:
                question['answerChoices'] = self.create_answer_choices()


class MultipleChoiceParser(WorkbookQuestionParser):
    def __init__(self):
        super(MultipleChoiceParser, self).__init__()

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
            start_type, starting_chars = self.check_starting_chars(line)
            if start_type in ['numeric start']:
                questions.append(line)
            else:
                for idx, q in enumerate(questions):
                    if len(q) < 3:
                        questions[idx] = q + line
                        break
        return questions

    def create_answer_choices(self):
        tf_answer_choices = {
            'a': {
                'idStructural': 'a',
                'processedText': 'true',
                'rawText': 'a. true',
                },
            'b': {
                'idStructural': 'b',
                'processedText': 'false',
                'rawText': 'b. false'
                }
        }
        return tf_answer_choices


class FillInBlankParser(WorkbookQuestionParser):
    def assemble_section(self, section_str):
        questions = []
        lines = section_str.split('\n')
        for line in lines:
            if line in self.strings_to_ignore:
                continue
            if line in self.numeric_starters:
                questions.append(line)
            else:
                for idx, q in enumerate(questions):
                    if len(q) < 3:
                        questions[idx] = q + line
                        break
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


class QuizParser(FlexbookParser):
    def __init__(self):
        super(QuizParser, self).__init__()


def refine_parsed_quizzes(parsed_quizzes):
    quiz_parser = CK12QuizParser()
    for quiz in parsed_quizzes.values():
        quiz_parser.refine_parsed_page(quiz)


def simple_quiz_parser_test(parsed_quizzes):
    for quiz_n, quiz in parsed_quizzes.items():
        for qid, quest in quiz['nonDiagramQuestions'].items():
            if quest['type'] == 'Multiple Choice':
                if len(quest['answerChoices']) != 4:
                    print quiz_n + ' mc error'
            if quest['type'] == 'True/False':
                if len(quest['answerChoices']) != 2:
                    print quiz_n + ' tf error'
            # if quest['type'] in ['Short Answer', 'Fill-in-the-Blank']:
            #     if 'answerChoices' in quest.keys():
            #         print quiz_n + ' sa or fib error'


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
    return quiz_content
