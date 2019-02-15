import os
import re
import time
import json


from fuzzywuzzy import fuzz
import pandas as pd
import spacy
import nltk
from nltk.corpus import stopwords

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
    # replace everything to ' ' except whitespace, alphanumeric character, apostrophe, hashtag
    return re.sub(r'[^\w\s\'#]', ' ', line)
    # consider keeping '-'


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
                # reward merging if the difference between the first two candidates are not large
                # e[selected_entity_name] += round(e[selected_entity_name]*1/(names.index(selected_entity_name)+1-0.88))
                # if top_results[0][1] < 2*top_results[1][1]:
                #     selected_name_i = names.index(selected_entity_name)
                #     name_i = names.index(name)
                #     if selected_name_i < 4:
                #         if name_i >= 4:
                #             # reward strength is proportional to indices' distance
                #             e[selected_entity_name] += e[name]*abs(selected_name_i - name_i)*1.5
                #         else:
                #             e[selected_entity_name] += e[name]*0.5
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
    # remove words "best", "performance", "language", "role", in", "a", "an", "any", "made", "for", "by", "b.", "award", and all punctuations
    pattern = r'\bbest\b|\bperformance\b|\blanguage\b|\brole\b|\bin\b|\ba\b|\ban\b|\bany\b|\bmade\b|\bfor\b|\bby\b|\bb\b|\baward\b|[^\w\s]'
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


def find_award_winner(awards, award_num_keywords_map, awards_reduced, award_index, stop_words):
    print(award_index)
    print('Predicting for:', awards[award_index])
    award = awards_reduced[award_index]
    print('award name reduced:', award)
    num_keywords_to_match = award_num_keywords_map[award_index]
    print("num keywords to match:", num_keywords_to_match)

    # add word boundary '\b' to prevent grabbing examples like "showing" and "wonder"
    pattern = re.compile(r'\bwin|\bwon\b|\bbest\b|\bcongrat', re.IGNORECASE)

    entity_freq_dict = {}

    num = 0
    flag = 0

    # find target word pattern to match for sure
    target_word = check_target_words(award)
    if target_word:
        target_word_pattern = re.compile(r'\b{0}\b'.format(target_word), re.IGNORECASE)
        print("matching target word '{0}'".format(target_word))
    # else if primary keyword is not found, match for secondary keyword
    elif 'tv' in award:
        target_word_pattern = re.compile(r'\b{0}\b'.format('tv'), re.IGNORECASE)
        print("matching target word 'tv'")
    elif 'screenplay' in award:
        target_word_pattern = re.compile(r'\b{0}\b'.format('screenplay'), re.IGNORECASE)
        print("matching target word 'screenplay'")
    else:
        target_word_pattern = re.compile(r'\b{0}\b'.format(award[0]), re.IGNORECASE)
        print("matching target word '{0}'".format(award[0]))

    for line in CLEANSED_DATA:
        match = re.findall(pattern, line.lower())
        match_target_word = re.findall(target_word_pattern, line.lower())

    # if len(award) != num_keywords_to_match (awards that have 'or' options)
    # and len(award) != 2 (for the case of ['musical', 'comedy']),
    # in addition, if target word in award, target word must be matched
    if len(award) != num_keywords_to_match:
        flag = 1

        # if line contains at least number keywords to match and pattern is found
        num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
        if (match and num_keywords_matched >= num_keywords_to_match) and match_target_word:
            # reward longer match
            weight = 10 if any('win' in tup for tup in match) else 1

            ratio = num_keywords_matched**5
            weight *= ratio

            tags = identify_entities(line)
            for entity in tags.keys():
                entity_raw = entity

                # remove stopwords if any
                entity_split = [w for w in entity.split() if w.lower() not in stop_words]
                if len(entity_split) != 0:
                    entity = ' '.join(entity_split)

                    # add more weights for appropriate entity classification
                    if target_word in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                        weight += 10
                    if target_word not in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                        weight -= 10
                    if entity not in entity_freq_dict:
                        entity_freq_dict[entity] = weight
                    else:
                        entity_freq_dict[entity] += weight
            num += 1

    else:
        for line in CLEANSED_DATA:
            match = re.findall(pattern, line.lower())

            # if line contains at least number keywords to match and pattern is found
            num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
            if match and num_keywords_matched == num_keywords_to_match:
                weight = 10 if any('win' in tup for tup in match) else 1
                weight *= num_keywords_matched


                tags = identify_entities(line)
                for entity in tags.keys():
                    entity_raw = entity

                    # remove stopwords if any
                    entity_split = [w for w in entity.split() if w.lower() not in stop_words]
                    if len(entity_split) != 0:
                        entity = ' '.join(entity_split)

                        # add more weights for appropriate entity classification
                        if target_word in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                            weight += 10
                        if target_word not in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                            weight -= 10
                        if entity not in entity_freq_dict:
                            entity_freq_dict[entity] = weight
                        else:
                            entity_freq_dict[entity] += weight
                num += 1

    # if no results found, recursively add more keywords and reduce num_keywords_to_match
    while(num == 0 or num < 10):
        print('no results found or too few matches!!! add more keywords and reduce num_keywords_to_match!!!')

        num_keywords_to_match -= 1
        print("num keywords to match:", num_keywords_to_match)
        if num_keywords_to_match == 0:
            break

        print('award before:', award)
        # add alternative word for 'Motion Picture'
        if 'motion picture' in awards[award_index]:
            award.append('movie')
        print('expanded award with more keywards:', award)

        if flag == 1:
            if target_word:
                print("matching target word '{0}'".format(target_word))
            for line in CLEANSED_DATA:
                match = re.findall(pattern, line.lower())

                match_target_word = re.findall(target_word_pattern, line.lower())

                # if line contains at least number keywords to match and pattern is found
                num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
                if num_keywords_matched >= num_keywords_to_match and match and match_target_word:

                    weight = 10 if any('win' in tup for tup in match) else 1

                    ratio = num_keywords_matched**5
                    weight *= ratio

                    tags = identify_entities(line)
                    for entity in tags.keys():
                        entity_raw = entity
                        # remove stopwords if any
                        entity_split = [w for w in entity.split() if w.lower() not in stop_words]
                        if len(entity_split) != 0:
                            entity = ' '.join(entity_split)

                            # add more weights for appropriate entity classification
                            if target_word in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                                weight += 10
                            if target_word not in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                                weight -= 10
                            if entity not in entity_freq_dict:
                                entity_freq_dict[entity] = weight
                            else:
                                entity_freq_dict[entity] += weight
                    num += 1
        else:
            for line in CLEANSED_DATA:
                match = re.findall(pattern, line.lower())
                # if line contains at least number keywords to match and pattern is found
                num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
                if num_keywords_matched == num_keywords_to_match and match:

                    weight = 10 if any('win' in tup for tup in match) else 1
                    weight *= num_keywords_matched

                    tags = identify_entities(line)
                    for entity in tags.keys():
                        entity_raw = entity
                        # remove stopwords if any
                        entity_split = [w for w in entity.split() if w.lower() not in stop_words]
                        if len(entity_split) != 0:
                            entity = ' '.join(entity_split)

                            # add more weights for appropriate entity classification
                            if target_word in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                                weight += 10
                            if target_word not in ['actor', 'actress', 'director'] and tags[entity_raw] == 'PERSON':
                                weight -= 10
                            if entity not in entity_freq_dict:
                                entity_freq_dict[entity] = weight
                            else:
                                entity_freq_dict[entity] += weight
                    num += 1
    print('num of matches:', num)
    return entity_freq_dict


def find_award_presenter(awards, awards_reduced, award_index, award_num_keywords_map, stop_words):
    print('Predicting for:', awards[award_index])
    award = awards_reduced[award_index]
    num_keywords_to_match = award_num_keywords_map[award_index]

    # add word boundary '\b' to prevent grabbing examples like "showing" and "wonder"
    pattern = re.compile(r'\bpresenter|\bpresent\b|\bpresenting\b|\bpresentador\b', re.IGNORECASE)

    entity_dict = {}

    num = 0
    flag = 0

    # keep track of the longest match
    max_match = 0
    max_match_entities = []

    # find target word pattern to match for sure
    primary_target_word = check_primary_target_words(award)
    if primary_target_word:
        target_word_pattern = re.compile(r'\b{0}\b'.format(primary_target_word), re.IGNORECASE)
    # else if primary keyword is not found, match for secondary keyword
    elif 'tv' in award:
        target_word_pattern = re.compile(r'\b{0}\b'.format('tv'), re.IGNORECASE)
    else:
        target_word_pattern = re.compile(r'\b{0}\b'.format(award[0]), re.IGNORECASE)

    if len(award) != num_keywords_to_match:
        flag = 1
        for line in CLEANSED_DATA:
            match = re.findall(pattern, line.lower())
            match_target_word = re.findall(target_word_pattern, line.lower())
            weight = 100 if any('presenter' in tup for tup in match) or any('presenting' in tup for tup in match) else 1

            # if line contains at least number keywords to match and pattern is found
            num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
            if match and num_keywords_matched >= num_keywords_to_match and match_target_word:
                ratio = num_keywords_matched**5
                weight *= ratio

                tags = identify_entities(line)

                for entity in tags.keys():
                    entity_raw = entity
                    # remove stopwords if any
                    entity_split = [w for w in entity.split() if w.lower() not in stop_words]
                    if len(entity_split) != 0:
                        entity = ' '.join(entity_split)
                        # add more weights for appropriate entity classification
                        if tags[entity_raw] == 'PERSON':
                            weight += 5
                        if tags[entity_raw] == 'PERSON':
                            weight -= 5
                        if entity not in entity_dict:
                            entity_dict[entity] = weight
                        else:
                            entity_dict[entity] += weight

                # update max_match_entities
                if num_keywords_matched > max_match:
                    max_match = num_keywords_matched
                    max_match_entities = []
                    for entity in tags.keys():
                        max_match_entities.append(entity)
                num += 1

    else:
        for line in CLEANSED_DATA:
            match = re.findall(pattern, line.lower())
            weight = 100 if any('presenter' in tup for tup in match) or any('presenting' in tup for tup in match) else 1

            # if line contains at least number keywords to match and pattern is found
            num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
            if match and num_keywords_matched == num_keywords_to_match:

                ratio = num_keywords_matched**5
                weight *= ratio

                tags = identify_entities(line)

                for entity in tags.keys():
                    entity_raw = entity
                    # remove stopwords if any
                    entity_split = [w for w in entity.split() if w.lower() not in stop_words]
                    if len(entity_split) != 0:
                        entity = ' '.join(entity_split)
                        # add more weights for appropriate entity classification
                        if tags[entity_raw] == 'PERSON':
                            weight += 5
                        if tags[entity_raw] == 'PERSON':
                            weight -= 5
                        if entity not in entity_dict:
                            entity_dict[entity] = weight
                        else:
                            entity_dict[entity] += weight

                # update max_match_entities
                if num_keywords_matched > max_match:
                    max_match = num_keywords_matched
                    max_match_entities = []
                    for entity in tags.keys():
                        max_match_entities.append(entity)
                num += 1

    # if no results found, recursively reducing num_keywords_to_match
    while(num == 0 or num < 10):
        num_keywords_to_match -= 1
        if num_keywords_to_match == 0:
            break

        if len(award) != num_keywords_to_match:
            for line in CLEANSED_DATA:
                match = re.findall(pattern, line.lower())
                match_target_word = re.findall(target_word_pattern, line.lower())

                weight = 100 if any('presenter' in tup for tup in match) or any('presenting' in tup for tup in match) else 1

                # if line contains at least number keywords to match and pattern is foundnum_keywords_matched = len(set(award).intersection(set(line.lower().split())))
                num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
                if match and num_keywords_matched >= num_keywords_to_match and match_target_word:

                    ratio = num_keywords_matched**5
                    weight *= ratio

                    tags = identify_entities(line)
#
                    for entity in tags.keys():
                        entity_raw = entity
                        # remove stopwords if any
                        entity_split = [w for w in entity.split() if w.lower() not in stop_words]
                        if len(entity_split) != 0:
                            entity = ' '.join(entity_split)
                            # add more weights for appropriate entity classification
                            if tags[entity_raw] == 'PERSON':
                                weight += 5
                            if tags[entity_raw] == 'PERSON':
                                weight -= 5
                            if entity not in entity_dict:
                                entity_dict[entity] = weight
                            else:
                                entity_dict[entity] += weight

                    # update max_match_entities
                    if num_keywords_matched > max_match:
                        max_match = num_keywords_matched
                        max_match_entities = []
                        for entity in tags.keys():
                            max_match_entities.append(entity)
                    num += 1
        else:
            for line in CLEANSED_DATA:
                match = re.findall(pattern, line.lower())
                weight = 100 if any('presenter' in tup for tup in match) or any('presenting' in tup for tup in match) else 1

                # if line contains at least number keywords to match and pattern is found
                num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
                if num_keywords_matched == num_keywords_to_match and match:

                    ratio = num_keywords_matched**5
                    weight *= ratio

                    tags = identify_entities(line)

                    for entity in tags.keys():
                        entity_raw = entity
                        # remove stopwords if any
                        entity_split = [w for w in entity.split() if w.lower() not in stop_words]
                        if len(entity_split) != 0:
                            entity = ' '.join(entity_split)
                            # add more weights for appropriate entity classification
                            if tags[entity_raw] == 'PERSON':
                                weight += 5
                            if tags[entity_raw] == 'PERSON':
                                weight -= 5
                            if entity not in entity_dict:
                                entity_dict[entity] = weight
                            else:
                                entity_dict[entity] += weight

                    # update max_match_entities
                    if num_keywords_matched > max_match:
                        max_match = num_keywords_matched
                        max_match_entities = []
                        for entity in tags.keys():
                            max_match_entities.append(entity)
                    num += 1

    return entity_dict


def generate_stopwords(awards):
    awards_words = set()
    for award in awards:
        awards_words |= set(cleanse(award).split())
    stop_words = set(stopwords.words('english'))
    stop_words |= awards_words
    stop_words |= {'tv'}
    stop_words |= {'winner'}
    stop_words |= {'congrats'}
    stop_words |= {'congratulations'}
    stop_words |= {'golden'}
    stop_words |= {'globes'}
    stop_words |= {'rt'}
    stop_words.remove('of')
    # remove possible names from stopwords
    stop_words.remove('don')
    stop_words.remove('will')
    return stop_words


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
    global CLEANSED_DATA
    for tweet in data:
        line = remove_retweet_prefix(tweet)
        line = remove_hashtag(line)
        line = remove_at(line)
        line = remove_url(line)
        line = cleanse(line)
        CLEANSED_DATA.append(line)

    # remove redundancies after processing retweets
    print(len(CLEANSED_DATA))
    CLEANSED_DATA = list(set(CLEANSED_DATA))
    print(len(CLEANSED_DATA))

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

    # generate stopwords, award_num_keywords_map, and awards_reduced
    stop_words = generate_stopwords(awards)
    award_num_keywords_map, awards_reduced = generate_award_num_keywords_map(awards)

    for i, award in enumerate(awards_reduced):
        if 'tv' in award:
            awards_reduced[i].append('television')

    for key in award_num_keywords_map.keys():
        entity_freq_dict = find_award_winner(awards, award_num_keywords_map, awards_reduced, key, stop_words)
        top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:100]
        # remove 'golden globes' from identified host names
        entity_freq_dict = remove_goldeb_globes(top_results, entity_freq_dict)
        top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:30]
        # filter for names if necessary
        if 'actor' in awards_reduced[key] or 'actress' in awards_reduced[key] or 'director' in awards_reduced[key]:
            top_results, entity_freq_dict = filter_names(top_results, entity_freq_dict)
        print('top results:')
        print(top_results)
        print('\ntop results after merging:')
        # top_10 = merge_names(top_results, entity_freq_dict)
        top_10 = top_results[:10]
        print(top_10)
        print()

        global award_winner_dict
        if len(top_10) != 0:
            award_winner_dict[awards[key].lower()] = top_10[0][0]
        else:
            award_winner_dict[awards[key].lower()] = ''

    winners = award_winner_dict

    import pprint
    pprint.pprint(winners)
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

    # generate stopwords, award_num_keywords_map, and awards_reduced
    stop_words = generate_stopwords(awards)
    award_num_keywords_map, awards_reduced = generate_award_num_keywords_map(awards)

    for key in award_num_keywords_map.keys():
        entity_freq_dict = find_award_presenter(awards, awards_reduced, key, award_num_keywords_map, stop_words)
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
    print(presenters)
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
    nltk.download('stopwords')
    return


# individual task testing
if __name__ == '__main__':
    # get_hosts('2013')
    # get_awards('2013')
    # get_presenters('2013')
    get_winner('2013')
