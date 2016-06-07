# coding: utf-8
import pickle
import boto
import json
import jsonschema
from collections import defaultdict
from copy import deepcopy
import boto.mturk.connection as tc
import boto.mturk.question as tq
from boto.mturk.qualification import PercentAssignmentsApprovedRequirement, Qualifications, Requirement
from flask import request
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
        req1 = PercentAssignmentsApprovedRequirement(comparator = "GreaterThan", integer_value = "95")
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
    while True and page_n < 8:
        print page_n
        hit_range = mturk_connection.get_reviewable_hits(page_size=100, page_number=page_n)
        print hit_range
        reviewable_hits.extend(hit_range)
        page_n += 1
    return reviewable_hits


def get_assignments(mturk_connection, reviewable_hits):
    assignments = defaultdict(list)
    for hit in reviewable_hits:
        assignment = mturk_connection.get_assignments(hit.HITId)
        print  assignment
        assignments[assignment.AssignmentId].append(assignment)
    return assignments


def process_raw_hits(assignments):
    mechanical_turk_results = defaultdict(list)
    for hit_id, assignment in assignments.items():
        for answers in assignment[0][0].answers:
            mechanical_turk_results[answers[0].fields[0]].append({hit_id: answers[1].fields})
    return mechanical_turk_results


def accept_hits(mturk_connection, assignments_to_approve):
    for hit_id, assignment in assignments_to_approve.items():
        print hit_id, assignment[0][0].AssignmentId
        mturk_connection.approve_assignment(assignment[0][0].AssignmentId)
        mturk_connection.disable_hit(hit_id)


def form_annotation_url(page_name):
    base_path = '/Users/schwenk/wrk/notebooks/stb/ai2-vision-turk-data/textbook-annotation-test/test-annotations/'
    return base_path + page_name.replace('jpeg', 'json')


def load_local_annotation(page_name):
    base_path = '/Users/schwenk/wrk/notebooks/stb/ai2-vision-turk-data/textbook-annotation-test/test-annotations/'
    file_path = base_path + page_name.replace('jpeg', 'json')
    with open(file_path, 'r') as f:
        local_annotations = json.load(f)
    return local_annotations


def process_annotation_results(anno_page_name, turk_consensus_result, unannotated_page, annotations_folder, page_schema):

    turk_results_json = json.loads(turk_consensus_result[0])
    for result in turk_results_json:
        unannotated_page['text'][result['id']]['category'] = result['category']

    validator = jsonschema.Draft4Validator(page_schema)
#     validator.validate(json.loads(json.dumps(unannotated_page)))

    file_path = annotations_folder + anno_page_name.replace('jpeg', 'json').replace("\\", "")
    with open(file_path, 'wb') as f:
        json.dump(unannotated_page, f)
    return


def write_consensus_results(consensus_results):
    for page_name, results in consensus_results.iteritems():
        local_result_path = './ai2-vision-turk-data/textbook-annotation-test/test-annotations/'
        unaltered_annotations = load_local_annotation(page_name)
        process_annotation_results(page_name, results, unaltered_annotations, local_result_path, page_schema)


def review_results(consensus_results):
    review_api_endpoint = 'http://localhost:8080/api/review'
    payload = {'pages_to_review': str(consensus_results.keys())}
    headers = {'content-type': 'application/json'}
    requests.post(review_api_endpoint, data=json.dumps(payload), headers=headers)

# book_groups,ranges = load_book_info()
# daily_sci_urls = make_book_group_urls(book_groups, 'daily_sci', ranges)
# spectrum_sci_urls = make_book_group_urls(book_groups, 'spectrum_sci', ranges)
