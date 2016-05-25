import json
from collections import OrderedDict
from collections import defaultdict
import requests

from ocr_pipeline import assemble_url


class Detection:

    def __init__(self, start_x, start_y, end_x, end_y, value, score):
        self.start_x = start_x
        self.start_y = start_y
        self.end_x = end_x
        self.end_y = end_y
        self.value = value
        self.score = score

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


def make_annotation_json(box):
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
            "source": {
                "type": "object",
                "$schema": "http://json-schema.org/draft-04/schema",
                "additionalProperties": False,
                "properties": [
                    {"book_source": 't'},
                    {"page_n": 1}
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


def merge_boxes(detections, y_threshold=1.0, x_threshold=1.0):
    rectangle_groups = []
    int_keys = {int(k[1:]): v for k,v in detections.items()}
    sdets = OrderedDict(sorted(int_keys.items()))
    for name, current_d in sdets.items():
        found_group = False
        for g in rectangle_groups:
            if not found_group:
                for d in g:
                    y_distance = min(abs(start_y(d) - end_y(current_d)), abs(start_y(current_d) - end_y(d)))
                    if y_distance < (height(d) * y_threshold) and start_x(current_d) < end_x(d) *x_threshold and end_x(current_d)*x_threshold > start_x(d):
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
            min_x = min(map(lambda x: start_x(x), g))
            max_x = max(map(lambda x: end_x(x), g))
            min_y = min(map(lambda x: start_y(x), g))
            max_y = max(map(lambda x: end_y(x), g))
            words = ' '.join(map(lambda x: get_value(x), g))
            score = ' '.join(map(lambda x: str(get_score(x)), g))
            detection = Detection(min_x, min_y, max_x, max_y, words, score)
            new_detection = make_annotation_json(detection.to_JSON())
            new_detections.append(new_detection)
    return new_detections


def merge_single_page(file_path, y_tol):
    with open(file_path, 'r') as f:
        annotations = json.load(f)
    merged_annotation = merge_boxes(annotations['text'], y_tol)
    return merged_annotation


def merge_single_book(book_name, (start_n, stop_n), destination_path, y_tol):
    base_path = './ai2-vision-turk-data/textbook-annotation-test/unmerged-annotations/'
    for page_n in range(start_n, stop_n):
        file_path = base_path + book_name.replace('.pdf', '') + '_' + str(page_n) + '.json'
        merged_text_anno = merge_single_page(file_path, y_tol)
        merged_text_named = {'T'+str(i + 1): merged_text_anno[i] for i in range(len(merged_text_anno))}
        for name, detection in merged_text_named.items():
            detection['box_id'] = name
        new_file_path = destination_path + book_name.replace('.pdf', '') + '_' + str(page_n) + '.json'
        full_anno = {"text": merged_text_named, "figure": {}, "relationship": {}}

        with open(new_file_path, 'w') as f:
            json.dump(full_anno, f)
    return

