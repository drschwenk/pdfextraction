import glob
import string
import functools
import pdfparser.poppler as pdf
from collections import defaultdict
from collections import OrderedDict
from copy import deepcopy
import numpy as np


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


class QuestionTypeParser(object):
    def __init__(self, overlap_tol=None, blank_threshold=None):
        self.numeric_starters = [str(n) + '.' for n in range(15)]
        self.numeric_starters += [str(n) + ')' for n in range(15)]
        self.letter_starters = [char + ')' for char in string.ascii_uppercase[:6]]
        self.letter_starters += [char + ')' for char in string.ascii_lowercase[:6]]
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

    @classmethod
    def clean_box(cls, box):
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
        combined_raw_words = self.blank_signifier.join(map(lambda x: x['raw_content'], sorted_box_groups))
        combined_words = self.blank_signifier.join(map(lambda x: x['processed_content'], sorted_box_groups))
        combined_rect = [min_x, min_y, max_x, max_y]
        new_box = {
            'correct': sorted_box_groups[0]['correct'],
            'raw_content': combined_raw_words,
            'processed_content': combined_words,
            'structural_id': sorted_box_groups[0]['structural_id'],
            'rectangle': combined_rect}
        return new_box

    def append_box_to_last_element(self, box):
        last_val = self.get_last_added(self.parsed_questions)
        combined_box = self.merge_boxes([last_val, box])
        start_type, starting_chars = self.check_starting_chars(combined_box['processed_content'])
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

    def check_starting_chars(self, box_text):
        if box_text[:2] in self.numeric_starters:
            return 'numeric start', box_text[:2]
        elif box_text[:3] in self.numeric_starters:
            return 'numeric start', box_text[:3]
        elif box_text[:2] in self.letter_starters:
            return 'letter start', box_text[:2]
        else:
            return False, None

    def make_question_component(self, box, structural_id):
        question_id = 'Q_' + str(self.current_question_number)
        self.parsed_questions[question_id] = OrderedDict()
        # order of property fields is important for get last values
        property_fields = [["question_id", question_id],
                           ["ask",   QuestionTypeParser.clean_box(box)]]
        for field in property_fields:
            self.parsed_questions[question_id][field[0]] = field[1]
        self.last_added_depth = 2

    def make_answer_choice(self, box, structural_id):
        choice_id = 'answer_choice ' + structural_id
        question_id = 'Q_' + str(self.current_question_number)
        if 'answer_choices' not in self.parsed_questions[question_id].keys():
            self.parsed_questions[question_id]['answer_choices'] = OrderedDict()
        self.parsed_questions[question_id]['answer_choices'][choice_id] = QuestionTypeParser.clean_box(box)
        self.last_added_depth = 3

    def make_correct_answer(self, box, structural_id):
        question_id = 'Q_' + str(self.current_question_number)
        if 'correct_answer' not in self.parsed_questions[question_id].keys():
            self.parsed_questions[question_id]['correct_answer'] = {}
            self.parsed_questions[question_id]['correct_answer']['structural_id'] = structural_id
            self.parsed_questions[question_id]['correct_answer']['processed_content'] = box['processed_content']
        else:
            self.parsed_questions[question_id]['correct_answer']['processed_content'] += '' + box['processed_content']
        self.last_added_depth = 2

    def scan_boxes(self, text_boxes):
        for idx, box in enumerate(text_boxes):
            box_text = box['processed_content']
            start_type, starting_chars = self.check_starting_chars(box_text)
            box['structural_id'] = starting_chars
            if start_type == 'numeric start':
                self.current_question_number += 1
                self.make_question_component(box, starting_chars)
            if start_type in ['letter dot start', 'letter start']:
                self.make_answer_choice(box, starting_chars)
            if len(box_text) > 2 and not box['correct'] and not start_type:
                self.append_box_to_last_element(box)
            if box['correct']:
                last_start_type, last_starter = self.check_starting_chars(self.get_last_added(self.parsed_questions)['processed_content'])
                if last_start_type != 'letter start' or last_starter == 'd)':
                    self.make_correct_answer(box, starting_chars)


class CK12QuizParser(object):

    def __init__(self):
        self.q_parser = None
        self.parsed_content = {
            'title': '',
            'question_components': []
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
        doc = pdf.Document(file_path)
        for page in doc:
            self.extract_page_text(page, page_n)
            page_n += 1
        sorted_boxes = sorted(self.parsed_content['question_components'],
                              key=lambda x: (x['rectangle'][1], x['rectangle'][0]))
        self.q_parser.scan_boxes(sorted_boxes)
        self.parsed_content['question_components'] = self.q_parser.parsed_questions
        return self.parsed_content

    def extract_page_text(self, page, page_n):
        title_text = ''
        for flow in page:
            for block in flow:
                for line in block:
                    line_props = {
                        'raw_content': line.text,
                        'processed_content': line.text.lower().strip().replace('\t', ' ').encode('ascii', 'ignore'),
                        'rectangle': list(line.bbox.as_tuple()),
                        'font_size': list(line.char_fonts)[0].size,
                        'color': max(list(line.char_fonts)[0].color.as_tuple(), list(line.char_fonts)[-1].color.as_tuple()),
                        'correct': False
                    }
                    line_props['rectangle'][1] += self.page_dim * page_n
                    line_props['rectangle'][3] += self.page_dim * page_n
                    if self.check_color(line_props) == 'title_color':
                        title_line_text = line_props['processed_content']

                        for sw in self.stop_words['titles']:
                            title_line_text = title_line_text.replace(sw, '')
                        title_text += title_line_text
                    else:
                        if self.check_color(line_props) == 'red_answer':
                            line_props['correct'] = True
                        self.parsed_content['question_components'].append(line_props)
        self.parsed_content['title'] += title_text.strip().encode('ascii', 'ignore')

    def classify_question(self, parsed_question):
        q_type = 'None'
        if 'true or false' in parsed_question['ask']['processed_content']:
            q_type = 'True/False'
        if '____' in parsed_question['ask']['processed_content'] and q_type == 'None':
            q_type = 'Fill-in-the-Blank'
        if parsed_question['ask'] and 'answer_choices' not in parsed_question.keys() and q_type == 'None':
            q_type = 'Short Answer'
        if 'answer_choices' in parsed_question.keys() and len(parsed_question['answer_choices']) == 4:
            q_type = 'Multiple Choice'
        if 'answer_choices' in parsed_question.keys() and len(parsed_question['answer_choices']) == 2:
            q_type = 'True/False'
        return q_type

    @classmethod
    def remove_structural_ids(cls, question):
        q_components = [question['ask']] + [question['correct_answer']]
        pck = 'processed_content'
        sik = 'structural_id'
        for component in q_components:
            if component and component != '_MISSING_' and component[sik]:
                component[pck] = component[pck].replace(component[sik], '').strip()
                if 'rectangle' in component.keys():
                    del component['rectangle']
                    del component['correct']
        if 'answer_choices' in question.keys():
            for component in question['answer_choices'].values():
                component[pck] = component[pck].replace(component[sik], '').strip()
                if 'rectangle' in component.keys():
                    del component['rectangle']
                    del component['correct']

    def refine_parsed_page(self, parsed_page):
        for qid, question in parsed_page['question_components'].items():
            question['question_type'] = self.classify_question(question)

            if 'correct_answer' not in question.keys() and question['question_type'] in 'Multiple Choice':
                question['correct_answer'] = {}
                for ac_id, answer_choice in question['answer_choices'].items():
                    if answer_choice['correct']:
                        question['correct_answer']['structural_id'] = answer_choice['structural_id']
                        question['correct_answer']['processed_content'] = answer_choice['processed_content']
            if 'correct_answer' not in question.keys():
                question['correct_answer'] = '_MISSING_'
            if 'answer_choices' not in question.keys() and question['question_type'] == 'True/False':
                question['answer_choices'] = {
                    'answer_choice a': {
                        'processed_content': 'true',
                        'structural_id': 'a)'},
                    'answer_choice b': {
                        'processed_content': 'false',
                        'structural_id': 'b)'}
                }
            CK12QuizParser.remove_structural_ids(question)


def parse_pdf_collection(pdf_dir):
    quiz_content = {}
    for pdf_file in glob.glob(pdf_dir + '/*'):
        quiz_parser = CK12QuizParser()
        try:
            parsed_quiz = quiz_parser.parse_pdf(pdf_file)
            quiz_content[parsed_quiz['title']] = parsed_quiz
        except (IndexError, KeyError) as e:
            print pdf_file
    return quiz_content


def refine_parsed_quizzes(parsed_quizzes):
    quiz_parser = CK12QuizParser()
    for quiz in parsed_quizzes.values():
        quiz_parser.refine_parsed_page(quiz)


def simple_quiz_parser_test(parsed_quizzes):
    for quiz_n, quiz in parsed_quizzes.items():
        for qid, quest in quiz['question_components'].items():
            if quest['question_type'] == 'Multiple Choice':
                if len(quest['answer_choices']) != 4:
                    print quiz_n + ' mc error'
            if quest['question_type'] == 'True/False':
                if len(quest['answer_choices']) != 2:
                    print quiz_n + ' tf error'
            if quest['question_type'] in ['Short Answer', 'Fill-in-the-Blank']:
                if 'answer_choices' in quest.keys():
                    print quiz_n + ' sa or fib error'
