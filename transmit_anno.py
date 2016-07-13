import json


def start_x(box):
    return box[0][0]


def start_y(box):
    return box[0][1]


def end_x(box):
    return box[1][0]


def end_y(box):
    return box[1][1]


def box_overlaps(this_box, other_box, overlap_tol_fract):
    this_coords = [start_x(this_box), start_y(this_box), end_x(this_box), end_y(this_box)]
    other_coords = [start_x(other_box), start_y(other_box), end_x(other_box), end_y(other_box)]

    def area(box):
        return (end_y(box) - start_y(box)) * (end_x(box) - start_x(box))

    dx = min(this_coords[2], other_coords[2]) - max(this_coords[0], other_coords[0])
    dy = min(this_coords[3], other_coords[3]) - max(this_coords[1], other_coords[1])
    if (dx >= 0) and (dy >= 0):
        intersection_area = dx * dy
        return float(intersection_area) / min(area(this_box), area(other_box)) > overlap_tol_fract
    else:
        return False


def find_constituent_boxes(unmerged_anno, merged_anno_box, overlap_tol_fract, box_type):
    constituent_boxes = []
    for box_name, box_vals in unmerged_anno[box_type].items():
        if box_overlaps(box_vals['rectangle'], merged_anno_box['rectangle'], overlap_tol_fract):
            box_vals['category'] = merged_anno_box['category']
            constituent_boxes.append(box_vals)
    return constituent_boxes


def transmit_labels(unmerged_annotations, merged_annotations, overlap_tol_fract):
    new_annotations = []
    for box_name, box_val in merged_annotations['text'].items():
        atomic_boxes = find_constituent_boxes(unmerged_annotations, box_val, overlap_tol_fract, box_type='text')
        if atomic_boxes:
            new_annotations.extend(atomic_boxes)
    sorted_boxes = sorted(new_annotations, key=lambda x: x['rectangle'][0][1])
    unmerged_text_named = {'T' + str(i + 1): sorted_boxes[i] for i in range(len(sorted_boxes))}
    for name, detection in unmerged_text_named.items():
        detection['box_id'] = name
    return unmerged_text_named


def transmit_question_labels(unmerged_annotations, merged_annotations, overlap_tol_fract):
    new_annotations = []
    for box_name, box_val in merged_annotations['question'].items():
        atomic_boxes = find_constituent_boxes(unmerged_annotations, box_val, overlap_tol_fract, 'question')
        if atomic_boxes:
            new_annotations.extend(atomic_boxes)
    sorted_boxes = sorted(new_annotations, key=lambda x: x['rectangle'][0][1])
    unmerged_text_named = {'Q' + str(i + 1): sorted_boxes[i] for i in range(len(sorted_boxes))}
    for name, detection in unmerged_text_named.items():
        detection['box_id'] = name
    return unmerged_text_named


def write_transmitted_annotations(unmerged_text_anno, new_file_path):
    full_anno = {"text": unmerged_text_anno, "figure": {}, "relationship": {}}
    with open(new_file_path, 'w') as f:
        json.dump(full_anno, f)


def write_transmitted_question_annotations(non_q_annotations, unmerged_text_anno, new_file_path):
    full_anno = {"question": unmerged_text_anno, "text": non_q_annotations['text'],"figure": {}, "relationship": {}}
    with open(new_file_path, 'w') as f:
        json.dump(full_anno, f)


def transmit_boxes_single_page(page_image, overlap_tol_fract,
                               base_path, overmerged_dir, unmerged_dir, lessmerged_dir, question_flag):
    json_file = page_image.replace('.jpeg', '.json')

    merged_anno_path = base_path + overmerged_dir + json_file
    unmerged_anno_path = base_path + unmerged_dir + json_file
    lessmerged_anno_path = base_path + lessmerged_dir + json_file

    with open(merged_anno_path, 'rb') as f:
        merged_anno = json.load(f)
    with open(unmerged_anno_path, 'rb') as f:
        unmerged_anno = json.load(f)
    if question_flag:
        unmerged_text_boxes = transmit_question_labels(unmerged_anno, merged_anno, overlap_tol_fract)
        write_transmitted_question_annotations(unmerged_anno, unmerged_text_boxes, lessmerged_anno_path)
    else:
        unmerged_text_boxes = transmit_labels(unmerged_anno, merged_anno, overlap_tol_fract)
        write_transmitted_annotations(unmerged_text_boxes, lessmerged_anno_path)


def transmit_anno_single_textbook(book_name, (start_n, stop_n), overlap_tol_fract,
                                  base_path, overmerged_dir, unmerged_dir, destination_dir, question_round=False):
    for page_n in range(start_n, stop_n):
        page_image = book_name.replace('.pdf', '') + '_' + str(page_n) + '.jpeg'
        try:
            transmit_boxes_single_page(page_image, overlap_tol_fract,
                                       base_path, overmerged_dir, unmerged_dir, destination_dir, question_round)
        except IOError as e:
            print e
