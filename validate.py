#!/usr/bin/env python3


import os.path
from collections import defaultdict
from collections import Counter
import copy
from pprint import pprint
import warnings
import glob
import json
import sys
import argparse
import re
from io import StringIO


def validate(ck12_json):
    import jsonschema
    """
    validate ck12 dataset using the jsonschema defined below
    """

    def fetch_identifiers(doc):
        identifiers = defaultdict(set)
        for k in ['text', 'regions', 'blobs', 'objects', 'arrows', 'arrowHeads']:
            identifiers[k].update(list(doc[k].keys()))

        identifiers['relationships'].update(
            list(doc['relationships']['intraObject']['linkage'].keys()))
        identifiers['relationships'].update(
            list(doc['relationships']['intraObject']['label'].keys()))
        identifiers['relationships'].update(
            list(doc['relationships']['interObject']['linkage'].keys()))

        return identifiers

    def create_schema(doc):
        ids = fetch_identifiers(doc)
        id_regex = dict()
        for k, v in ids.items():
            id_regex[k] = '|'.join(v)

        def recurse(d):
            if type(d) == list:
                for x in d:
                    recurse(x)
            elif type(d) == dict:
                for k, v in d.items():
                    if k == 'pattern':
                        d[k] = v.format(**id_regex)
                    recurse(v)
        evaluated_schema = copy.deepcopy(schema)
        recurse(evaluated_schema)
        return evaluated_schema

    for p in glob.glob(shining3Path + "/*.json"):
        with open(p) as f:
            j = json.loads(f.read())

        image_name = p.split('/')[2].split('.json')[0]
        if int(image_name.split('.')[0]) > 1507:
            try:
                validator = jsonschema.Draft4Validator(create_schema(j))
                for error in sorted(validator.iter_errors(j), key=str):
                    warnings.warn("Error in schema --%s-- for %s" % (error.message, image_name))
            except jsonschema.ValidationError as e:
                warnings.warn("Error in schema --%s-- for %s" % (e.message, image_name))


def run_tests():

    with open("categories.json") as f:
        categories = json.loads(f.read())

    validateDataset('./annotations')


def main():
    parser = argparse.ArgumentParser(description='Run Shining3 validation tests')
    parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
    args = parser.parse_args()

    if not args.verbose:
        warning_buffer = StringIO()
        saved_stderr = sys.stderr
        sys.stderr = warning_buffer
        run_tests()
        warnings = warning_buffer.getvalue()
        warning_buffer.close()
        sys.stderr = saved_stderr
        warning_pattern = re.compile('validate.py:\d+:\s+UserWarning:\s+(.+)\s+[0-9]+\.png')
        single_warns = re.findall(warning_pattern, warnings)
        warning_counts = Counter()
        for warn in single_warns:
            warning_counts.update([warn])

        print('Summary of warnings'+'\n'*2)
        for warning, count in warning_counts.most_common():
            print('%s, %d occurrences' % (warning, count) + '\n'*2)

    else:
        run_tests()

if __name__ == "__main__":
    main()



