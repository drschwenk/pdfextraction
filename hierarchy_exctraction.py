import json
import string
import re


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


def label_multi_choice_components(question_group):
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


def assemble_questions(pages, file_path):
    numeric_starters = [str(n) + '.' for n in range(10)]
    letter_starters = [char for char in string.ascii_uppercase[:6]]
    letter_punct_starters = [char + '.' for char in string.ascii_uppercase[:6]]

    re_pattern = re.compile('([A-Z])(?:[a-z]?){1}\s')

    for page in pages:
        complete_questions = {}

        page_file_path = file_path + page.replace('jpeg', 'json')
        with open(page_file_path) as f:
            page_boxes = json.load(f)

        q_series = page_boxes['question']
        vertically_ordered_question = sorted(q_series.values(),
                                             key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
        current_question_id = False
        ask_index = 0
        for qv in vertically_ordered_question:
            box_category = qv['category']
            box_text = qv['contents'].replace('(', '').replace(')', '').replace('O', '')
            del qv['source']
            del qv['score']
            del qv['v_dim']
            del qv['category']

            if box_text[:2] in numeric_starters:
                ask_index = 1
                current_question_id = 'full_Q_' + box_text[:1]
                complete_questions[current_question_id] = {
                    "question_id": current_question_id,
                    "category": box_category,
                    "structural_id": box_text[:2],
                    "asks": {'Qc' + str(ask_index): qv},
                    "answer_choices": {}
                }
            elif re.findall(re_pattern, box_text) and re.findall(re_pattern, box_text)[0] in letter_starters:
                structural_label = re.findall(re_pattern, box_text)[0]
                current_choice_id = "answer_choice_" + structural_label
                complete_questions[current_question_id]['answer_choices'][current_choice_id] = {
                    "structural_label": structural_label,
                    "possible_answer": qv
                }
            elif box_text[-1] in letter_starters:
                structural_label = box_text[-1]
                current_choice_id = "answer_choice_" + structural_label
                complete_questions[current_question_id]['answer_choices'][current_choice_id] = {
                    "structural_label": structural_label,
                    "possible_answer": qv
                }
            elif current_question_id and box_category == 'Multiple Choice':
                ask_index += 1
                complete_questions[current_question_id]['asks']['Qc' + str(ask_index)] = qv
            else:
                print 'miss'
                print box_text
                print
    return complete_questions


