import os
import re
import time
import json

# pip3 install python-Levenshtein for 4-10x speedup for fuzzywuzzy
from fuzzywuzzy import fuzz
import pandas as pd
import spacy
# python3 -m spacy download en
nlp = spacy.load('en')


retweets_freq_dict = {}
hashtag_freq_dict = {}
at_freq_dict = {}


# global variables to be later updated and read for autograder
CLEANSED_DATA = []
PREPROCESSED_FLAG = 0
award_winner_dict = {}
award_presenters_dict = {}


def remove_retweet_prefix(line):
    # find 'RT @abc: ' where abc's length is arbitrary
    pattern = re.compile(r'\bRT @([\w\'/]*)\b: ')
    match = re.search(pattern, line)
    if match:
        # store corresponding retweet without 'RT @' prefix
        string = match.group()[4:]
        if string in retweets_freq_dict:
            retweets_freq_dict[string] += 1
        else:
            retweets_freq_dict[string] = 1
    return re.sub(pattern, ' ', line)


def remove_hashtag(line):
    pattern = re.compile(r'#([\w\'/]*)\b')
    matches = re.findall(pattern, line)
    if matches:
        for match in matches:
            if match in hashtag_freq_dict:
                hashtag_freq_dict[match] += 1
            else:
                hashtag_freq_dict[match] = 1
    return re.sub(pattern, ' ', line)


def remove_at(line):
    pattern = re.compile(r'@([\w\'/]*)\b')
    matches = re.findall(pattern, line)
    if matches:
        for match in matches:
            if match in at_freq_dict:
                at_freq_dict[match] += 1
            else:
                at_freq_dict[match] = 1
    return re.sub(pattern, ' ', line)


def remove_url(line):
    pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+\b')
    return re.sub(pattern, ' ', line)


def remove_apostrophe(text):
    pattern = re.compile(r'\'s\b')
    return re.sub(pattern, ' ', text)


def cleanse(line):
    # replace everything to ' ' except whitespace, alphanumeric character, apostrophe, hashtag, @
    return re.sub(r'[^\w\s\'#@-]', ' ', line)


def identify_entities(text):
    tags = {}
    entities = list(nlp(text).ents)
    for entity in entities:
        if entity not in tags:
            tags[entity.text]=[entity.label_]
    return tags


def find_host(CLEANSED_DATA):
    pattern = re.compile(r'\bhost')
    entity_freq_dict = {}
    for line in CLEANSED_DATA:
        match = re.search(pattern, line.lower())
        if match:
            for entity in identify_entities(line).keys():
                entity = entity.strip()
                if len(entity) > 1:
                    if entity not in entity_freq_dict:
                        entity_freq_dict[entity] = 1
                    else:
                        entity_freq_dict[entity] += 1
    return entity_freq_dict


def remove_goldeb_globes(top_results, entity_freq_dict):
    golden_globes = [name for name in [pair[0] for pair in top_results] if fuzz.ratio(name.lower(), 'golden globes') > 60]
    for name in golden_globes:
        if name in entity_freq_dict:
            del entity_freq_dict[name]
    return entity_freq_dict


# we also consider dropping all lower cases examples or examples that contain digit(s), which are not names
def filter_names(pair_list, entity_freq_dict):
    filtered_results = []
    for pair in pair_list:
        string = ''.join(pair[0].split())
        if not all(char.islower() for char in string) and not any(char.isdigit() for char in string):
            filtered_results.append(pair)
        else:
            if pair[0] in entity_freq_dict:
                del entity_freq_dict[pair[0]]
    return filtered_results, entity_freq_dict


def merge_names(top_results, entity_freq_dict):
    names = [pair[0] for pair in top_results]
    names_clusters = []
    for name in names:
        # each name starts as a cluster
        cluster = [name]
        names_to_reduce = names[:]
        names_to_reduce.remove(name)
        # one vs. all comparisons
        for i in names_to_reduce:
            ratio = fuzz.ratio(name.lower(), i.lower())
            # if similarity is larger than 75 or one name is contained in the other name
            if ratio > 75 or re.search(name, i, flags=re.IGNORECASE) or re.search(i, name, flags=re.IGNORECASE):
                cluster.append(i)
        # if multiple names are identified in one cluster
        if len(cluster) > 1:
            names_clusters.append(cluster)

    # find names clusters that should merge
    # ['Amy Poehler', 'Amy', 'Amy Poelher']
    # ['Tina', 'Tina Fey']

    # sort clusters
    names_clusters.sort()
    # sort within each cluster
    names_clusters = ['|'.join(sorted(cluster)) for cluster in names_clusters]
    # remove overlaps
    names_clusters_reduced = [line.split('|') for line in list(set(names_clusters))]
    # sort by length from shortest to longest (merge from the shortest)
    names_clusters_reduced.sort(key=len)

    # weighted frequency of an entity is defined by its frequency multiplied by its string length
    def weighted_freq(element):
        return entity_freq_dict[element] * len(element)

    e = entity_freq_dict.copy()
    for cluster in names_clusters_reduced:
        # select the entity name with highest weighted frequency
        selected_entity_name = max(cluster, key=weighted_freq)
        cluster.remove(selected_entity_name)
        # for names to be merged to the selected entity name
        for name in cluster:
            # if not deleted in previous cases, cumulate frequencies to the selected entity
            if name in e and selected_entity_name in e:
                e[selected_entity_name] += e[name]
                # reward merging
                e[selected_entity_name] += round(e[selected_entity_name]*1/(names.index(selected_entity_name)+1-0.88))
                del e[name]

    top_10 = sorted(e.items(), key=lambda pair: pair[1], reverse=True)[:10]
    return top_10


def find_awards(data):
    endlist = ['picture', 'television', 'drama', 'comedy', 'animated']
    awards = {}
    for item in data:
        l = item.lower().split()
        for j in endlist:
            if 'best' in l and j in l:
                temp1 = l.index('best')
                temp2 = l.index(j)
                if temp1 < temp2:
                    l2 = ['television' if x == 'tv' else x for x in l]
                    key1 = " ".join(l2[temp1:temp2 + 1])
                    if key1 not in awards:
                        awards[key1] = 1
                    else:
                        awards[key1] += 1
    res = []
    for item in awards:
        if awards.get(item) > 95:
            l = item
            if len(l.split()) > 3:
                res.append(item)
    res.sort()
    res.append('cecil b.demille award')
    return res


def reduce(line):
    pattern = r'\btelevision\b'
    line = re.sub(pattern, 'tv', line.lower())

    # remove words "best", "performance", "motion", "picture", "limited", "language", "role", in", "a", "an", "any", "made", "for", "by", "b.", "award", and all punctuations
    pattern = r'\bbest\b|\bperformance\b|\bmotion\b|\bpicture\b|\blimited\b|\blanguage\b|\brole\b|\bin\b|\ba\b|\ban\b|\bany\b|\bmade\b|\bfor\b|\bby\b|\bb\b|\baward\b|[^\w\s]'
    return re.sub(pattern, ' ', line.lower()).split()


def generate_award_num_keywords_map(awards):
    awards_reduced = []
    award_num_keywords_map = {}
    for i, award in enumerate([sorted(set(reduce(award)), key=lambda word: reduce(award).index(word)) for award in awards]):
        if 'or' in award:
            # find number of words from "or" to the end of award name
            num_words = len(award) - 1 - award.index('or')
            award.remove('or')
            # do not count words from "or" to the end of award name
            award_num_keywords_map[i] = len(award) - num_words
        else:
            award_num_keywords_map[i] = len(award)
        awards_reduced.append(award)
    return award_num_keywords_map, awards_reduced


def check_target_words(awards_reduced):
    target_words = ['actor', 'actress', 'director', 'score', 'song', 'foreign', 'tv']
    for word in target_words:
        if word in awards_reduced:
            return word
    return False


def check_primary_target_words(awards_reduced):
    target_words = ['actor', 'actress', 'director', 'score', 'song']
    for word in target_words:
        if word in awards_reduced:
            return word
    return False


def find_award_winner(awards, awards_reduced, award_index, award_num_keywords_map):
    award = awards_reduced[award_index]
    num_keywords_to_match = award_num_keywords_map[award_index]

    # add word boundary '\b' to prevent grabbing examples like "showing" and "wonder"
    pattern = re.compile(r'(\bwin)|(\bwon\b)|(\bbest\b)', re.IGNORECASE)

    entity_freq_dict = {}

    num = 0
    flag = 0

    target_word_pattern = None
    match_target_word = None
    target_word = check_target_words(award)

    # if len(award) != num_keywords_to_match (awards that have 'or' options)
    # and len(award) != 2 (for the case of ['musical', 'comedy']),
    # in addition, if target word in award, target word must be matched
    if len(award) != num_keywords_to_match and target_word:
        flag = 1
        # find target word pattern to match for sure
        primary_target_word = check_primary_target_words(award)
        if primary_target_word:
            target_word_pattern = re.compile(r'\b{0}\b'.format(primary_target_word), re.IGNORECASE)
        # else if primary keyword is not found, match for secondary keyword
        elif 'tv' in award:
            target_word_pattern = re.compile(r'\b{0}\b'.format('tv'), re.IGNORECASE)
        else:
            target_word_pattern = re.compile(r'\b{0}\b'.format(award[0]), re.IGNORECASE)

        for line in CLEANSED_DATA:
            match = re.findall(pattern, line.lower())
            match_target_word = re.findall(target_word_pattern, line.lower())
            # if line contains at least number keywords to match and pattern is found
            num_keywords_matched = len(set(award).intersection(set(line.split())))
            if match and num_keywords_matched >= num_keywords_to_match and match_target_word:
                # reward longer match
                weight = 10 if any('win' in tup for tup in match) else 1
                ratio = round(num_keywords_matched/(num_keywords_to_match+0.0001))
                weight *= ratio

                tags = identify_entities(line)
                for entity in tags.keys():
                    entity_raw = entity
                    entity = entity.strip()
                    if len(entity) > 1:
                        # add more weights for appropriate entity classification
                        if target_word in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                            weight += 5
                        if target_word not in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                            weight -= 5
                        if entity not in entity_freq_dict:
                            entity_freq_dict[entity] = weight
                        else:
                            entity_freq_dict[entity] += weight
                num += 1
    else:
        for line in CLEANSED_DATA:
            match = re.findall(pattern, line.lower())
            # if line contains at least number keywords to match and pattern is found
            num_keywords_matched = len(set(award).intersection(set(line.split())))
            if match and num_keywords_matched == num_keywords_to_match:

                weight = 10 if any('win' in tup for tup in match) else 1
                ratio = round(num_keywords_matched/(num_keywords_to_match+0.0001))
                weight *= ratio

                tags = identify_entities(line)
                for entity in tags.keys():
                    entity_raw = entity
                    entity = entity.strip()
                    if len(entity) > 1:
                        # add more weights for appropriate entity classification
                        if target_word in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                            weight += 5
                        if target_word not in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                            weight -= 5
                        if entity not in entity_freq_dict:
                            entity_freq_dict[entity] = weight
                        else:
                            entity_freq_dict[entity] += weight
                num += 1
    # if no results found, recursively add more keywords and reduce num_keywords_to_match
    while(num == 0 or num < 10):
        num_keywords_to_match -= 1
        if num_keywords_to_match == 0:
            break

        # add alternative word for 'tv'
        if 'tv' in award and 'television' not in award:
            award.append('television')
        # add alternative word for 'Motion Picture'
        if 'Motion Picture' in awards[award_index]:
            award.append('movie')
            award.append('motion')
            award.append('picture')

        if flag == 1:
            for line in CLEANSED_DATA:
                match = re.findall(pattern, line.lower())
                match_target_word = re.findall(target_word_pattern, line.lower())
                # if line contains at least number keywords to match and pattern is found
                num_keywords_matched = len(set(award).intersection(set(line.split())))
                if match and num_keywords_matched >= num_keywords_to_match and match_target_word:

                    weight = 10 if any('win' in tup for tup in match) else 1
                    ratio = round(num_keywords_matched/(num_keywords_to_match+0.0001))
                    weight *= ratio

                    tags = identify_entities(line)
                    for entity in tags.keys():
                        entity_raw = entity
                        entity = entity.strip()
                        if len(entity) > 1:
                            # add more weights for appropriate entity classification
                            if target_word in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                                weight += 5
                            if target_word not in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                                weight -= 5
                            if entity not in entity_freq_dict:
                                entity_freq_dict[entity] = weight
                            else:
                                entity_freq_dict[entity] += weight
                    num += 1
        else:
            for line in CLEANSED_DATA:
                match = re.findall(pattern, line.lower())
                # if line contains at least number keywords to match and pattern is found
                num_keywords_matched = len(set(award).intersection(set(line.split())))
                if match and num_keywords_matched == num_keywords_to_match:

                    weight = 10 if any('win' in tup for tup in match) else 1
                    ratio = round(num_keywords_matched/(num_keywords_to_match+0.0001))
                    weight *= ratio

                    tags = identify_entities(line)
                    for entity in tags.keys():
                        entity_raw = entity
                        entity = entity.strip()
                        if len(entity) > 1:
                            # add more weights for appropriate entity classification
                            if target_word in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                                weight += 5
                            if target_word not in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                                weight -= 5
                            if entity not in entity_freq_dict:
                                entity_freq_dict[entity] = weight
                            else:
                                entity_freq_dict[entity] += weight
                    num += 1
    return entity_freq_dict


def find_award_presenter(awards, awards_reduced, award_index, award_num_keywords_map):
    award = awards_reduced[award_index]
    num_keywords_to_match = award_num_keywords_map[award_index]

    # add word boundary '\b' to prevent grabbing examples like "showing" and "wonder"
    pattern = re.compile(r'\bpresenter|\bpresent', re.IGNORECASE)

    entity_dict = {}
    num = 0
    flag = 0

    if len(award) != num_keywords_to_match:
        flag = 1
        for line in CLEANSED_DATA:
            match = re.findall(pattern, line.lower())
            weight = 20 if any('presenter' in tup for tup in match) or any('presenters' in tup for tup in match) else 1
            num_keywords_matched = len(set(award).intersection(set(line.split())))
            if match and num_keywords_matched >= num_keywords_to_match:
                ratio = round(num_keywords_matched/(num_keywords_to_match+0.0001))
                weight *= ratio

                tags = identify_entities(line)
                for entity in tags.keys():
                    entity_raw = entity
                    entity = entity.strip()
                    if len(entity) > 1:
                        # add more weights for appropriate entity classification
                        if tags[entity_raw] == 'PERSON':
                            weight += 5
                        if tags[entity_raw] == 'PERSON':
                            weight -= 5
                        if entity not in entity_dict:
                            entity_dict[entity] = weight
                        else:
                            entity_dict[entity] += weight
                num += 1
    else:
        for line in CLEANSED_DATA:
            match = re.findall(pattern, line.lower())
            weight = 20 if any('presenter' in tup for tup in match) or any('presenters' in tup for tup in match) else 1
            # if line contains at least number keywords to match and pattern is found
            num_keywords_matched = len(set(award).intersection(set(line.split())))
            if num_keywords_matched == num_keywords_to_match and match:
                ratio = round(num_keywords_matched/(num_keywords_to_match+0.0001))
                weight *= ratio

                tags = identify_entities(line)
                for entity in tags.keys():
                    entity_raw = entity
                    entity = entity.strip()
                    if len(entity) > 1:
                        # add more weights for appropriate entity classification
                        if tags[entity_raw] == 'PERSON':
                            weight += 5
                        if tags[entity_raw] == 'PERSON':
                            weight -= 5
                        if entity not in entity_dict:
                            entity_dict[entity] = weight
                        else:
                            entity_dict[entity] += weight
                num += 1

    # if no results found, recursively reducing num_keywords_to_match
    while(num == 0 or num < 10):
        num_keywords_to_match -= 1
        if num_keywords_to_match == 0:
            break

        # add alternative word for 'tv'
        if 'tv' in award and 'television' not in award:
            award.append('television')
        # add alternative word for 'Motion Picture'
        if 'Motion Picture' in awards[award_index]:
            award.append('movie')
            award.append('motion')
            award.append('picture')

        if flag == 1:
            for line in CLEANSED_DATA:
                match = re.findall(pattern, line.lower())
                weight = 20 if any('presenter' in tup for tup in match) or any('presenters' in tup for tup in match) else 1
                num_keywords_matched = len(set(award).intersection(set(line.split())))
                if match and num_keywords_matched >= num_keywords_to_match:
                    ratio = round(num_keywords_matched/(num_keywords_to_match+0.0001))
                    weight *= ratio

                    tags = identify_entities(line)
                    for entity in tags.keys():
                        entity_raw = entity
                        entity = entity.strip()
                        if len(entity) > 1:
                            # add more weights for appropriate entity classification
                            if tags[entity_raw] == 'PERSON':
                                weight += 5
                            if tags[entity_raw] == 'PERSON':
                                weight -= 5
                            if entity not in entity_dict:
                                entity_dict[entity] = weight
                            else:
                                entity_dict[entity] += weight
                    num += 1
        else:
            for line in CLEANSED_DATA:
                match = re.findall(pattern, line.lower())
                weight = 20 if any('presenter' in tup for tup in match) or any('presenters' in tup for tup in match) else 1
                # if line contains at least number keywords to match and pattern is found
                num_keywords_matched = len(set(award).intersection(set(line.split())))
                if num_keywords_matched == num_keywords_to_match and match:

                    ratio = round(num_keywords_matched/(num_keywords_to_match+0.0001))
                    weight *= ratio

                    tags = identify_entities(line)
                    for entity in tags.keys():
                        entity_raw = entity
                        entity = entity.strip()
                        if len(entity) > 1:
                            # add more weights for appropriate entity classification
                            if tags[entity_raw] == 'PERSON':
                                weight += 5
                            if tags[entity_raw] == 'PERSON':
                                weight -= 5
                            if entity not in entity_dict:
                                entity_dict[entity] = weight
                            else:
                                entity_dict[entity] += weight
                    num += 1
    return entity_dict

def preprocess(year):
    start_time = time.time()
    print('preprocssing...')

    df = pd.read_json(path_or_buf='gg{0}.json'.format(year))
    data = df['text']

    # sample data if necessary
    sample_size = 200000
    if len(df) > sample_size:
        data = data.sample(n=sample_size)

    # clean tweets
    for tweet in data:
        line = remove_retweet_prefix(tweet)
        line = remove_hashtag(line)
        line = remove_at(line)
        line = remove_url(line)
        line = cleanse(line)
        global CLEANSED_DATA
        CLEANSED_DATA.append(line)

    print('total preprocessing time: {0:.2f} seconds'.format(time.time() - start_time))


# the following global variable and functions are adapted from gg_api.py from autograder
OFFICIAL_AWARDS_1315 = ['cecil b. demille award', 'best motion picture - drama', 'best performance by an actress in a motion picture - drama', 'best performance by an actor in a motion picture - drama', 'best motion picture - comedy or musical', 'best performance by an actress in a motion picture - comedy or musical', 'best performance by an actor in a motion picture - comedy or musical', 'best animated feature film', 'best foreign language film', 'best performance by an actress in a supporting role in a motion picture', 'best performance by an actor in a supporting role in a motion picture', 'best director - motion picture', 'best screenplay - motion picture', 'best original score - motion picture', 'best original song - motion picture', 'best television series - drama', 'best performance by an actress in a television series - drama', 'best performance by an actor in a television series - drama', 'best television series - comedy or musical', 'best performance by an actress in a television series - comedy or musical', 'best performance by an actor in a television series - comedy or musical', 'best mini-series or motion picture made for television', 'best performance by an actress in a mini-series or motion picture made for television', 'best performance by an actor in a mini-series or motion picture made for television', 'best performance by an actress in a supporting role in a series, mini-series or motion picture made for television', 'best performance by an actor in a supporting role in a series, mini-series or motion picture made for television']

OFFICIAL_AWARDS_1819 = ['best motion picture - drama', 'best motion picture - musical or comedy', 'best performance by an actress in a motion picture - drama', 'best performance by an actor in a motion picture - drama', 'best performance by an actress in a motion picture - musical or comedy', 'best performance by an actor in a motion picture - musical or comedy', 'best performance by an actress in a supporting role in any motion picture', 'best performance by an actor in a supporting role in any motion picture', 'best director - motion picture', 'best screenplay - motion picture', 'best motion picture - animated', 'best motion picture - foreign language', 'best original score - motion picture', 'best original song - motion picture', 'best television series - drama', 'best television series - musical or comedy', 'best television limited series or motion picture made for television', 'best performance by an actress in a limited series or a motion picture made for television', 'best performance by an actor in a limited series or a motion picture made for television', 'best performance by an actress in a television series - drama', 'best performance by an actor in a television series - drama', 'best performance by an actress in a television series - musical or comedy', 'best performance by an actor in a television series - musical or comedy', 'best performance by an actress in a supporting role in a series, limited series or motion picture made for television', 'best performance by an actor in a supporting role in a series, limited series or motion picture made for television', 'cecil b. demille award']


def get_hosts(year):
    '''Hosts is a list of one or more strings. Do NOT change the name
    of this function or what it returns.'''
    # Your code here
    global PREPROCESSED_FLAG
    if PREPROCESSED_FLAG == 0:
        preprocess(year)
        PREPROCESSED_FLAG = 1

    print('finding hosts...')
    entity_freq_dict = find_host(CLEANSED_DATA)
    top_100 = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:100]
    # remove 'golden globes' from identified host names
    entity_freq_dict = remove_goldeb_globes(top_100, entity_freq_dict)
    top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:20]
    # filter for names
    top_results, entity_freq_dict = filter_names(top_results, entity_freq_dict)
    top_10 = merge_names(top_results, entity_freq_dict)
    HOSTS = [name[0] for name in top_10][:2]
    return HOSTS


def get_awards(year):
    '''Awards is a list of strings. Do NOT change the name
    of this function or what it returns.'''
    # Your code here
    global PREPROCESSED_FLAG
    if PREPROCESSED_FLAG == 0:
        preprocess(year)
        PREPROCESSED_FLAG = 1

    AWARDS = find_awards(CLEANSED_DATA)
    return AWARDS


def get_nominees(year):
    '''Nominees is a dictionary with the hard coded award
    names as keys, and each entry a list of strings. Do NOT change
    the name of this function or what it returns.'''
    # Your code here
    global PREPROCESSED_FLAG
    if PREPROCESSED_FLAG == 0:
        preprocess(year)
        PREPROCESSED_FLAG = 1

    return nominees


def get_winner(year):
    '''Winners is a dictionary with the hard coded award
    names as keys, and each entry containing a single string.
    Do NOT change the name of this function or what it returns.'''
    # Your code here
    global PREPROCESSED_FLAG
    if PREPROCESSED_FLAG == 0:
        preprocess(year)
        PREPROCESSED_FLAG = 1

    if year == '2013' or '2015':
        awards = OFFICIAL_AWARDS_1315
    elif year == '2018' or '2019':
        awards = OFFICIAL_AWARDS_1819

    award_num_keywords_map, awards_reduced = generate_award_num_keywords_map(awards)

    for key in award_num_keywords_map.keys():
        entity_freq_dict = find_award_winner(awards, awards_reduced, key, award_num_keywords_map)
        top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:100]
        # remove 'golden globes' from identified host names
        entity_freq_dict = remove_goldeb_globes(top_results, entity_freq_dict)
        top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:30]
        # filter for names if necessary
        if 'actor' in awards_reduced[key] or 'actress' in awards_reduced[key] or 'director' in awards_reduced[key]:
            top_results, entity_freq_dict = filter_names(top_results, entity_freq_dict)
        top_10 = merge_names(top_results, entity_freq_dict)

        global award_winner_dict
        if len(top_10) != 0:
            award_winner_dict[awards[key].lower()] = top_10[0][0]
        else:
            award_winner_dict[awards[key].lower()] = ''

    winners = award_winner_dict
    # import pprint
    # pprint.pprint(winners, width=160)
    return winners


def get_presenters(year):
    '''Presenters is a dictionary with the hard coded award
    names as keys, and each entry a list of strings. Do NOT change the
    name of this function or what it returns.'''
    # Your code here
    global PREPROCESSED_FLAG
    if PREPROCESSED_FLAG == 0:
        preprocess(year)
        PREPROCESSED_FLAG = 1

    if year == '2013' or '2015':
        awards = OFFICIAL_AWARDS_1315
    elif year == '2018' or '2019':
        awards = OFFICIAL_AWARDS_1819

    award_num_keywords_map, awards_reduced = generate_award_num_keywords_map(awards)

    for key in award_num_keywords_map.keys():
        entity_freq_dict = find_award_presenter(awards, awards_reduced, key, award_num_keywords_map)
        top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:100]
        # remove 'golden globes' from identified host names
        entity_freq_dict = remove_goldeb_globes(top_results, entity_freq_dict)
        top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:30]
        # filter for names if necessary
        top_results, entity_freq_dict = filter_names(top_results, entity_freq_dict)
        top_10 = merge_names(top_results, entity_freq_dict)

        global award_presenters_dict
        if len(top_10) == 0:
            award_presenters_dict[awards[key].lower()] = ''
        elif len(top_10) == 1:
            award_presenters_dict[awards[key].lower()] = top_10[0][0]
        elif len(top_10) > 1:
            award_presenters_dict[awards[key].lower()] = [top_10[0][0], top_10[1][0]]

    presenters = award_presenters_dict
    return presenters


def pre_ceremony():
    '''This function loads/fetches/processes any data your program
    will use, and stores that data in your DB or in a json, csv, or
    plain text file. It is the first thing the TA will run when grading.
    Do NOT change the name of this function or what it returns.'''
    # Your code here
    # install all necessary libraries
    print('installing necessary libraries loading language model used...')
    print('step 1: pip install -r requirements.txt')
    os.system("pip install -r requirements.txt")
    print('step 2: python3 -m spacy download en')
    os.system("python3 -m spacy download en")
    print("Pre-ceremony processing complete.")
    return


# individual task testing
if __name__ == '__main__':
    # get_hosts('2013')
    # get_awards('2013')
    # get_presenters('2013')
    get_winner('2013')
