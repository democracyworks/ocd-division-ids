#!/usr/bin/env python3
import re
import os
import sys
import csv
import glob
import argparse
import warnings
import collections

# Explicitly disallow python 2.x
if sys.version_info < (3, 0):
    sys.stdout.write("Python 2.x not supported.\n")
    sys.exit(1)


def validate_id(id_):
    id_regex = re.compile(r'^ocd-division/country:[a-z]{2}(/[^\W\d]+:[\w.~-]+)*$', re.U)
    if not id_regex.match(id_) and id_.lower() == id_:
        raise ValueError('invalid id: ' + id_)


def open_csv(filename):
    """ return a DictReader iterable regardless of input CSV type """
    print('processing', filename)
    fh = open(filename)
    first_row = next(csv.reader(fh))
    if 'ocd-division/country' in first_row[0]:
        warnings.warn('proceeding in legacy mode, please add column headers to file',
                      DeprecationWarning)
        fh.seek(0)
        return csv.DictReader(fh, ('division_id', 'name'))
    else:
        fh.seek(0)
        return csv.DictReader(fh)


def main():
    parser = argparse.ArgumentParser(description='combine component CSV files into one')
    parser.add_argument('country', type=str, default=None, help='country to compile')
    args = parser.parse_args()
    country = args.country.lower()

    ids = collections.defaultdict(dict)
    sources = collections.defaultdict(list)
    records_with = collections.Counter()
    types = collections.Counter()
    all_keys = []
    missing_parents = set()

    for filename in glob.glob('identifiers/country-{}/*.csv'.format(country)):
        if filename.endswith('exceptions.csv'):
            continue

        csvfile = open_csv(filename)
        for field in csvfile.fieldnames:
            if field not in all_keys:
                all_keys.append(field)

        for row in csvfile:
            id_ = row['division_id']
            validate_id(id_)

            # check parents
            parent, endpiece = id_.rsplit('/', 1)
            if parent != 'ocd-division' and parent not in ids:
                missing_parents.add(parent)

            # count types
            type_ = endpiece.split(':')[0]
            types[type_] += 1

            # update record
            id_record = ids[id_]
            for key, val in row.items():
                # skip if value is blank
                if not val:
                    continue
                elif key not in id_record:
                    id_record[key] = val
                    records_with[key] += 1
                elif val and id_record[key] != val:
                    print('mismatch for attribute {} on {} from {}'.format(key, id_, filename))
                    print('other sources:')
                    for source in sources[id_]:
                        print('   ', source)
                    return 1
            # add source
            sources[id_].append(filename)

    missing_parents -= set(ids.keys())
    if missing_parents:
        print(len(missing_parents), 'unknown parents')
        for parent in sorted(seen_parents):
            print('   ', parent)
        return 1

    # print some statistics
    print('types')
    for type_, count in types.most_common():
        print('   {:<25} {:>10}'.format(type_, count))

    print('fields')
    for key, count in records_with.most_common():
        print('   {:<15} {:>10}'.format(key, count))

    # write output file
    output_file = 'identifiers/country-{}.csv'.format(country)
    print('writing', output_file)
    with open(output_file, 'w') as out:
        out = csv.DictWriter(out, fieldnames=all_keys)
        out.writeheader()
        for id_, row in sorted(ids.items()):
            out.writerow(row)

if __name__ == '__main__':
    sys.exit(main())
