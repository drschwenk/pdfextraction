import json
import string
import re
from collections import defaultdict
from copy import deepcopy
import pprint


class QuestionTypeParser(object):
    def __init__(self):
        self.numeric_starters = [str(n) + '.' for n in range(20)]
        self.letter_starters = [char + '.' for char in string.ascii_uppercase[:6]]
        self.letter_starters += [char + '.' for char in string.ascii_lowercase[:6]]
        self.letter_dot_starters = [char + '.' for char in string.ascii_uppercase[:6]]
        self.parsed_questions = {}

    @staticmethod
    def get_type_specific_parser(question_type):
        if question_type == 'Multiple Choice':
            return MultipleChoiceParser()
        elif question_type == 'Short Answer':
            return ShortAnswerParser()
        elif question_type == 'True/False':
            return TrueFalseParser()
        elif question_type == 'Fill-In-the-Blank':
            return FillInBlankParser()

    @staticmethod
    def make_instruction_component(parsed_questions, inst_id, box):
        parsed_questions['instructions'] = {
            "instruction": {'I' + str(inst_id): box},
        }

    @staticmethod
    def make_question_component(box, ask_index, structural_id, question_id, parsed_questions, box_category):
        box_text = box['contents']
        question_id[0] = 'full_Q_' + structural_id
        parsed_questions[question_id[0]] = {
            "question_id": question_id[0],
            "category": box_category,
            "structural_id": structural_id,
            "asks": {'Qc' + str(ask_index): box},
            "answer_choices": {},
        }

    def make_answer_choice(self):
        pass

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
            return False


class MultipleChoiceParser(QuestionTypeParser):
    def __init__(self):
        super(MultipleChoiceParser, self).__init__()
        self.parsed_mc_questions = defaultdict(dict)

    @staticmethod
    def amplify_mc_answer_starters(box):
        box_text = box['contents'].replace('(', '').replace(')', '').replace('O', '')
        return box_text

    def scan_mc_boxes(self, mc_boxes):
        current_question_id = [0]
        ask_index = 0
        self.make_instruction_component(self.parsed_questions, mc_boxes[0])
        for box in mc_boxes[1:]:
            box_text = self.amplify_mc_answer_starters(['contents'])


class TrueFalseParser(QuestionTypeParser):
    def __init__(self):
        super(self).__init__()


class FillInBlankParser(QuestionTypeParser):
    def __init__(self):
        super(self).__init__()


class ShortAnswerParser(QuestionTypeParser):
    def __init__(self):
        super(self).__init__()


class QuestionGroupsByPage(object):

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
            print inferior_indent
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
    def group_questions_by_type(cls, all_page_boxes):
        question_types = ['Multiple Choice', 'Short Answer', 'True/False', 'Fill-In-the-Blank']
        ordered_questions = sorted(all_page_boxes['question'].values(),
                                   key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
        ordered_qs_feat = [QuestionGroupsByPage.make_box_row(box, idx) for idx, box in enumerate(ordered_questions)]
        # assigned_groups = QuestionGroupsByPage.assign_group_numbers(ordered_qs_feat)

        questions_by_type = {qt: [box for box in ordered_questions if box['category'] == qt] for qt in question_types}

        return
