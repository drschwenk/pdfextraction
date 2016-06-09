# coding: utf-8
import pickle
import boto
import pandas as pd
import json
import jsonschema
from collections import defaultdict
from copy import deepcopy
import boto.mturk.connection as tc
import boto.mturk.question as tq
from boto.mturk.qualification import PercentAssignmentsApprovedRequirement, Qualifications, Requirement
import requests

from annotation_schema import page_schema


def load_book_info():
    with open('breakdowns.pkl', 'rb') as f:
        book_breakdowns = pickle.load(f)

    with open('pdfs/page_ranges.csv') as f:
        ranges = f.readlines()
    range_lookup = {line.split(' ')[0]:[int(num) for num in line.strip().split(' ')[1:]] for line in ranges}
    return book_breakdowns, range_lookup


def form_hit_url(book_name, page_n):
    book_name_no_ext = book_name.replace('.pdf', '_')
    base_url = 'https://s3-us-west-2.amazonaws.com/ai2-vision-turk-data/textbook-annotation-test/textbook_hit_instructions/instructions.html'
    full_url = base_url + '?url={}{}.jpeg&id={}'.format(book_name_no_ext, page_n, page_n)
    return full_url


def make_book_group_urls(book_groups, book_group, ranges):
    group_urls = []

    def get_start_end(start, end):
        return start, end
    
    for tb in book_groups[book_group]:
        start, end = get_start_end(*ranges[tb])
        for page_n in range(start, end):
            group_urls.append(form_hit_url(tb, page_n))
    return group_urls


def build_hit_params(url, static_params):
    def build_qualifications():
        qualifications = Qualifications()
        req1 = PercentAssignmentsApprovedRequirement(comparator="GreaterThan", integer_value="95")
        qualifications.add(req1)
        return qualifications
    
    hit_params = deepcopy(static_params)
    hit_params['qualifications'] = build_qualifications()
    hit_params['questionform'] = tq.ExternalQuestion(url, static_params['frame_height'])
    hit_params['reward'] = boto.mturk.price.Price(hit_params['amount'])
    return hit_params


def create_single_hit(mturk_connection, url, static_hit_params):
    """
    creates a single HIT from a provided url
    """
    
    hit_params = build_hit_params(url, static_hit_params)
    
    create_hit_result = mturk_connection.create_hit(
        title=hit_params['title'],
        description=hit_params['description'],
        keywords=hit_params['keywords'],
        question=hit_params['questionform'],
        reward=hit_params['reward'],
        max_assignments=hit_params['max_assignments'],
        duration=hit_params['duration'],
        qualifications=hit_params['qualifications']
    )
    return create_hit_result


def create_hits_from_pages(mturk_connection, page_links, static_hit_params):
    for url in page_links:
        create_single_hit(mturk_connection, url, static_hit_params)
    

def delete_all_hits(mturk_connection):
    my_hits = list(mturk_connection.get_all_hits())
    for hit in my_hits:
        mturk_connection.disable_hit(hit.HITId)


def get_completed_hits(mturk_connection):
    reviewable_hits = []

    page_n = 1
    hits_left = True
    while hits_left:
        hit_range = mturk_connection.get_reviewable_hits(page_size=100, page_number=page_n)
        if not hit_range:
            hits_left = False
            break
        reviewable_hits.extend(hit_range)
        page_n += 1
    return reviewable_hits


def get_assignments(mturk_connection, reviewable_hits):
    assignments = defaultdict(list)
    for hit in reviewable_hits:
        assignment = mturk_connection.get_assignments(hit.HITId)
        assignments[hit.HITId].extend(assignment)
    return assignments


def process_raw_hits(assignments_by_hit):
    mechanical_turk_results = defaultdict(list)
    for hit_id, hit_assignments in assignments_by_hit.items():
        for assignment in hit_assignments:
            for answers in assignment.answers:
                box_result = answers[1].fields[0]
                box_json = json.loads(box_result)
                for box in box_json:
                    box['worker_id'] = assignment.WorkerId
                mechanical_turk_results[hit_id].append({
                    assignment.AssignmentId: {answers[0].fields[0]: box_json}}
                )
    return mechanical_turk_results


def accept_hits(mturk_connection, assignments_to_approve):
    for hit_id, hit_assignments in assignments_to_approve.items():
        for assignment in hit_assignments:
            mturk_connection.approve_assignment(assignment.AssignmentId)
        mturk_connection.disable_hit(hit_id)


def make_results_df(raw_hit_results):
    col_names = ['page', 'category', 'hit_id', 'assignment_id', 'box_id', 'worker_id']
    results_df = pd.DataFrame(columns=col_names)
    idx = 0
    for hit_id, assignments in raw_hit_results.items():
        for assignment in assignments:
            for a_id, annotation in assignment.items():
                for page, labeled_text in annotation.items():
                    for box in labeled_text:
                        results_df.loc[idx] = \
                            [page, box['category'], hit_id, a_id, box['id'], box['worker_id']]
                        idx += 1
    return results_df


def form_annotation_url(page_name):
    base_path = '/Users/schwenk/wrk/notebooks/stb/ai2-vision-turk-data/textbook-annotation-test/merged-annotations/'
    return base_path + page_name.replace('jpeg', 'json')


def load_local_annotation(page_name):
    base_path = '/Users/schwenk/wrk/notebooks/stb/ai2-vision-turk-data/textbook-annotation-test/merged-annotations/'
    file_path = base_path + page_name.replace('jpeg', 'json')
    with open(file_path, 'r') as f:
        local_annotations = json.load(f)
    return local_annotations


def process_annotation_results(anno_page_name, boxes, unannotated_page, annotations_folder, page_schema):

    def update_box(result_row):
        box_id = result_row['box_id']
        category = result_row['category']
        unannotated_page['text'][box_id]['category'] = category

    boxes.apply(update_box, axis=1)

    # validator = jsonschema.Draft4Validator(page_schema)
#     validator.validate(json.loads(json.dumps(unannotated_page)))
    file_path = annotations_folder + anno_page_name.replace('jpeg', 'json').replace("\\", "")
    with open(file_path, 'wb') as f:
        json.dump(unannotated_page, f)
    return


def write_consensus_results(page_name, boxes):
    unaltered_annotations = load_local_annotation(page_name)
    local_result_path = './ai2-vision-turk-data/textbook-annotation-test/test-annotations/'
    process_annotation_results(page_name, boxes, unaltered_annotations, local_result_path, page_schema)


def write_results_df(aggregate_results_df):
    for page, boxes in aggregate_results_df.groupby('page'):
        write_consensus_results(page, boxes)


def review_results(pages_to_review):
    review_api_endpoint = 'http://localhost:8080/api/review'
    payload = {'pages_to_review': str(pages_to_review)}
    headers = {'content-type': 'application/json'}
    requests.post(review_api_endpoint, data=json.dumps(payload), headers=headers)


def pickle_this(results_df, file_name):
    with open(file_name, 'w') as f:
        pickle.dump(results_df, f)
