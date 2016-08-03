import json
import string
import re
from collections import defaultdict
from collections import OrderedDict
from copy import deepcopy
import functools
import pprint


class QuestionTypeParser(object):
    def __init__(self, overlap_tol, blank_threshold):
        self.numeric_starters = [str(n) + '.' for n in range(20)]
        self.letter_starters = [char + '.' for char in string.ascii_uppercase[:6]]
        self.letter_starters += [char + '.' for char in string.ascii_lowercase[:6]]
        self.letter_dot_starters = [char + '.' for char in string.ascii_uppercase[:6]]
        self.current_question_number = 0
        self.parsed_questions = OrderedDict()
        self.overlap_tol = overlap_tol
        self.blank_thresh = blank_threshold
        self.blank_signifier = ' __BLANK__ '

    def get_type_specific_parser(self, question_type):
        if question_type == 'Multiple Choice':
            return MultipleChoiceParser()
        elif question_type == 'Short Answer':
            return ShortAnswerParser()
        elif question_type == 'True/False':
            return TrueFalseParser(self.overlap_tol, self.blank_thresh)
        elif question_type == 'Fill-In-the-Blank':
            return FillInBlankParser()

    @classmethod
    def clean_box(cls, box):
        box_copy = deepcopy(box)
        del box_copy['source']
        del box_copy['score']
        del box_copy['v_dim']
        del box_copy['category']
        del box_copy['group_n']
        return box_copy

    @classmethod
    def get_last_added(cls, ordered_prop_dict, depth):
        return functools.reduce(lambda x, _: list(x.items())[-1][1], range(depth), ordered_prop_dict)

    def merge_boxes(self, sorted_box_groups):
        min_x = min(map(lambda x: QuestionTypeParser.start_x(x), sorted_box_groups))
        max_x = max(map(lambda x: QuestionTypeParser.end_x(x), sorted_box_groups))
        min_y = min(map(lambda x: QuestionTypeParser.start_y(x), sorted_box_groups))
        max_y = max(map(lambda x: QuestionTypeParser.end_y(x), sorted_box_groups))
        combined_box_id = '+'.join(map(lambda x: x['box_id'], sorted_box_groups))
        combined_words = self.blank_signifier.join(map(lambda x: x['contents'], sorted_box_groups))
        combined_rect = [[min_x, min_y], [max_x, max_y]]
        new_box = {
            'contents': combined_words,
            'box_id': combined_box_id,
            'rectangle': combined_rect}
        return new_box

    def make_instruction_component(self, inst_id, box):
        self.parsed_questions['instructions'] = {
            "instruction": {'I' + str(inst_id): QuestionTypeParser.clean_box(box)},
        }

    def make_question_component(self, box, ask_index, structural_id):
        box_category = box['category']
        question_id = 'Q_' + str(self.current_question_number)
        self.parsed_questions[question_id] = OrderedDict()
        property_fields = [["question_id", question_id],
                           ["category", box_category],
                           ["structural_id", structural_id],
                           ["asks", OrderedDict({'question_line_' + str(ask_index):  QuestionTypeParser.clean_box(box)})]]
        for field in property_fields:
            self.parsed_questions[question_id][field[0]] = field[1]

    def scan_over_boxes(self, ordered_boxes):
        pass

    def check_starting_chars(self, box_text):
        if box_text[:2] in self.numeric_starters:
            return 'numeric start', box_text[:2]
        elif box_text[:3] in self.numeric_starters:
            return 'numeric start', box_text[:3]
        elif box_text[:2] in self.letter_starters:
            return 'letter start', box_text[:2]
        elif box_text[:2] in self.letter_dot_starters:
            return 'letter dot start', box_text[:2]
        else:
            return None, None

    def append_box_to_last_element(self, box):
        last_val = QuestionTypeParser.get_last_added(self.parsed_questions, 3)
        last_key, _ = self.parsed_questions.popitem()
        combined_box = self.merge_boxes([last_val, box])
        # print(last_val)
        # print(box)
        # print(combined_box)
        # print('')
        self.parsed_questions[last_key] = combined_box

    @classmethod
    def start_x(cls, box):
        return box['rectangle'][0][0]

    @classmethod
    def start_y(cls, box):
        return box['rectangle'][0][1]

    @classmethod
    def end_x(cls, box):
        return box['rectangle'][1][0]

    @classmethod
    def end_y(cls, box):
        return box['rectangle'][1][1]

    @classmethod
    def height(cls, box):
        return QuestionTypeParser.end_y(box) - QuestionTypeParser.start_y(box)

    @classmethod
    def width(cls, box):
        return QuestionTypeParser.end_x(box) - QuestionTypeParser.start_x(box)

    def check_for_same_line(self, current_box, last_box_seen):
        boxes_y_coords = [[QuestionTypeParser.start_y(current_box), QuestionTypeParser.end_y(current_box)],
                          [QuestionTypeParser.start_y(last_box_seen), QuestionTypeParser.end_y(last_box_seen)]]
        ordered_boxes = sorted(boxes_y_coords)
        overlap = max(0, min(ordered_boxes[0][1], ordered_boxes[1][1]) - max(ordered_boxes[0][0], ordered_boxes[1][0]))
        larger_box_width = max(QuestionTypeParser.height(current_box), QuestionTypeParser.height(last_box_seen))
        return overlap / float(larger_box_width) > self.overlap_tol

    def detect_blank(self, current_box, parsed_questions):
        last_box_seen = list(QuestionTypeParser.get_last_added(parsed_questions, 2).values())[0]
        large_gap = (QuestionTypeParser.start_x(current_box) - QuestionTypeParser.end_x(last_box_seen)) > self.blank_thresh
        same_line = self.check_for_same_line(current_box, last_box_seen)
        return same_line and large_gap


class MultipleChoiceParser(QuestionTypeParser):
    def __init__(self):
        super(MultipleChoiceParser, self).__init__()
        self.q_sub_n = 0

    @staticmethod
    def amplify_mc_answer_starters(box):
        box_text = box['contents'].replace('(', '').replace(')', '').replace('O', '')
        return box_text

    def make_answer_choice(self, box, structural_id):
        choice_id = 'answer_choice ' + structural_id
        question_id = 'Q_' + str(self.current_question_number)
        if 'answer_choices' not in self.parsed_questions[question_id].keys():
            self.parsed_questions[question_id]['answer_choices'] = OrderedDict()
        self.parsed_questions[question_id]["answer_choices"][choice_id] = {
            "structural_label": choice_id,
            "possible_answer": QuestionTypeParser.clean_box(box)
        }
        return

    def scan_boxes(self, mc_boxes):
        ask_index = 0
        for idx, box in enumerate(mc_boxes):
            box_text = self.amplify_mc_answer_starters(box)
            start_type, starting_chars = self.check_starting_chars(box_text)
            if not self.q_sub_n and not start_type:
                self.make_instruction_component(idx, box)
            elif start_type == 'numeric start':
                self.q_sub_n += 1
                self.current_question_number += 1
                self.make_question_component(box, ask_index, starting_chars)
            elif start_type in ['letter dot start', 'letter start']:
                self.make_answer_choice(box, starting_chars)
            elif start_type == 'letter start':
                pass


class TrueFalseParser(QuestionTypeParser):

    def __init__(self, overlap_tol, blank_threshold):
        super(TrueFalseParser, self).__init__(overlap_tol, blank_threshold)
        self.q_sub_n = 0

    def scan_boxes(self, mc_boxes):
        ask_index = 0
        for idx, box in enumerate(mc_boxes):
            box_text = box['contents']
            start_type, starting_chars = self.check_starting_chars(box_text)
            if not self.q_sub_n and not start_type:
                self.make_instruction_component(idx, box)
            elif start_type == 'numeric start':
                self.q_sub_n += 1
                self.current_question_number += 1
                self.make_question_component(box, ask_index, starting_chars)
            elif self.detect_blank(box, self.parsed_questions):
                self.append_box_to_last_element(QuestionTypeParser.clean_box(box))
            elif start_type == 'letter start':
                pass


class FillInBlankParser(QuestionTypeParser):
    def __init__(self):
        super(self).__init__()

    def __init__(self):
        super(FillInBlankParser, self).__init__()

        self.q_sub_n = 0

    def scan_boxes(self, mc_boxes):
        ask_index = 0
        for idx, box in enumerate(mc_boxes):
            box_text = box['contents']
            start_type, starting_chars = self.check_starting_chars(box_text)
            if not self.q_sub_n and not start_type:
                self.make_instruction_component(idx, box)
            elif start_type == 'numeric start':
                self.q_sub_n += 1
                self.current_question_number += 1
                self.make_question_component(box, ask_index, starting_chars)
            elif start_type == 'letter start':
                pass


class ShortAnswerParser(QuestionTypeParser):
    def __init__(self):
        super(ShortAnswerParser, self).__init__()
        self.q_sub_n = 0

    def scan_boxes(self, mc_boxes):
        ask_index = 0
        for idx, box in enumerate(mc_boxes):
            box_text = box['contents']
            start_type, starting_chars = self.check_starting_chars(box_text)
            if not self.q_sub_n and not start_type:
                self.make_instruction_component(idx, box)
            elif start_type == 'numeric start':
                self.q_sub_n += 1
                self.current_question_number += 1
                self.make_question_component(box, ask_index, starting_chars)
            elif start_type == 'letter start':
                pass


class PageQuestionParser(object):

    def __init__(self):
        pass

    @classmethod
    def assign_group_numbers(cls, ordered_question_boxes):
        current_group_n = 0
        current_outer_indent = ordered_question_boxes[0]['start_x']
        last_seen_question_type = 'Unlabeled'
        indent_tolerance = 20
        separation_tolerance = 60
        last_box_end_y = 0
        for box in ordered_question_boxes:
            if box['category'] == 'Question' or box['category'] == 'Unlabeled':
                box['predicted_group_n'] = 0
                last_seen_question_type = box['category']
                last_box_end_y = box['end_y']
                continue

            type_changed = last_seen_question_type != box['category']
            vertically_separated = abs(int(box['start_y']) - int(last_box_end_y)) > separation_tolerance
            inferior_indent = (box['start_x'] - current_outer_indent) > indent_tolerance
            if (vertically_separated and not inferior_indent) or type_changed:
                current_group_n += 1
                current_outer_indent = box['start_x']

            last_seen_question_type = box['category']
            box['group_n'] = current_group_n
            last_box_end_y = box['end_y']

        return ordered_question_boxes

    @classmethod
    def make_box_row(cls, row_dict, pos_idx):
        new_row = row_dict.copy()
        rect = row_dict['rectangle']
        new_row['start_x'] = rect[0][0]
        new_row['start_y'] = rect[0][1]
        new_row['end_x'] = rect[1][0]
        new_row['end_y'] = rect[1][1]
        new_row['vertical_order'] = pos_idx
        del new_row['rectangle']
        return new_row

    @classmethod
    def fuzzy_sort(cls, all_page_boxes, fuzzy_tolerance):
        regular_sorted_boxes = sorted(all_page_boxes['question'].values(),
                                      key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
        fuzzy_sorted_group = deepcopy(regular_sorted_boxes)
        for idx in range(1, len(fuzzy_sorted_group)):
            if fuzzy_sorted_group[idx - 1]['rectangle'][0][1] + fuzzy_tolerance > \
                    fuzzy_sorted_group[idx]['rectangle'][0][1]:
                fuzzy_sorted_group[idx - 1], fuzzy_sorted_group[idx] = fuzzy_sorted_group[idx], fuzzy_sorted_group[
                    idx - 1]
        return fuzzy_sorted_group

    @classmethod
    def parse_page_questions(cls, all_page_boxes, overlap_tol, blank_threshold):
        question_types = ['Multiple Choice', 'Short Answer', 'True/False', 'Fill-In-the-Blank']
        ordered_questions = sorted(all_page_boxes['question'].values(),
                                   key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
        ordered_questions = PageQuestionParser.fuzzy_sort(all_page_boxes, 10)
        # pprint.pprint(ordered_questions)
        questions_by_type = {qt: [box for box in ordered_questions if box['category'] == qt] for qt in question_types[2:3]}

        master_page_parser = QuestionTypeParser(overlap_tol, blank_threshold)
        for q_type, question_boxes in questions_by_type.items():
            type_specific_parser = master_page_parser.get_type_specific_parser(q_type)
            type_specific_parser.scan_boxes(question_boxes)
            master_page_parser.parsed_questions[q_type] = type_specific_parser.parsed_questions
        return master_page_parser.parsed_questions
