"""
Copyright 2019, University of Freiburg
Chair of Algorithms and Data Structures.
Hannah Bast <bast@cs.uni-freiburg.de>
Claudius Korzen <korzen@cs.uni-freiburg.de>
Patrick Brosi <brosi@cs.uni-freiburg.de>
"""

import itertools
import time

# Uncomment to use C version of prefix edit distance calculation.
# from ped_c import ped

# Comment to use C version of prefix edit distance calculation
from ped_python import ped


class QGramIndex:
    """
    A QGram-Index.
    """

    def __init__(self, q):
        '''
        Creates an empty qgram index.
        '''

        self.q = q
        self.padding = "$" * (self.q - 1)
        self.idx = {}
        self.entities = []
        self.norm_names = []
        self.names = []
        self.name_ent = []

        # statistics
        self.ped_calcs = None
        self.ped_time = 0
        self.merges = None
        self.merge_time = 0

    def build_from_file(self, file_name):
        '''
        Builds the index from the given file (one line per entity, see ES5).

        The entity IDs are one-based (starting with one).

        >>> q = QGramIndex(3)
        >>> q.build_from_file("test.tsv")
        >>> sorted(q.idx.items())
        ... # doctest: +NORMALIZE_WHITESPACE
        [('$$b', [(2, 1)]), ('$$f', [(1, 1)]), ('$br', [(2, 1)]),
         ('$fr', [(1, 1)]), ('bre', [(2, 1)]), ('fre', [(1, 1)]),
         ('rei', [(1, 1), (2, 1)])]
        '''

        with open(file_name, "r", encoding="utf-8") as f:
            ent_id = 0
            name_id = 0
            f.readline()  # skip first line

            for line in f:
                ent_id += 1
                parts = line.split("\t")

                # cache the entity
                self.entities.append(parts)

                names = [parts[0]]

                for n in names:
                    name_id += 1
                    self.name_ent.append(ent_id)
                    normed_name = self.normalize(n)
                    # cache the normalized names
                    self.norm_names.append(normed_name)
                    self.names.append(n)

                    for qgram in self.compute_qgrams(normed_name):
                        if qgram not in self.idx:
                            self.idx[qgram] = []
                        if (len(self.idx[qgram]) > 0 and
                                self.idx[qgram][-1][0] == name_id):
                            self.idx[qgram][-1] = (self.idx[qgram]
                                                   [-1][0],
                                                   self.idx[qgram][-1][1] + 1)
                        else:
                            self.idx[qgram].append((name_id, 1))

    def compute_qgrams(self, word):
        '''
        Compute q-grams for padded version of given string.

        >>> q = QGramIndex(3)
        >>> q.compute_qgrams("freiburg")
        ['$$f', '$fr', 'fre', 'rei', 'eib', 'ibu', 'bur', 'urg']
        '''

        ret = []
        padded = self.padding + word
        for i in range(0, len(word)):
            ret.append(padded[i:i + self.q])
        return ret

    def merge_lists(self, lists):
        '''
        Merges the given inverted lists.

        >>> q = QGramIndex(3)
        >>> q.merge_lists([[(1, 2), (3, 1), (5, 1)], [(2, 1), (3, 2), (9, 2)]])
        [(1, 2), (2, 1), (3, 3), (5, 1), (9, 2)]
        >>> q.merge_lists([[(1, 2), (3, 1), (5, 1)], []])
        [(1, 2), (3, 1), (5, 1)]
        >>> q.merge_lists([[], []])
        []
        '''

        start = time.monotonic()
        merged = []
        c = 0
        for el in sorted(itertools.chain.from_iterable(lists)):
            c += 1
            if len(merged) != 0 and merged[-1][0] == el[0]:
                merged[-1] = (merged[-1][0], merged[-1][1] + el[1])
            else:
                merged.append(el)

        self.merges = (len(lists), c)
        self.merge_time = (time.monotonic() - start) * 1000
        return merged

    def find_matches(self, prefix, delta):
        '''
        Finds all entities y with PED(x, y) <= delta for a given integer delta
        and a given (normalized) prefix x.

        The test check for a list of triples containing the entity ID,
        the PED distance and its score:

        [(entity id, PED, score), ...]

        The entity IDs are one-based (starting with 1).

        >>> q = QGramIndex(3)
        >>> q.build_from_file("test.tsv")
        >>> q.find_matches("frei", 0)
        [(1, 0, 3, 1)]
        >>> q.find_matches("frei", 2)
        [(1, 0, 3, 1), (2, 1, 2, 2)]
        >>> q.find_matches("freibu", 2)
        [(1, 2, 3, 1)]
        '''

        threshold = len(prefix) - (self.q * delta)
        matches = []
        tot = 0
        c = 0

        lists = []
        for qgram in self.compute_qgrams(prefix):
            if qgram in self.idx:
                lists.append(self.idx[qgram])

        merged = self.merge_lists(lists)

        start = time.monotonic()

        for pair in merged:
            tot += 1
            if pair[1] >= threshold:
                # ids are 1-based
                pedist = ped(prefix, self.norm_names[pair[0] - 1], delta)
                c += 1
                if pedist <= delta:
                    matches.append(
                        (self.name_ent[pair[0] - 1], pedist, pair[0]))
                    continue

        self.ped_calcs = (c, tot)
        self.ped_time = (time.monotonic() - start) * 1000

        # only one result per entity, namely the best PED
        matches = sorted(matches, key=lambda match: (match[0], match[1]))

        ret = []

        for match in matches:
            if len(ret) == 0 or ret[-1][0] != match[0]:
                ret.append((match[0], match[1], int(
                    self.entities[match[0] - 1][1]), match[2]))

        return ret

    def normalize(self, word):
        '''
        Normalize the given string (remove non-word characters and lower case).

        >>> q = QGramIndex(3)
        >>> q.normalize("freiburg")
        'freiburg'
        >>> q.normalize("Frei, burG !?!")
        'freiburg'
        '''

        low = word.lower()
        return ''.join([i for i in low if i.isalnum()])

    def rank_matches(self, matches):
        '''
        Ranks the given list of (entity id, PED, s), where PED is the PED
        value and s is the popularity score of an entity.

        The test check for a list of triples containing the entity ID,
        the PED distance and its score:

        [(entity id, PED, score), ...]

        >>> q = QGramIndex(3)
        >>> q.rank_matches([(1, 0, 3), (2, 1, 2), (2, 1, 3), (1, 0, 2)])
        [(1, 0, 3), (1, 0, 2), (2, 1, 3), (2, 1, 2)]
        '''

        return sorted(matches, key=lambda post: (post[1], -post[2]))

    def fuzzy_search(self, search_query):
        '''
        Finds the search result for given search_query
        '''

        search_results = []
        search_query = self.normalize(search_query)

        # Process the keywords.
        delta = int(len(search_query) / 4)

        postings = self.find_matches(search_query, delta)
        rank_match = self.rank_matches(postings)

        for ent in rank_match[:5]:
            search_results.append((self.entities[ent[0] - 1][0],
                                   self.entities[ent[0] - 1][1],
                                   self.entities[ent[0] - 1][2],
                                   self.entities[ent[0] - 1][3]))

        return search_results
