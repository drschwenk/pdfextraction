def process_mc_group(question_boxes):

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

    re_pattern = re.compile('([A-Z])(?:[a-z]?){1}\s')
    complete_questions = defaultdict(dict)
    instructions = defaultdict(dict)


    q_series = page_boxes['question']
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

        elif re.findall(re_pattern, box_text) and re.findall(re_pattern, box_text)[0] in letter_starters:
            structural_label = re.findall(re_pattern, box_text)[0]
            make_possible_answer_entry(structural_label, complete_questions, qv)
        elif box_text[-1] in letter_starters:
            structural_label = box_text[-1]
            make_possible_answer_entry(structural_label, complete_questions, qv)

        elif current_question_id and box_category == 'Multiple Choice':
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