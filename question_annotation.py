from collections import OrderedDict
from collections import defaultdict
import json


def make_annotation_w_questions(original_annotation, book_name, page_n):
    text_boxes = original_annotation['text']
    annotation = defaultdict(defaultdict)
    for box_id, box in text_boxes.items():

        category = box['category']
        try:
            if category == 'Question':
                box_id = box['box_id'].replace('T', 'Q')
                annotation['question'][box_id] = {
                    "box_id": box_id,
                    "category": category,
                    "contents": box['contents'],
                    "score": box['score'],
                    "rectangle": box['rectangle'],
                    "v_dim": box['v_dim'],
                    "group_n": 0,
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
            else:
                annotation['text'][box_id] = {
                    "box_id": box['box_id'],
                    "category": category,
                    "contents": box['contents'],
                    "score": box['score'],
                    "rectangle": box['rectangle'],
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
        except KeyError as e:
            print e
            annotation['text'] = {}

    annotation['figure'] = {}
    annotation['relationship'] = {}
    return annotation


def amend_single_book(book_name, (start_n, stop_n), destination_path, base_path):
    for page_n in range(start_n, stop_n):
        try:
            file_path = base_path + book_name.replace('.pdf', '') + '_' + str(page_n) + '.json'
            new_file_path = destination_path + book_name.replace('.pdf', '') + '_' + str(page_n) + '.json'

            with open(file_path, 'rb') as f:
                base_annotation = json.load(f)

            full_annotation = make_annotation_w_questions(base_annotation, book_name, page_n)
            with open(new_file_path, 'w') as f:
                json.dump(full_annotation, f)
        except IOError as e:
            print e
    return
