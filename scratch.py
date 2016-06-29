single_page = ['Daily_Science_Grade_2_Evan_Moor_144.jpeg']
# single_page = ['Daily_Science_Grade_5_Evan_Moor_33.jpeg']
# single_page = ['Daily_Science_Grade_6_(Daily_Practice_Books)_Evan_Moor_123.jpeg']

numeric_starters = [str(n) + '.' for n in range(10)]
letter_punct_starters = [char + '.' for char in string.ascii_uppercase[:6]]
letter_starters = [char for char in string.ascii_uppercase[:6]]

re_pattern = re.compile('([A-Z])(?:[a-z]?){1}\s')

pages = single_page
for page in pages:
    complete_questions = {}
    
    page_file_path = test_path + page.replace('jpeg', 'json')
    with open(page_file_path) as f:
        page_boxes = json.load(f)

    q_series = page_boxes['question']
    vertically_ordered_question = sorted(q_series.values(), key=lambda x: (x['rectangle'][0][1], x['rectangle'][0][0]))
    current_question_id = False
    ask_index = 0
    for qv in vertically_ordered_question:
        box_category = qv['category']
        del qv['source']
        del qv['score']
        del qv['v_dim']
        del qv['category']
        box_text = qv['contents'].replace('(', '').replace(')', '').replace('O', '')
        if box_text[:2] in numeric_starters:
            ask_index = 1
            current_question_id = 'full_Q_' + box_text[:1]
            complete_questions[current_question_id] = {
                "question_id" : current_question_id,
                "category": box_category,
                "structural_id" : box_text[:2],
                "asks" : {'Qc' + str(ask_index) : qv},
                "answer_choices" : {}
            }
#             print 'question'
#             print box_text
#             print
        elif re.findall(re_pattern, box_text) and re.findall(re_pattern, box_text)[0] in letter_starters:
            structural_label = re.findall(re_pattern, box_text)[0]
            current_choice_id = "answer_choice_" + structural_label
            complete_questions[current_question_id]['answer_choices'][current_choice_id] = {
                "structural_label" : structural_label,
                "possible_answer" : qv 
            }
#             print 'choice'
#             print re.findall(re_pattern, box_text)[0]
#             print box_text
#             print
        elif box_text[-1 ]in letter_starters:
            structural_label = box_text[-1]
            current_choice_id = "answer_choice_" + structural_label
            complete_questions[current_question_id]['answer_choices'][current_choice_id] = {
                "structural_label" : structural_label,
                "possible_answer" : qv
            }
        elif current_question_id and box_category == 'Multiple Choice':
            ask_index += 1
            complete_questions[current_question_id]['asks']['Qc' + str(ask_index)] = qv
        else:
            print 'miss'
            print box_text
            print
    pprint.pprint(complete_questions)