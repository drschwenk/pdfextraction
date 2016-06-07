import json
from collections import OrderedDict
from collections import defaultdict
import operator


from ocr_pipeline import assemble_url


class Detection:

    def __init__(self, start_x, start_y, end_x, end_y, value, score, v_dim):
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.value = value
        self.score = score
        self.v_dim = v_dim

    def height(self):
        return self.end_y - self.start_y

    def width(self):
        return self.end_x - self.start_x

    def average_character_length(self):
        return (self.end_x - self.start_x)/float(len(self.value))

    def horizontal_near(self, other_detection):
        distance = abs(other_detection.start_x - self.end_x)

        return distance/other_detection.average_character_length() < 2.0

    def merge(self, other_detection):
        self.start_x = min(self.start_x, other_detection.start_x)
        self.start_y = min(self.start_y, other_detection.start_y)
        self.end_x = max(self.end_x, other_detection.end_x)
        self.end_y = max(self.end_y, other_detection.end_y)
        self.value += " " + other_detection.value

    def to_JSON(self):
        return {
            'rectangle':[{'x':self.start_x, 'y':self.start_y}, {'x':self.end_x, 'y':self.end_y}],
            'value': self.value,
            'v_dim': self.v_dim,
            'score': self.score}

    def __repr__(self):
        return json.dumps(self.to_JSON())


def det_json_to_obj(detections):
    return [Detection(det['rectangle'][0]['x'],det['rectangle'][0]['y'], det['rectangle'][1]['x'],det['rectangle'][1]['y'], det['value'], det['score']) for det in detections]


def start_x(box):
    return box['rectangle'][0][0]


def start_y(box):
    return box['rectangle'][0][1]


def end_x(box):
    return box['rectangle'][1][0]


def end_y(box):
    return box['rectangle'][1][1]


def height(box):
    return end_y(box) - start_y(box)


def width(box):
    return end_x(box) - start_x(box)


def get_value(box):
    return box['contents']


def get_score(box):
    return box['score']


def get_v_dim(box):
    try:
        return box['v_dim']
    except KeyError:
        return 0


def average_character_length(box):
    return (end_x(box) - start_x(box)) / float(len(get_value(box)))


def horizontal_overlap(this_box, other_box, merge_p):
    boxes_x_coords = [[start_x(this_box), end_x(this_box)], [start_x(other_box), end_x(other_box)]]
    ordered_boxes = sorted(boxes_x_coords)
    overlap = max(0, min(ordered_boxes[0][1], ordered_boxes[1][1]) - max(ordered_boxes[0][0], ordered_boxes[1][0]))
    comp_box_width = max(width(this_box), width(other_box))
    return (overlap / float(comp_box_width)) > merge_p['overlap_x']


def horizontal_overlap2(this_box, other_box, merge_p):
    boxes_x_coords = [[start_x(this_box), end_x(this_box)], [start_x(other_box), end_x(other_box)]]
    ordered_boxes = sorted(boxes_x_coords)
    overlap = max(0, min(ordered_boxes[0][1], ordered_boxes[1][1]) - max(ordered_boxes[0][0], ordered_boxes[1][0]))
    comp_box_width = max(width(this_box), width(other_box))
    return (overlap / float(comp_box_width)) > merge_p['near_overlap_x']


def vertical_overlap(this_box, other_box, merge_p):
    boxes_y_coords = [[start_y(this_box), end_y(this_box)], [start_y(other_box), end_y(other_box)]]
    ordered_boxes = sorted(boxes_y_coords)
    overlap = max(0, min(ordered_boxes[0][1], ordered_boxes[1][1]) - max(ordered_boxes[0][0], ordered_boxes[1][0]))
    comp_box_width = max(height(this_box), height(other_box))
    return overlap / float(comp_box_width) > merge_p['overlap_y']


def horizontal_near(this_detection, other_detection, merge_p):
    x_distance = min(abs(start_x(other_detection) - end_x(this_detection)), abs(start_x(this_detection) - end_x(other_detection)))
    comp_char_len = min(average_character_length(other_detection), average_character_length(this_detection))
    return x_distance < comp_char_len * merge_p['near_x']


def vertical_near(this_box, other_box, merge_p):
    y_distance = min(abs(start_y(other_box) - end_y(this_box)), abs(start_y(this_box) - end_y(other_box)))
    comp_char_len = min(average_character_length(other_box), average_character_length(this_box))
    return y_distance < comp_char_len * merge_p['near_y']


def vertical_near_2(this_box, other_box, merge_p):
    y_distance = min(abs(start_y(other_box) - end_y(this_box)), abs(start_y(this_box) - end_y(other_box)))
    comp_char_len = min(average_character_length(other_box), average_character_length(this_box))
    return y_distance < comp_char_len * merge_p['starting_near_near_y']


def start_near(this_box, other_box, merge_p):
    start_dist = abs(start_x(this_box) - start_x(other_box))
    return start_dist < min(average_character_length(this_box), average_character_length(other_box)) * merge_p['start_x']


def short_line(box, merge_p):
    return width(box) < average_character_length(box) * merge_p['short_length']


def similar_char_size(this_box, other_box, merge_p):
    char_sizes = [average_character_length(this_box), average_character_length(other_box)]
    sorted_char_sizes = sorted(char_sizes)
    return (sorted_char_sizes[1] - sorted_char_sizes[0]) / sorted_char_sizes[0] < merge_p['char_size_ratio']


def merge_contained(this_box, other_box, merge_p):
    this_coords = [start_x(this_box), start_y(this_box), end_x(this_box), end_y(this_box)]
    other_coords = [start_x(other_box), start_y(other_box), end_x(other_box), end_y(other_box)]

    def area(box):
        return (end_y(box) - start_y(box)) * (end_x(box) - start_x(box))

    dx = min(this_coords[2], other_coords[2]) - max(this_coords[0], other_coords[0])
    dy = min(this_coords[3], other_coords[3]) - max(this_coords[1], other_coords[1])
    if (dx >= 0) and (dy >= 0):
        intersection_area = dx * dy
        return float(intersection_area) / min(area(this_box), area(other_box)) > merge_p['overlap_fract']
    else:
        return False


def merge_same_line(this_box, other_box, merge_p):
    location_comp = horizontal_near(this_box, other_box, merge_p) and vertical_overlap(this_box, other_box, merge_p)
    size_comp = similar_char_size(this_box, other_box, merge_p)
    return location_comp and size_comp


def merge_adjacent_lines(this_box, other_box, merge_p):
    comp_all = vertical_near(this_box, other_box, merge_p) and horizontal_overlap(this_box, other_box, merge_p)
    comp_start = vertical_near_2(this_box, other_box, merge_p) and start_near(this_box, other_box, merge_p) and horizontal_overlap2(this_box, other_box, merge_p)
    # comp_all = False
    # comp_start = False
    comp_line_length = short_line(this_box, merge_p) or short_line(this_box, merge_p)
    size_comp = similar_char_size(this_box, other_box, merge_p)
    return (comp_all or (comp_start and not comp_line_length)) and size_comp


def make_annotation_json(box, book_name, page_n):
    def point_to_tuple(box):
        return tuple(OrderedDict(sorted(box.items())).values())

    def get_bbox_tuples(detection):
        return map(point_to_tuple, detection['rectangle'])

    ids = 1
    annotation = defaultdict(defaultdict)
    try:
        box_id = 'T' + str(ids)
        bounding_rectangle = get_bbox_tuples(box)
        annotation['text'][box_id] = {
            "box_id": box_id,
            "category": "unlabeled",
            "contents": box['value'],
            "score": box['score'],
            "rectangle": bounding_rectangle,
            "v_dim": box['v_dim'],
            "source": {
                "type": "object",
                "$schema": "http://json-schema.org/draft-04/schema",
                "additionalProperties": False,
                "properties": [
                    {"book_source": book_name},
                    {"page_n": page_n}
                ]
            }
        }
        ids += 1
    except KeyError:
        return
        annotation['text'] = {}

    annotation['figure'] = {}
    annotation['relationship'] = {}
    return annotation['text'].values()[0]


def merge_boxes(detections, merge_params, book_name, page_n):
    int_keys = {int(k[1:]): v for k, v in sorted(detections.items(), key=lambda x: x[1]['rectangle'][0][1])}
    sorted_detections = OrderedDict(sorted(int_keys.items()))

    def merge_box_values(g, book_name, page_n):
        min_x = min(map(lambda x: start_x(x), g))
        max_x = max(map(lambda x: end_x(x), g))
        min_y = min(map(lambda x: start_y(x), g))
        max_y = max(map(lambda x: end_y(x), g))
        words = ' '.join(map(lambda x: get_value(x), g))
        score = sum([get_score(x) for x in g])/len(g)
        v_dim = get_v_dim(g[0])
        detection = Detection(min_x, min_y, max_x, max_y, words, score, v_dim)
        new_detection = make_annotation_json(detection.to_JSON(), book_name, page_n)
        return new_detection

    def merge_horizontal_pass(detected_boxes, merge_p):
        rectangle_groups = []
        for name, current_d in detected_boxes.items():
            found_group = False
            for g in rectangle_groups:
                if not found_group:
                    for d in g:
                        if merge_same_line(current_d, d, merge_p):
                            g.append(current_d)
                            found_group = True
                            break
            if not found_group:
                rectangle_groups.append([current_d])

        new_detections = []
        for g in rectangle_groups:
            if len(g) == 1:
                new_detections.append(g[0])
            else:
                new_detections.append(merge_box_values(g, book_name, page_n))

        return sorted(new_detections, key=lambda x: x['rectangle'][0][1])

    def merge_vertical_pass(detected_boxes, merge_p):
        rectangle_groups = []
        for current_d in detected_boxes:
            found_group = False
            for g in rectangle_groups:
                if not found_group:
                    for d in g:
                        if merge_adjacent_lines(current_d, d, merge_p):
                            g.append(current_d)
                            found_group = True
                            break
            if not found_group:
                rectangle_groups.append([current_d])

        new_detections = []
        for g in rectangle_groups:
            if len(g) == 1:
                new_detections.append(g[0])
            else:
                new_detections.append(merge_box_values(g, book_name, page_n))

        return new_detections

    def merge_final_pass(detected_boxes, merge_p):
        rectangle_groups = []
        # for name, current_d in detected_boxes.items():
        for current_d in detected_boxes:
            found_group = False
            for g in rectangle_groups:
                if not found_group:
                    for d in g:
                        if merge_contained(current_d, d, merge_p):
                            g.append(current_d)
                            found_group = True
                            break
            if not found_group:
                rectangle_groups.append([current_d])

        new_detections = []
        for g in rectangle_groups:
            if len(g) == 1:
                new_detections.append(g[0])
            else:
                new_detections.append(merge_box_values(g, book_name, page_n))
        return sorted(new_detections, key=lambda x: x['rectangle'][0][1])

    horizontal_pass_dets = merge_horizontal_pass(sorted_detections, merge_params)
    overlap_pass_dets = merge_final_pass(horizontal_pass_dets, merge_params)
    vertical_pass_combined = merge_vertical_pass(overlap_pass_dets, merge_params)
    return vertical_pass_combined


def merge_single_page(file_path, merge_params, book_name, page_n):
    with open(file_path, 'r') as f:
        annotations = json.load(f)
    merged_annotation = merge_boxes(annotations['text'], merge_params, book_name, page_n)
    return merged_annotation


def merge_single_book(book_name, (start_n, stop_n), destination_path, merge_params):
    base_path = './ai2-vision-turk-data/textbook-annotation-test/annotations_ws/'
    for page_n in range(start_n, stop_n):
        file_path = base_path + book_name.replace('.pdf', '') + '_' + str(page_n) + '.json'
        merged_text_anno = merge_single_page(file_path, merge_params, book_name, page_n)
        merged_text_named = {'T'+str(i + 1): merged_text_anno[i] for i in range(len(merged_text_anno))}

        for name, detection in merged_text_named.items():
            detection['box_id'] = name

        new_file_path = destination_path + book_name.replace('.pdf', '') + '_' + str(page_n) + '.json'
        full_anno = {"text": merged_text_named, "figure": {}, "relationship": {}}

        with open(new_file_path, 'w') as f:
            json.dump(full_anno, f)
    return

