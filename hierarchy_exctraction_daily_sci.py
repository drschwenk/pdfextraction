import json
import string
import re
from collections import defaultdict
from copy import deepcopy
import pprint


def print_contents(box):
    print ''
    print 'actual ' + box['group_n']
    print 'predicted ' + str(box['predicted_group_n'])
    print box['contents']
    print ''


def make_box_row(row_dict, pos_idx):
    new_row = row_dict.copy()
    rect = row_dict['rectangle']
    new_row['start_x'] = rect[0][0]
    new_row['start_y'] = rect[0][1]
    new_row['end_x'] = rect[1][0]
    new_row['end_y'] = rect[1][1]
    new_row['vert_order'] = pos_idx
    del new_row['rectangle']
    return new_row

### Start old


def write_predicted_groups(page_results, base_path, test_path):
    page = page_results[0]
    predicted_boxes = page_results[-1]
    page_file_path = base_path + page.replace('jpeg', 'json')
    new_file_path = test_path + page.replace('jpeg', 'json')

    with open(page_file_path) as f:
        all_page_boxes = json.load(f)

    for box in predicted_boxes:
        all_page_boxes['question'][box['box_id']]['group_n'] = box['predicted_group_n']

    with open(new_file_path, 'w') as f:
        json.dump(all_page_boxes, f)


def assign_group_numbers_wo_labeled_qs(ordered_question_boxes):
    current_group_n = 0
    current_outer_indent = ordered_question_boxes[0]['start_x']
    last_seen_question_type = 'Unlabeled'
    indent_tolerance = 20
    separation_tolerance = 20
    last_box_end_y = 0

    for idx, box in enumerate(ordered_question_boxes):
        if box['category'] == 'Unlabeled': #or box['category'] == 'Question':
            box['predicted_group_n'] = 0
            last_seen_question_type = box['category']
            last_box_end_y = box['end_y']
            continue
        #             return 0

        type_changed = last_seen_question_type != box['category']
        last_seen_question_type = box['category'] if type_changed else last_seen_question_type
        vertically_separated = int(box['start_y']) - int(last_box_end_y) > separation_tolerance
        #         print box['start_y']
        #         print last_box_end_y
        last_box_end_y = box['end_y']
        #         print 'vs ' + str(vertically_seperated)
        #         print 'tc ' + str(type_changed)

        if vertically_separated and (type_changed or box['start_x'] - indent_tolerance < current_outer_indent ):
            current_group_n += 1

        box['predicted_group_n'] = current_group_n
    return ordered_question_boxes


def assign_group_numbers(ordered_question_boxes):
    current_group_n = 0
    current_outer_indent = ordered_question_boxes[0]['start_x']
    last_seen_question_type = 'Unlabeled'
    indent_tolerance = 20
    separation_tolerance = 20
    last_box_end_y = 0
    
    for idx, box in enumerate(ordered_question_boxes):
        if box['category'] == 'Question' or box['category'] == 'Unlabeled':
            box['predicted_group_n'] = 0
            last_seen_question_type = box['category']
            last_box_end_y = box['end_y']
            continue
#             return 0
        
        type_changed = last_seen_question_type != box['category']
        last_seen_question_type = box['category'] if type_changed else last_seen_question_type
        vertically_separated = int(box['start_y']) - int(last_box_end_y) > separation_tolerance
#         print box['start_y']
#         print last_box_end_y
        last_box_end_y = box['end_y']
#         print 'vs ' + str(vertically_seperated)
#         print 'tc ' + str(type_changed)

        if vertically_separated and (type_changed or box['start_x'] - indent_tolerance < current_outer_indent ):
            current_group_n += 1
            
        box['predicted_group_n'] = current_group_n
    return ordered_question_boxes


def check_group_numbers(ordered_boxes_w_pred):
    n_wrong = 0 
    for box in ordered_boxes_w_pred:
        if int(box['group_n']) != box['predicted_group_n']:
            n_wrong += 1
    return n_wrong, len(ordered_boxes_w_pred), 1 - n_wrong / float(len(ordered_boxes_w_pred))


def predict_groups(pages, base_path):
    total_num_boxes = 0
    for page in pages:
        page_file_path = base_path + page.replace('jpeg', 'json')
        with open(page_file_path) as f:
            page_boxes = json.load(f)

        for qn, qv in page_boxes['question'].items():
            total_num_boxes += 1
            del qv['source']
            del qv['score']
            del qv['v_dim']

        q_series = page_boxes['question']
        vertically_ordered_question = sorted(q_series.values(), key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
        vertically_ordered_question_feat = [make_box_row(box, idx) for idx, box in enumerate(vertically_ordered_question)]
        boxes_w_predicts = assign_group_numbers(vertically_ordered_question_feat)
    return boxes_w_predicts


def predict_and_verify_groups(pages, base_path):
    results_by_page = []
    total_num_boxes = 0
    for page in pages:
        page_file_path = base_path + page.replace('jpeg', 'json')
        with open(page_file_path) as f:
            page_boxes = json.load(f)

        for qn, qv in page_boxes['question'].items():
            total_num_boxes += 1
            del qv['source']
            del qv['score']
            del qv['v_dim']

        q_series = page_boxes['question']
        vertically_ordered_question = sorted(q_series.values(), key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
        vertically_ordered_question_feat = [make_box_row(box, idx) for idx, box in enumerate(vertically_ordered_question)]
        boxes_w_predicts = assign_group_numbers(vertically_ordered_question_feat)
        if boxes_w_predicts:
            n_wrong, box_n_this_page, fraction_right = check_group_numbers(boxes_w_predicts)
            total_num_boxes += box_n_this_page
            if fraction_right:
                results_by_page.append((page, n_wrong, fraction_right, boxes_w_predicts))

    total_wrong = sum([res[1] for res in results_by_page])
    overall_accuracy = 1 - total_wrong / float(total_num_boxes)
    return overall_accuracy, total_wrong, total_num_boxes, results_by_page


def label_multi_choice_components(base_path, pages):
    results_by_page = []
    total_num_boxes = 0
    for page in pages:
        page_file_path = base_path + page.replace('jpeg', 'json')
        with open(page_file_path) as f:
            page_boxes = json.load(f)

        for qn, qv in page_boxes['question'].items():
            total_num_boxes += 1

        q_series = page_boxes['question']
        vertically_ordered_question = sorted(q_series.values(), key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
        vertically_ordered_question_feat = [make_box_row(box, idx) for idx, box in enumerate(vertically_ordered_question)]
        boxes_w_predicts = assign_group_numbers(vertically_ordered_question_feat)
        if boxes_w_predicts:
            n_wrong, box_n_this_page, fraction_right = check_group_numbers(boxes_w_predicts)
            total_num_boxes += box_n_this_page
            if fraction_right:
                results_by_page.append((page, n_wrong, fraction_right, boxes_w_predicts))

    total_wrong = sum([res[1] for res in results_by_page])
    overall_accuracy = 1 - total_wrong / float(total_num_boxes)
    return overall_accuracy, total_wrong, total_num_boxes, results_by_page


# def parse_tf_questions(question_group):
#
#     def make_possible_answer_entry(structural_label, complete_questions, qv):
#         last_type_seen[0] = 'possible_answer'
#         choice_id = "answer_choice_" + structural_label
#         complete_questions[current_group_n][current_question_number[0]]['answer_choices'][choice_id] = {
#             "structural_label": structural_label,
#             "possible_answer": qv
#         }
#
#     def make_question_entry(ask_index, complete_questions, qv, structural_label):
#         last_type_seen[0] = 'question'
#         box_text = qv['contents']
#         current_question_number[0] = 'full_Q_' + structural_label
#         complete_questions[current_group_n][current_question_number[0]] = {
#             "question_id": current_question_number[0],
#             "category": box_category,
#             "structural_id": structural_label,
#             "asks": {'Qc' + str(ask_index): qv},
#             "answer_choices": {},
#         }
#
#     def make_instructions_entry(instuctions, inst_id):
#         instructions[current_group_n] = {
#             "instruction": {'I' + str(inst_id): qv},
#         }
#
#     numeric_starters = [str(n) + '.' for n in range(10)]
#     letter_starters = [char for char in string.ascii_uppercase[:6]]
#     letter_punct_starters = [char + '.' for char in string.ascii_uppercase[:6]]
#
#     mc_option_pattern = re.compile('([A-Z])(?:[a-z]?){1}\s')
#
#     complete_questions = defaultdict(dict)
#     instructions = defaultdict(dict)
#
#     q_series = question_group
#     vertically_ordered_question = sorted(q_series.values(),
#                                          key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
#     last_type_seen = [0]
#     misfits_created = False
#     current_question_number = [0]
#     ask_index = 0
#     unlabeled_choice_idx = 1
#     current_group_n = 0
#     instructions_idx = 0
#     for qv in vertically_ordered_question:
#         current_group_n = 'G' + str(qv['group_n'])
#         box_category = qv['category']
#         box_text = qv['contents'].replace('(', '').replace(')', '').replace('O', '')
#         del qv['source']
#         del qv['score']
#         del qv['v_dim']
#         del qv['category']
#
#         if box_text[:2] in letter_punct_starters:
#             instructions_idx += 1
#             make_instructions_entry(instructions, instructions_idx)
#
#         elif box_text[:2] in numeric_starters:
#             last_question_structural_id = box_text[:2]
#             ask_index += 1
#             make_question_entry(ask_index, complete_questions, qv, last_question_structural_id)
#
#         elif re.findall(mc_option_pattern, box_text) and re.findall(mc_option_pattern, box_text)[0] in letter_starters:
#             structural_label = re.findall(mc_option_pattern, box_text)[0]
#             make_possible_answer_entry(structural_label, complete_questions, qv)
#         elif box_text[-1] in letter_starters:
#             structural_label = box_text[-1]
#             make_possible_answer_entry(structural_label, complete_questions, qv)
#
#         elif current_question_number:
#             if last_type_seen[0] == 'possible_answer':
#                 structural_label = 'Z' + str(unlabeled_choice_idx)
#                 unlabeled_choice_idx += 1
#                 make_possible_answer_entry(structural_label, complete_questions, qv)
#             elif last_type_seen[0] == 'question':
#                 ask_index += 1
#                 complete_questions[current_group_n][current_question_number[0]]['asks']['Qc' + str(ask_index)] = qv
#         else:
#             if not misfits_created:
#                 complete_questions[current_group_n]['misfits'] = {
#                 }
#                 complete_questions[current_group_n]['misfits'][qv['box_id']] = {
#                     "category": box_category,
#                     "asks": {'M' + str(ask_index): qv},
#                     "answer_choices": {}
#                 }
#                 misfits_created = True
#             elif misfits_created:
#                 complete_questions[current_group_n]['misfits'][qv['box_id']] = {
#                     "category": box_category,
#                     "asks": {'M' + str(ask_index): qv},
#                     "answer_choices": {}
#                 }
#             else:
#                 pass
#                 print 'miss'
#                 print box_text
#                 print
#
#     return complete_questions, instructions


# def parse_fib_questions(question_group):
#
#     def make_possible_answer_entry(structural_label, complete_questions, qv):
#         last_type_seen[0] = 'possible_answer'
#         choice_id = "answer_choice_" + structural_label
#         complete_questions[current_group_n][current_question_number[0]]['answer_choices'][choice_id] = {
#             "structural_label": structural_label,
#             "possible_answer": qv
#         }
#
#     def make_question_entry(ask_index, complete_questions, qv, structural_label):
#         last_type_seen[0] = 'question'
#         box_text = qv['contents']
#         current_question_number[0] = 'full_Q_' + structural_label
#         complete_questions[current_group_n][current_question_number[0]] = {
#             "question_id": current_question_number[0],
#             "category": box_category,
#             "structural_id": structural_label,
#             "asks": {'Qc' + str(ask_index): qv},
#             "answer_choices": {},
#         }
#
#     def make_instructions_entry(instuctions, inst_id):
#         instructions[current_group_n] = {
#             "instruction": {'I' + str(inst_id): qv},
#         }
#
#     numeric_starters = [str(n) + '.' for n in range(10)]
#     letter_starters = [char for char in string.ascii_uppercase[:6]]
#     letter_punct_starters = [char + '.' for char in string.ascii_uppercase[:6]]
#
#     mc_option_pattern = re.compile('([A-Z])(?:[a-z]?){1}\s')
#
#     complete_questions = defaultdict(dict)
#     instructions = defaultdict(dict)
#
#     q_series = question_group
#     vertically_ordered_question = sorted(q_series.values(),
#                                          key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
#     last_type_seen = [0]
#     misfits_created = False
#     current_question_number = [0]
#     ask_index = 0
#     unlabeled_choice_idx = 1
#     current_group_n = 0
#     instructions_idx = 0
#     for qv in vertically_ordered_question:
#         current_group_n = 'G' + str(qv['group_n'])
#         box_category = qv['category']
#         box_text = qv['contents'].replace('(', '').replace(')', '').replace('O', '')
#         del qv['source']
#         del qv['score']
#         del qv['v_dim']
#         del qv['category']
#
#         if box_text[:2] in letter_punct_starters:
#             instructions_idx += 1
#             make_instructions_entry(instructions, instructions_idx)
#
#         elif box_text[:2] in numeric_starters:
#             last_question_structural_id = box_text[:2]
#             ask_index += 1
#             make_question_entry(ask_index, complete_questions, qv, last_question_structural_id)
#
#         elif re.findall(mc_option_pattern, box_text) and re.findall(mc_option_pattern, box_text)[0] in letter_starters:
#             structural_label = re.findall(mc_option_pattern, box_text)[0]
#             make_possible_answer_entry(structural_label, complete_questions, qv)
#         elif box_text[-1] in letter_starters:
#             structural_label = box_text[-1]
#             make_possible_answer_entry(structural_label, complete_questions, qv)
#
#         elif current_question_number:
#             if last_type_seen[0] == 'possible_answer':
#                 structural_label = 'Z' + str(unlabeled_choice_idx)
#                 unlabeled_choice_idx += 1
#                 make_possible_answer_entry(structural_label, complete_questions, qv)
#             elif last_type_seen[0] == 'question':
#                 ask_index += 1
#                 complete_questions[current_group_n][current_question_number[0]]['asks']['Qc' + str(ask_index)] = qv
#         else:
#             if not misfits_created:
#                 complete_questions[current_group_n]['misfits'] = {
#                 }
#                 complete_questions[current_group_n]['misfits'][qv['box_id']] = {
#                     "category": box_category,
#                     "asks": {'M' + str(ask_index): qv},
#                     "answer_choices": {}
#                 }
#                 misfits_created = True
#             elif misfits_created:
#                 complete_questions[current_group_n]['misfits'][qv['box_id']] = {
#                     "category": box_category,
#                     "asks": {'M' + str(ask_index): qv},
#                     "answer_choices": {}
#                 }
#             else:
#                 pass
#                 print 'miss'
#                 print box_text
#                 print
#
#     return complete_questions, instructions
### End old


def parse_tf_questions(question_group, first_pass=True):

    def make_possible_answer_entry(structural_label, complete_questions, qv):
        last_type_seen[0] = 'possible_answer'
        choice_id = "answer_choice_" + structural_label
        complete_questions[current_group_n][current_question_id[0]]['answer_choices'][choice_id] = {
            "structural_label": structural_label,
            "possible_answer": qv
        }

    def make_question_entry(ask_index, complete_questions, qv, structural_label):
        last_type_seen[0] = 'question'
        box_text = qv['contents']
        current_question_id[0] = 'full_Q_' + structural_label
        complete_questions[current_group_n][current_question_id[0]] = {
            "question_id": current_question_id[0],
            "category": box_category,
            "structural_id": structural_label,
            "asks": {'Qc' + str(ask_index): qv},
            "answer_choices": {},
        }

    def make_instructions_entry(instuctions, inst_id):
        instructions[current_group_n] = {
            "instruction": {'I' + str(inst_id): qv},
        }

    numeric_starters = [str(n) + '.' for n in range(10)]
    letter_punct_starters = [char + '.' for char in string.ascii_uppercase[:6]]

    complete_questions = defaultdict(dict)
    instructions = defaultdict(dict)

    q_series = deepcopy(question_group)
    vertically_ordered_question = sorted(q_series.values(),
                                         key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
    last_type_seen = [0]
    misfits_created = False
    current_question_id = [0]
    ask_index = 0
    unlabeled_choice_idx = 1
    current_group_n = 0
    instructions_idx = 0
    for qv in vertically_ordered_question:
        current_group_n = 'G' + str(qv['group_n'])
        box_category = qv['category']
        box_text = qv['contents'].replace('(', '').replace(')', '').replace('O', '')
        del qv['source']
        del qv['score']
        del qv['v_dim']
        del qv['category']
        if box_text[:2] in letter_punct_starters:
            if first_pass:
                instructions_idx += 1
                make_instructions_entry(instructions, instructions_idx)
            else:
                last_question_structural_id = box_text[:2]
                ask_index += 1
                make_question_entry(ask_index, complete_questions, qv, last_question_structural_id)
        elif box_text[:2] in numeric_starters:
            last_question_structural_id = box_text[:2]
            ask_index += 1
            make_question_entry(ask_index, complete_questions, qv, last_question_structural_id)
        elif ask_index and not ('true' in box_text.lower() or 'false' in box_text.lower()):
            ask_index += 1
            complete_questions[current_group_n][current_question_id[0]]['asks']['Qc' + str(ask_index)] = qv
        elif not first_pass:
            if not misfits_created:
                complete_questions[current_group_n]['misfits'] = {
                }
                complete_questions[current_group_n]['misfits'][qv['box_id']] = {
                    "category": box_category,
                    "asks": {'M' + str(ask_index): qv},
                    "answer_choices": {}
                }
                misfits_created = True
            elif misfits_created:
                complete_questions[current_group_n]['misfits'][qv['box_id']] = {
                    "category": box_category,
                    "asks": {'M' + str(ask_index): qv},
                    "answer_choices": {}
                }
        elif not first_pass:
            pass
            print 'miss'
            print box_text
            print
    if not complete_questions and instructions:
        pass
        return parse_sa_questions(question_group, False)
    return complete_questions, instructions


def parse_fib_questions(question_group, first_pass=True):

    def make_possible_answer_entry(structural_label, complete_questions, qv):
        last_type_seen[0] = 'possible_answer'
        choice_id = "answer_choice_" + structural_label
        complete_questions[current_group_n][current_question_id[0]]['answer_choices'][choice_id] = {
            "structural_label": structural_label,
            "possible_answer": qv
        }

    def make_question_entry(ask_index, complete_questions, qv, structural_label):
        last_type_seen[0] = 'question'
        box_text = qv['contents']
        current_question_id[0] = 'full_Q_' + structural_label
        complete_questions[current_group_n][current_question_id[0]] = {
            "question_id": current_question_id[0],
            "category": box_category,
            "structural_id": structural_label,
            "asks": {'Qc' + str(ask_index): qv},
            "answer_choices": {},
        }

    def make_instructions_entry(instuctions, inst_id):
        instructions[current_group_n] = {
            "instruction": {'I' + str(inst_id): qv},
        }

    numeric_starters = [str(n) + '.' for n in range(10)]
    letter_punct_starters = [char + '.' for char in string.ascii_uppercase[:6]]

    complete_questions = defaultdict(dict)
    instructions = defaultdict(dict)

    q_series = deepcopy(question_group)
    vertically_ordered_question = sorted(q_series.values(),
                                         key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
    last_type_seen = [0]
    misfits_created = False
    current_question_id = [0]
    ask_index = 0
    unlabeled_choice_idx = 1
    current_group_n = 0
    instructions_idx = 0
    for qv in vertically_ordered_question:
        current_group_n = 'G' + str(qv['group_n'])
        box_category = qv['category']
        box_text = qv['contents'].replace('(', '').replace(')', '').replace('O', '')
        del qv['source']
        del qv['score']
        del qv['v_dim']
        del qv['category']
        if box_text[:2] in letter_punct_starters:
            if first_pass:
                instructions_idx += 1
                make_instructions_entry(instructions, instructions_idx)
            else:
                last_question_structural_id = box_text[:2]
                ask_index += 1
                make_question_entry(ask_index, complete_questions, qv, last_question_structural_id)

        elif box_text[:2] in numeric_starters:
            last_question_structural_id = box_text[:2]
            ask_index += 1
            make_question_entry(ask_index, complete_questions, qv, last_question_structural_id)
        elif ask_index:
            ask_index += 1
            complete_questions[current_group_n][current_question_id[0]]['asks']['Qc' + str(ask_index)] = qv
        elif not first_pass:
            if not misfits_created:
                complete_questions[current_group_n]['misfits'] = {
                }
                complete_questions[current_group_n]['misfits'][qv['box_id']] = {
                    "category": box_category,
                    "asks": {'M' + str(ask_index): qv},
                    "answer_choices": {}
                }
                misfits_created = True
            elif misfits_created:
                complete_questions[current_group_n]['misfits'][qv['box_id']] = {
                    "category": box_category,
                    "asks": {'M' + str(ask_index): qv},
                    "answer_choices": {}
                }
        elif not first_pass:
            pass
            print 'miss'
            print box_text
            print
    if not complete_questions and instructions:
        pass
        return parse_sa_questions(question_group, False)
    return complete_questions, instructions


def parse_sa_questions(question_group, first_pass=True):

    def make_possible_answer_entry(structural_label, complete_questions, qv):
        last_type_seen[0] = 'possible_answer'
        choice_id = "answer_choice_" + structural_label
        complete_questions[current_group_n][current_question_id[0]]['answer_choices'][choice_id] = {
            "structural_label": structural_label,
            "possible_answer": qv
        }

    def make_question_entry(ask_index, complete_questions, qv, structural_label):
        last_type_seen[0] = 'question'
        box_text = qv['contents']
        current_question_id[0] = 'full_Q_' + structural_label
        complete_questions[current_group_n][current_question_id[0]] = {
            "question_id": current_question_id[0],
            "category": box_category,
            "structural_id": structural_label,
            "asks": {'Qc' + str(ask_index): qv},
            "answer_choices": {},
        }

    def make_instructions_entry(instuctions, inst_id):
        instructions[current_group_n] = {
            "instruction": {'I' + str(inst_id): qv},
        }

    numeric_starters = [str(n) + '.' for n in range(10)]
    letter_punct_starters = [char + '.' for char in string.ascii_uppercase[:6]]

    complete_questions = defaultdict(dict)
    instructions = defaultdict(dict)

    q_series = deepcopy(question_group)
    vertically_ordered_question = sorted(q_series.values(),
                                         key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
    last_type_seen = [0]
    misfits_created = False
    current_question_id = [0]
    ask_index = 0
    unlabeled_choice_idx = 1
    current_group_n = 0
    instructions_idx = 0
    for qv in vertically_ordered_question:
        current_group_n = 'G' + str(qv['group_n'])
        box_category = qv['category']
        box_text = qv['contents'].replace('(', '').replace(')', '').replace('O', '')
        del qv['source']
        del qv['score']
        del qv['v_dim']
        del qv['category']
        if box_text[:2] in letter_punct_starters:
            if first_pass:
                instructions_idx += 1
                make_instructions_entry(instructions, instructions_idx)
            else:
                last_question_structural_id = box_text[:2]
                ask_index += 1
                make_question_entry(ask_index, complete_questions, qv, last_question_structural_id)

        elif box_text[:2] in numeric_starters:
            last_question_structural_id = box_text[:2]
            ask_index += 1
            make_question_entry(ask_index, complete_questions, qv, last_question_structural_id)
        elif ask_index:
            ask_index += 1
            complete_questions[current_group_n][current_question_id[0]]['asks']['Qc' + str(ask_index)] = qv
        elif not first_pass:
            if not misfits_created:
                complete_questions[current_group_n]['misfits'] = {
                }
                complete_questions[current_group_n]['misfits'][qv['box_id']] = {
                    "category": box_category,
                    "asks": {'M' + str(ask_index): qv},
                    "answer_choices": {}
                }
                misfits_created = True
            elif misfits_created:
                complete_questions[current_group_n]['misfits'][qv['box_id']] = {
                    "category": box_category,
                    "asks": {'M' + str(ask_index): qv},
                    "answer_choices": {}
                }
        elif not first_pass:
            pass
            print 'miss'
            print box_text
            print
    if not complete_questions and instructions:
        pass
        return parse_sa_questions(question_group, False)
    return complete_questions, instructions


def parse_mc_questions(question_group):

    def make_possible_answer_entry(structural_label, complete_questions, qv):
        last_type_seen[0] = 'possible_answer'
        choice_id = "answer_choice_" + structural_label
        complete_questions[current_group_n][current_question_id[0]]['answer_choices'][choice_id] = {
            "structural_label": structural_label,
            "possible_answer": qv
        }

    def make_question_entry(ask_index, complete_questions, qv, structural_label):
        last_type_seen[0] = 'question'
        box_text = qv['contents']
        current_question_id[0] = 'full_Q_' + structural_label
        complete_questions[current_group_n][current_question_id[0]] = {
            "question_id": current_question_id[0],
            "category": box_category,
            "structural_id": structural_label,
            "asks": {'Qc' + str(ask_index): qv},
            "answer_choices": {},
        }

    def make_instructions_entry(instuctions, inst_id):
        instructions[current_group_n] = {
            "instruction": {'I' + str(inst_id): qv},
        }

    numeric_starters = [str(n) + '.' for n in range(10)]
    letter_starters = [char for char in string.ascii_uppercase[:6]]
    letter_punct_starters = [char + '.' for char in string.ascii_uppercase[:6]]

    mc_option_pattern = re.compile('([A-Z])(?:[a-z]?){1}\s')

    complete_questions = defaultdict(dict)
    instructions = defaultdict(dict)

    q_series = question_group
    vertically_ordered_question = sorted(q_series.values(),
                                         key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
    last_type_seen = [0]
    misfits_created = False
    current_question_id = [0]
    ask_index = 0
    unlabeled_choice_idx = 1
    current_group_n = 0
    instructions_idx = 0
    for qv in vertically_ordered_question:
        current_group_n = 'G' + str(qv['group_n'])
        box_category = qv['category']
        box_text = qv['contents'].replace('(', '').replace(')', '').replace('O', '')
        del qv['source']
        del qv['score']
        del qv['v_dim']
        del qv['category']

        if box_text[:2] in letter_punct_starters:
            instructions_idx += 1
            make_instructions_entry(instructions, instructions_idx)

        elif box_text[:2] in numeric_starters:
            last_question_structural_id = box_text[:2]
            ask_index += 1
            make_question_entry(ask_index, complete_questions, qv, last_question_structural_id)

        elif re.findall(mc_option_pattern, box_text) and re.findall(mc_option_pattern, box_text)[0] in letter_starters:
            structural_label = re.findall(mc_option_pattern, box_text)[0]
            make_possible_answer_entry(structural_label, complete_questions, qv)
        elif box_text[-1] in letter_starters:
            structural_label = box_text[-1]
            make_possible_answer_entry(structural_label, complete_questions, qv)

        elif current_question_id:
            if last_type_seen[0] == 'possible_answer':
                structural_label = 'Z' + str(unlabeled_choice_idx)
                unlabeled_choice_idx += 1
                make_possible_answer_entry(structural_label, complete_questions, qv)
            elif last_type_seen[0] == 'question':
                ask_index += 1
                complete_questions[current_group_n][current_question_id[0]]['asks']['Qc' + str(ask_index)] = qv
        else:
            if not misfits_created:
                complete_questions[current_group_n]['misfits'] = {
                }
                complete_questions[current_group_n]['misfits'][qv['box_id']] = {
                    "category": box_category,
                    "asks": {'M' + str(ask_index): qv},
                    "answer_choices": {}
                }
                misfits_created = True
            elif misfits_created:
                complete_questions[current_group_n]['misfits'][qv['box_id']] = {
                    "category": box_category,
                    "asks": {'M' + str(ask_index): qv},
                    "answer_choices": {}
                }
            else:
                pass
                print 'miss'
                print box_text
                print

    return complete_questions, instructions


def parse_book(pages, file_path):
    for page in pages:
        page_file_path = file_path + page.replace('jpeg', 'json')
        with open(page_file_path) as f:
            page_json = json.load(f)
        parsed_pages = parse_page_questions(page_json)
    return parsed_pages


def parse_page_questions(all_question_boxes):
    all_questions = {}

    mc_questions = {qid: box for qid, box in all_question_boxes['question'].items() if
                    box['category'] == 'Multiple Choice'}
    sa_questions = {qid: box for qid, box in all_question_boxes['question'].items() if
                    box['category'] == 'Short Answer'}
    tf_questions = {qid: box for qid, box in all_question_boxes['question'].items() if
                    box['category'] == 'True/False'}
    fib_questions = {qid: box for qid, box in all_question_boxes['question'].items() if
                    box['category'] == 'Fill-in-the-Blank'}

    # pprint.pprint(mc_questions)

    parsed_mc_qs, parsed_mc_instructions = parse_mc_questions(mc_questions)
    # pprint.pprint(parsed_mc_instructions)
    # parsed_sa_qs, parsed_sa_instructions = parse_sa_questions(sa_questions)
    # parsed_tf_qs, parsed_tf_instructions = parse_tf_questions(tf_questions)
    # parsed_fib_qs, parsed_fib_instructions = parse_fib_questions(fib_questions)
    # all_questions.update(parsed_sa_qs)
    all_questions.update(parsed_mc_qs)
    # all_questions.update(parsed_tf_qs)
    # all_questions.update(parsed_fib_qs)

    return all_questions




