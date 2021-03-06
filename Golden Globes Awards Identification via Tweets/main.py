import os
import re
import time
import json
import pickle


import nltk
from nltk.corpus import stopwords
import spacy
import pandas as pd
from fuzzywuzzy import fuzz
from textblob import TextBlob
import gender_guesser.detector as gender


nlp = spacy.load('en')


retweets_freq_dict = {}
hashtag_freq_dict = {}
at_freq_dict = {}


# global variables to be later updated and read for autograder
CLEANSED_DATA = []
PREPROCESSED_FLAG = 0
HOSTS = []
award_winner_dict = {}
award_presenters_dict = {}
award_nominees_dict = {}


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
    # replace everything to ' ' except whitespace, alphanumeric character, apostrophe, hashtag, and period
    return re.sub(r'[^\w\s\'#.]', ' ', line)
    # consider keeping '-'


def identify_entities(text, stop_words):
    tags = {}
    for ent in nlp(text).ents:
        entity = ent.text.strip()
        if entity not in tags and len(entity) > 1:
            # remove stopwords
            entity_split = [w for w in entity.split() if w.lower() not in stop_words]
            if len(entity_split) != 0:
                entity = ' '.join(entity_split)
                # if entity is a single word that is 'the' or is a single character
                if (len(entity.split()) == 1 and entity.lower() == 'the') or len(entity) == 1:
                    pass
                else:
                    tags[entity]=[ent.label_]
    return tags


def find_host(CLEANSED_DATA, awards, year):
    stop_words = generate_stopwords(awards, year)
    pattern = re.compile(r'\bhost')
    entity_freq_dict = {}

    for line in CLEANSED_DATA:
        match = re.search(pattern, line.lower())
        if match:
            for entity in identify_entities(line, stop_words).keys():
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
def filter_people_names(pair_list, entity_freq_dict):
    filtered_results = []
    for pair in pair_list:
        string = ''.join(pair[0].split())
        if not all(char.islower() for char in string) and not any(char.isdigit() for char in string):
            filtered_results.append(pair)
        else:
            if pair[0] in entity_freq_dict:
                del entity_freq_dict[pair[0]]
    return filtered_results, entity_freq_dict


def filter_category_names(pair_list, entity_freq_dict):
    try:
        with open('people_names.pickle', 'rb') as file:
            people_names = pickle.load(file)

        if len(people_names) > 0:
            filtered_pair_list = []
            for pair in pair_list:
                if pair[0] in people_names and pair[0] in entity_freq_dict:
                    del entity_freq_dict[pair[0]]
                else:
                    filtered_pair_list.append(pair)
            return filtered_pair_list, entity_freq_dict
    except:
        print("'people_names.pkl' is not found...")
        print("make sure you have run 'pre_ceremony()' before running tasks")
        return pair_list, entity_freq_dict


def merge_names(top_results, entity_freq_dict, top_num = 10):
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
            find = 0
            # check if element of a new cluster is already added to a cluster
            for existing_cluster in names_clusters:
                for element in cluster:
                    if element in existing_cluster:
                        find += 1
            if find == 0:
                names_clusters.append(cluster)

    # merge names clusters
    # ['Amy Poehler', 'Amy', 'Amy Poelher']
    # ['Tina', 'Tina Fey']

    # weighted frequency of an entity is defined by its frequency multiplied by its string length
    def weighted_freq(element):
        return entity_freq_dict[element] * len(element)

    e = entity_freq_dict.copy()
    for cluster in names_clusters:
        # select the entity name with highest weighted frequency
        selected_entity_name = max(cluster, key=weighted_freq)
        cluster.remove(selected_entity_name)
        # for names to be merged to the selected entity name
        for name in cluster:
            # if not deleted in previous cases, cumulate frequencies to the selected entity
            if name in e and selected_entity_name in e:
                e[selected_entity_name] += e[name]
                del e[name]

    top_10 = sorted(e.items(), key=lambda pair: pair[1], reverse=True)[:top_num]
    return top_10


# the functions of finding awards start
def find_awards(year):
    # read data
    df = pd.read_json(path_or_buf='gg' + year + '.json')
    rawdata = df['text']
    # sample data if necessary
    sample_size = 200000
    if len(df) > sample_size:
        rawdata = rawdata.sample(n=sample_size)
    # clean tweets
    data = []
    for tweet in rawdata:
        line = remove_hashtag(tweet)
        line = remove_at(line)
        line = remove_url(line)
        line = re.sub(r'[^\w\s\'#@]', ' ', line)
        data.append(line)

    res = []
    awards = {}
    removelist = []
    endlist = get_endList(year)

    for item in data:
        line = item.lower().split()
        for endword in endlist:
            if 'best' in line and endword in line:
                start = line.index('best')
                end = line.index(endword)
                if start < end:
                    line2 = ['television' if x == 'tv' else x for x in line]
                    key = " ".join(line2[start:end + 1])
                    if key not in awards:
                        awards[key] = 1
                    else:
                        awards[key] += 1

    for item in awards:
        if awards.get(item) > 60:
            line = item
            if len(line.split()) > 3:
                res.append(item)


    for i in range(0, len(res) - 1):
        for j in range(i + 1, len(res)):
            if string_match(res[i], res[j]):
                if len(res[i]) > len(res[j]):
                    removelist.append(res[j])
                else:
                    removelist.append(res[i])

    for item in removelist:
        if item in res:
            res.remove(item)

    for i in range(0,len(res)):
        if 'comedy'in res[i] and 'musical' not in res[i]:
            res[i]=res[i].replace('comedy','comedy or musical')
        elif 'musical'in res[i] and 'comedy' not in res[i]:
            res[i]=res[i].replace('musical','comedy or musical')
        else:
            continue
            
    print(res)
    return res[0:30]


def get_endList(year):
    if year in ['2013', '2015']:
        return ['picture', 'television', 'drama', 'film', 'musical']

    return ['picture', 'television', 'drama', 'film', 'comedy']

def string_match(a,b):
    if len(a) > len(b):
        if b in a:
            return True
        return False
    if a in b:
        return True
    return False
# the functions of finding awards end

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

    # find target word pattern to match for sure
    target_word = check_target_words(award)
    if target_word:
        target_word_pattern = re.compile(r'\b{0}\b'.format(target_word), re.IGNORECASE)
        print("matching target word '{0}'".format(target_word))
    # else if 'tv' in award, pick 'tv' as a target word
    elif 'tv' in award:
        target_word_pattern = re.compile(r'\b{0}\b'.format('tv'), re.IGNORECASE)
        print("matching target word 'tv'")
    # else pick the first word in award as target word
    else:
        target_word_pattern = re.compile(r'\b{0}\b'.format(award[0]), re.IGNORECASE)
        print("matching target word '{0}'".format(award[0]))

    # if len(award) != num_keywords_to_match (awards that have 'or' options)
    # target word must be matched
    if len(award) != num_keywords_to_match:
        for line in CLEANSED_DATA:
            match = re.findall(pattern, line.lower())
            match_target_word = re.findall(target_word_pattern, line.lower())

            # if line contains at least number keywords to match and pattern is found
            num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
            if (match and num_keywords_matched >= num_keywords_to_match) and match_target_word:
                weight = 10 if any('win' in tup for tup in match) else 1
                # reward longer match
                weight *= num_keywords_matched**5

                tags = identify_entities(line, stop_words)
                for entity in tags.keys():
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

                tags = identify_entities(line, stop_words)
                for entity in tags.keys():
                    if entity not in entity_freq_dict:
                        entity_freq_dict[entity] = weight
                    else:
                        entity_freq_dict[entity] += weight
                num += 1

    # if no results found, recursively add more keywords and reduce num_keywords_to_match
    while(num == 0 or num < 10):
        print('no results found or too few matches! reduce num_keywords_to_match!')
        num_keywords_to_match -= 1
        print("num keywords to match:", num_keywords_to_match)
        if num_keywords_to_match == 0:
            break

        if len(award) != num_keywords_to_match:
            if target_word:
                print("matching target word '{0}'".format(target_word))
            for line in CLEANSED_DATA:
                match = re.findall(pattern, line.lower())
                match_target_word = re.findall(target_word_pattern, line.lower())

                # if line contains at least number keywords to match and pattern is found
                num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
                if num_keywords_matched >= num_keywords_to_match and match and match_target_word:
                    weight = 10 if any('win' in tup for tup in match) else 1
                    # reward longer match
                    weight *= num_keywords_matched**5

                    tags = identify_entities(line, stop_words)
                    for entity in tags.keys():
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

                    tags = identify_entities(line, stop_words)
                    for entity in tags.keys():
                        if entity not in entity_freq_dict:
                            entity_freq_dict[entity] = weight
                        else:
                            entity_freq_dict[entity] += weight
                    num += 1
    print('num of matches:', num)
    return entity_freq_dict


def find_award_presenter(awards, awards_reduced, award_index, award_num_keywords_map, stop_words):
    print()
    print(award_index)
    print('Predicting for:', awards[award_index])
    award = awards_reduced[award_index]
    num_keywords_to_match = award_num_keywords_map[award_index]

    # add word boundary '\b' to prevent grabbing examples like "showing" and "wonder"
    pattern = re.compile(r'\bpresenter|\bpresent\b|\bpresenting\b|\bpresentador\b', re.IGNORECASE)
    entity_freq_dict = {}
    num = 0

    # find target word pattern to match for sure
    target_words = check_target_words(award)
    if target_words:
        target_word_pattern = re.compile(r'\b{0}\b'.format(target_words), re.IGNORECASE)
    # else if primary keyword is not found, match for secondary keyword
    elif 'tv' in award:
        target_word_pattern = re.compile(r'\b{0}\b'.format('tv'), re.IGNORECASE)
    else:
        target_word_pattern = re.compile(r'\b{0}\b'.format(award[0]), re.IGNORECASE)

    if len(award) != num_keywords_to_match:
        for line in CLEANSED_DATA:
            match = re.findall(pattern, line.lower())
            match_target_word = re.findall(target_word_pattern, line.lower())
            weight = 100 if any('presenter' in tup for tup in match) or any('presenting' in tup for tup in match) else 1

            # if line contains at least number keywords to match and pattern is found
            num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
            if match and num_keywords_matched >= num_keywords_to_match and match_target_word:
                weight *= num_keywords_matched**5

                tags = identify_entities(line, stop_words)
                for entity in tags.keys():
                    if entity not in entity_freq_dict:
                        entity_freq_dict[entity] = weight
                    else:
                        entity_freq_dict[entity] += weight
                num += 1
    else:
        for line in CLEANSED_DATA:
            match = re.findall(pattern, line.lower())
            weight = 100 if any('presenter' in tup for tup in match) or any('presenting' in tup for tup in match) else 1

            # if line contains at least number keywords to match and pattern is found
            num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
            if match and num_keywords_matched == num_keywords_to_match:
                weight *= num_keywords_matched

                tags = identify_entities(line, stop_words)
                for entity in tags.keys():
                    if entity not in entity_freq_dict:
                        entity_freq_dict[entity] = weight
                    else:
                        entity_freq_dict[entity] += weight
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
                    weight *= num_keywords_matched**5

                    tags = identify_entities(line, stop_words)
                    for entity in tags.keys():
                        if entity not in entity_freq_dict:
                            entity_freq_dict[entity] = weight
                        else:
                            entity_freq_dict[entity] += weight
                    num += 1
        else:
            for line in CLEANSED_DATA:
                match = re.findall(pattern, line.lower())
                weight = 100 if any('presenter' in tup for tup in match) or any('presenting' in tup for tup in match) else 1

                # if line contains at least number keywords to match and pattern is found
                num_keywords_matched = len(set(award).intersection(set(line.lower().split())))
                if num_keywords_matched == num_keywords_to_match and match:
                    weight = num_keywords_matched

                    tags = identify_entities(line, stop_words)
                    for entity in tags.keys():
                        if entity not in entity_freq_dict:
                            entity_freq_dict[entity] = weight
                        else:
                            entity_freq_dict[entity] += weight
                    num += 1
    return entity_freq_dict


def generate_stopwords(awards, year):
    stop_words = set()

    awards_words = set()
    for award in awards:
        awards_words |= set(cleanse(award).split())

    stop_words |= awards_words
    stop_words |= {'award'}
    stop_words |= {'awards'}
    stop_words |= {'tv'}
    stop_words |= {'movie'}
    stop_words |= {'movies'}
    stop_words |= {'win'}
    stop_words |= {'wins'}
    stop_words |= {'winner'}
    stop_words |= {'winners'}
    stop_words |= {'congrats'}
    stop_words |= {'congratulations'}
    stop_words |= {'golden'}
    stop_words |= {'globe'}
    stop_words |= {'globes'}
    stop_words |= {'present'}
    stop_words |= {'rt'}
    stop_words |= {'{0}'.format(year)}
    return stop_words


def preprocess(year):
    start_time = time.time()
    print('preprocssing...')
    df = pd.read_json(path_or_buf='gg{0}.json'.format(year))

    # sample data if necessary
    sample_size = 200000
    if len(df['text']) > sample_size:
        data = df['text'].sample(n=sample_size)
    else:
        data = df['text']

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
    CLEANSED_DATA = list(set(CLEANSED_DATA))
    print('total preprocessing time: {0:.2f} seconds'.format(time.time() - start_time))


def get_film_name():
    try:
        with open('film_names.json') as file:
            name_entites = json.load(file)
        file.closed
        return name_entites
    except:
        print("'film_names.json' is not found...")
        print("make sure you have run 'pre_ceremony()' before running tasks")
        return {}


def find_person_nominees(award, data, pattern, award_keywords, target_word_pattern, num_keywords_to_match_min, nominee_dict, stop_words, recurse = False):
    if num_keywords_to_match_min < 0:
        return nominee_dict

    if recurse:
        if 'tv' in award_keywords and 'television' not in award_keywords:
            award_keywords.append('television')
            # add alternative word for 'Motion Picture'
        if 'Motion Picture' in award and 'motion' not in award_keywords and 'movie' not in award_keywords and 'picture' not in award_keywords:
            award_keywords.append('movie')
            award_keywords.append('motion')
            award_keywords.append('picture')
        print('expanded award with more keywards', award_keywords)

    gender_detector = gender.Detector()
    if len(nominee_dict) <= 10:
        for line in data:
            match = re.findall(pattern, line.lower())
            match_target_word = re.findall(target_word_pattern, line.lower()) if target_word_pattern is not None else ['']
            num_keywords_matched = len(set(award_keywords).intersection(set(line.split())))

            # if match:
            #     try:
            #         with open('people_names.pickle', 'rb') as file:
            #             people_names = pickle.load(file)
            #         file.close()
            #     except:
            #         people_names = []
            #
            #     for name in people_names:
            #         if name in line:
            #             if name in nominee_dict:
            #                 nominee_dict[name] += 1
            #             else:
            #                 nominee_dict[name] = 1


            if num_keywords_matched >= num_keywords_to_match_min and (match_target_word or recurse) and match:
                weight = 5 if any('nominee' or 'nominat' or 'lost' or 'lose' in tup for tup in match) else 1
                weight *= num_keywords_matched

                tags = identify_entities(line, stop_words)

                for entity in tags.keys():
                    entity_raw = entity
                    entity = entity.strip()
                    entity = remove_apostrophe(entity)
                    entity_split = [w for w in entity.split() if w.lower() not in stop_words]
                    if len(entity_split) != 0:
                        entity = ' '.join(entity_split)
                    if len(entity) > 3:
                        # add more weights for appropriate entity classification
                        if tags[entity_raw] == ['PERSON']:
                            if 'actress' in award_keywords and gender_detector.get_gender(
                                    entity.split()[0]) == 'female':
                                weight += 10
                            elif 'actor' in award_keywords and gender_detector.get_gender(entity.split()[0]) == 'male':
                                weight += 10
                            weight += 5
                        else:
                            weight -= 10

                        try:
                            with open('people_names.pickle', 'rb') as file:
                                people_names = pickle.load(file)
                            file.close()
                        except:
                            people_names = []

                        for name in people_names:
                            if name in line:
                                if name in nominee_dict:
                                    nominee_dict[name] += weight
                                else:
                                    nominee_dict[name] = weight

                        if entity not in nominee_dict:
                            nominee_dict[entity] = weight
                        else:
                            nominee_dict[entity] += weight
    if len(nominee_dict) <= 10:
        nominee_dict = find_person_nominees(award, data, pattern, award_keywords, target_word_pattern,
                                            num_keywords_to_match_min-1, nominee_dict, stop_words, True)
    return nominee_dict


def find_other_nominees(year, award, data, pattern, award_keywords, target_word_pattern, num_keywords_to_match_min, nominee_dict, category, stop_words, recurse = False):
    if num_keywords_to_match_min <= 0:
        return nominee_dict

    if recurse:
        if 'tv' in award_keywords and 'television' not in award_keywords:
            award_keywords.append('television')
            # add alternative word for 'Motion Picture'
        if 'Motion Picture' in award and 'motion' not in award_keywords and 'movie' not in award_keywords and 'picture' not in award_keywords:
            award_keywords.append('movie')
            award_keywords.append('motion')
            award_keywords.append('picture')
        print('expanded award with more keywards', award_keywords)

    possible_film_names = []
    if category != 'song':
        # use film name data to get entity
        # get films in the last two years
        year = str(int(year) - 1)
        if year in FILM_NAMES:
            possible_film_names += FILM_NAMES[year]

        year = str(int(year) - 1)
        if year in FILM_NAMES:
            possible_film_names += FILM_NAMES[year]

    if len(nominee_dict) <= 10:
        for line in data:
            match = re.findall(pattern, line.lower())
            match_target_word = re.findall(target_word_pattern, line.lower()) if target_word_pattern is not None else ['']
            num_keywords_matched = len(set(award_keywords).intersection(set(line.split())))

            # if category != 'song' and match:
            #     # use film name data to get entity
            #     for film_name in possible_film_names:
            #         if film_name.lower() in line.lower() and len(film_name) > 3:
            #             if film_name not in nominee_dict:
            #                 nominee_dict[film_name] = 1
            #             else:
            #                 nominee_dict[film_name] += 1

            if num_keywords_matched >= num_keywords_to_match_min and (match_target_word or recurse) and match:
                weight = 1
                if any('nominee' or 'nominat' or 'lost' or 'lose' in tup for tup in match):
                    weight = 3
                weight *= num_keywords_matched

                tags = identify_entities(line, stop_words)

                for entity in tags.keys():
                    entity_raw = entity
                    entity = entity.strip()
                    entity = remove_apostrophe(entity)
                    if len(entity) > 3:
                        if category != 'song':
                            # use film name data to get entity
                            for film_name in possible_film_names:
                                if (film_name.lower() in line.lower()) and len(film_name) > 3:
                                    # print('find film:', film_name)
                                    if film_name not in nominee_dict:
                                        nominee_dict[film_name] = weight
                                    else:
                                        nominee_dict[film_name] += weight
                        if entity not in nominee_dict:
                            nominee_dict[entity] = weight
                        else:
                            nominee_dict[entity] += weight
    if len(nominee_dict) <= 10:
        nominee_dict = find_other_nominees(year, award, data, pattern, award_keywords, target_word_pattern, num_keywords_to_match_min-1, nominee_dict, category, stop_words, True)
    return nominee_dict


def find_nominees(data, award, year, stop_words):
    # no nominee for cecil b. demille award
    if award == 'cecil b. demille award':
        return []

    nominee_dict = {}

    # print(name_entites['song'])

    # keywords
    pattern = re.compile("(\bwin)|(\bwon\b)|(\blost\b)|(\blose\b)|(nominat)|(nominee)", re.IGNORECASE)
    award_keywords = reduce(award)
    if '-' in award_keywords:
        award_keywords.remove('-')
    print("keywords:", award_keywords)
    words_to_remove = ['Drama', 'Oscar', 'RT', 'best', 'ben', 'amy', 'Congrats', 'won', 'win', 'Congratulation',
                       'Nominee', 'Bill Clinton', 'lov', 'Anne Hathaway']
    words_to_remove = words_to_remove + award_keywords

    num_keywords_to_match_min = 1 if len(award_keywords) == 1 else round(len(award_keywords) * 0.7)
    target_word = check_target_words(award_keywords)
    print('target words:', target_word)

    # get entity names
    category = ''
    if len({'actor', 'actress', 'director'}.intersection(set(award.split()))) > 0:
        category = 'name'
    elif len({'song'}.intersection(set(award_keywords))) > 0:
        category = 'song'
    elif len({'show', 'tv', 'television', 'series'}.intersection(set(award.split()))) > 0:
        category = 'tv'
    elif len({'motion', 'picture', 'film', 'movie'}.intersection(set(award.split()))) > 0:
        category = 'film'

    print('category:', category)
    target_word_pattern = None

    film_names = get_film_name()
    global FILM_NAMES
    FILM_NAMES = film_names

    # if len(award_keywords) != num_keywords_to_match and target_word:
    # flag = 1
    # find target word pattern to match for sure
    primary_target_word = check_primary_target_words(award_keywords)
    if primary_target_word:
        target_word_pattern = re.compile(r'\b{0}\b'.format(primary_target_word), re.IGNORECASE)
        print("matching target word '{0}'".format(target_word))
    # else if primary keyword is not found, match for secondary keyword
    elif 'tv' in award_keywords:
        target_word_pattern = re.compile(r'\b{0}\b'.format('tv'), re.IGNORECASE)
        print("matching target word 'tv'")

    if category == 'name':
        nominee_dict = find_person_nominees(award, data, pattern, award_keywords, target_word_pattern, num_keywords_to_match_min,
                                                           {}, stop_words, False)
    else:
        nominee_dict = find_other_nominees(year, award, data, pattern, award_keywords, target_word_pattern, num_keywords_to_match_min, nominee_dict, category, stop_words, False)

    # remove unwanted words
    for word in words_to_remove:
        for name in list(nominee_dict.keys()):
            if re.search(word.lower(), name.lower()) or re.search(name.lower(), word.lower()) \
                    or fuzz.ratio(name.lower(), word.lower()) > 70 or len(name) <= 3:
                del nominee_dict[name]

    # remove 'golden globes' from identified host names
    top_results = sorted(nominee_dict.items(), key=lambda pair: pair[1], reverse=True)
    nominee_dict = remove_goldeb_globes(top_results, nominee_dict)

    top_results = sorted(nominee_dict.items(), key=lambda pair: pair[1], reverse=True)
    print('top results:')
    print(top_results)
    # print('top results after merging:')
    if category == 'name':
        top_results, nominee_dict = filter_people_names(top_results, nominee_dict)
        top_10 = merge_names(top_results, nominee_dict)
    else:
        top_results, nominee_dict = filter_category_names(top_results, nominee_dict)
        top_results = sorted(nominee_dict.items(), key=lambda pair: pair[1], reverse=True)
        top_10 = merge_names(top_results, nominee_dict)

    # remove winner from name list
    try:
        with open('winners_{0}.pickle'.format(year), 'rb') as file:
            global award_winner_dict
            award_winner_dict = pickle.load(file)
    except:
        get_winner(year)
    winner = award_winner_dict[award]
    winner = winner.lower()
    print("winner:", winner)
    for n in top_10[:5]:
        name = n[0]
        if re.search(winner, name.lower()) or fuzz.ratio(name.lower(), winner) > 90:
            top_10.remove(n)
    res = [k[0] for k in top_10]

    return res[0:4]


def identify_entities_tag(text, stop_words):
    tags = {}
    for ent in nlp(text):
        entity = ent.text.strip()
        if entity not in tags and len(entity) > 1:
            # remove stopwords
            entity_split = [w for w in entity.split() if w.lower() not in stop_words]
            if len(entity_split) != 0:
                entity = ' '.join(entity_split)
                if (len(entity.split()) == 1 and entity.lower() == 'the') or len(entity) == 1:
                    pass
                else:
                    tags[entity]=[ent.tag_]
    return tags


def find_sentiments(subject, stop_words):
    pattern = re.compile(r'\b{0}\b'.format(subject), re.IGNORECASE)
    num = 0
    sentiment_freq_dict = {}

    for line in CLEANSED_DATA:
        match = re.search(pattern, line.lower())
        if match:
            tags = identify_entities_tag(line, stop_words)
            for entity in tags.keys():
                if tags[entity][0] == 'JJ':
                    if entity not in sentiment_freq_dict:
                        sentiment_freq_dict[entity] = 1
                    else:
                        sentiment_freq_dict[entity] += 1
            num += 1
            if num == 500:
                break

    top_sentiments = sorted(sentiment_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:3]
    top_sentiments = [pair[0] for pair in top_sentiments]
    return top_sentiments


def sentiment_analysis(year):
    if year == '2013' or '2015':
        awards = OFFICIAL_AWARDS_1315
    elif year == '2018' or '2019':
        awards = OFFICIAL_AWARDS_1819

    stop_words = generate_stopwords(awards, year)
    # make sure names are not used as sentiments
    for name in HOSTS:
        for name_split in name.lower().split():
            stop_words |= {name_split}
    for name in award_winner_dict.values():
        for name_split in name.lower().split():
            stop_words |= {name_split}
    for list in award_presenters_dict.values():
        for name in list:
            for name_split in name.lower().split():
                stop_words |= {name_split}
    for list in award_nominees_dict.values():
        for name in list:
            for name_split in name.lower().split():
                stop_words |= {name_split}
    stop_words |= {'para'}

    print('hosts:', HOSTS)
    for host in HOSTS:
        print('most common sentiment used to:', host)
        print(find_sentiments(host, stop_words))
    print()

    for award in awards:
        print('award:', award)

        winner = award_winner_dict[award]
        print('winner:', winner)
        print('most common sentiment used:')
        print(find_sentiments(winner, stop_words))
        print()

        presenters = award_presenters_dict[award]
        print('presenter(s):', presenters)
        for presenter in presenters:
            print('most common sentiment used to:', presenter)
            print(find_sentiments(presenter, stop_words))
        print()

        nominees = award_nominees_dict[award]
        print('nominees:', nominees)
        for nominee in nominees:
            print('most common sentiment used to:', nominee)
            print(find_sentiments(nominee, stop_words))
        print()


def output_reesults(year):
    try:
        with open('hosts_{0}.pickle'.format(year), 'rb') as file:
            global HOSTS
            HOSTS = pickle.load(file)
    except:
        get_hosts(year)

    try:
        with open('winners_{0}.pickle'.format(year), 'rb') as file:
            global award_winner_dict
            award_winner_dict = pickle.load(file)
    except:
        get_winner(year)

    try:
        with open('presenters_{0}.pickle'.format(year), 'rb') as file:
            global award_presenters_dict
            award_presenters_dict = pickle.load(file)
    except:
        get_presenters(year)

    try:
        with open('nominees_{0}.pickle'.format(year), 'rb') as file:
            global award_nominees_dict
            award_nominees_dict = pickle.load(file)
    except:
        get_nominees(year)

    if year == '2013' or '2015':
        awards = OFFICIAL_AWARDS_1315
    elif year == '2018' or '2019':
        awards = OFFICIAL_AWARDS_1819

    print('Golden Globes {0} Host(s) and Awards Identification via Tweets'.format(year))
    print('hosts:', HOSTS)

    for award in awards:
        print('\naward:', award)
        presenters = award_presenters_dict[award]
        print('presenter(s):', presenters)
        winner = award_winner_dict[award]
        print('winner:', winner)
        nominees = award_nominees_dict[award]
        print('nominees:', nominees)

    print('\nJSON format:')
    d = {}
    d['host'] = HOSTS
    for award in awards:
        a = {}
        a['presenters'] = award_presenters_dict[award]
        a['nominees'] = award_nominees_dict[award]
        a['winner'] = award_winner_dict[award]
        d[award] = a
    print(d)

    # perform additional analyses
    additional_analysis(year)


def get_polarity(line):
    blob = TextBlob(line)
    for sentence in blob.sentences:
        return float(sentence.sentiment.polarity)


def red_carpet_analysis(year):
    pattern = re.compile("(dress)|(wear)|(outfit)|(suit)|(cloth)", re.IGNORECASE)
    neg_dict = {}
    pos_dict = {}

    for line in CLEANSED_DATA:
        match = pattern.search(line)

        if match:
            p = get_polarity(line)
            doc = nlp(line)

            for ent in doc.ents:
                if ent.label_ == 'PERSON':
                    name = ent.text.strip()
                    name = remove_apostrophe(name)
                    # not add to list if the entity is null or golden globe related
                    if p is None or name == '' or fuzz.ratio(name.lower(), 'golden globes') > 60:
                        continue
                    if p < -0.1:
                        if name in neg_dict:
                            neg_dict[name] += -1 * p
                        else:
                            neg_dict[name] = -1 * p
                    if p > 0.1:
                        if name in pos_dict:
                            pos_dict[name] += p
                        else:
                            pos_dict[name] = p

    # get rid of names that are too long or too short
    for name in list(pos_dict.keys()):
        if len(name) < 5 or len(name) > 17:
            del pos_dict[name]

    for name in list(neg_dict.keys()):
        if len(name) < 5 or len(name) > 17:
            del neg_dict[name]

    def get_sorted_names(nominees, f):
        sorted_nominees = sorted(nominees.items(), key=lambda e: e[1], reverse=f)
        names = [pair[0] for pair in sorted_nominees]
        return names

    # print(sorted(pos_dict.items(), key=lambda e: e[1], reverse=True))
    sorted_pos = merge_names(sorted(pos_dict.items(), key=lambda e: e[1], reverse=True), pos_dict, 500)
    sorted_neg = merge_names(sorted(neg_dict.items(), key=lambda e: e[1], reverse=True), neg_dict, 500)

    sorted_pos = [k[0] for k in sorted_pos]
    sorted_neg = [k[0] for k in sorted_neg]

    print("\nTop five best dressed:")
    print(sorted_pos[:5])
    print("\nTop five worst dressed:")
    print(sorted_neg[:5])


    contro_dict = {}
    for name in sorted_pos:
        if name in sorted_neg:
            if name in contro_dict:
                contro_dict[name] += sorted_neg.index(name) + sorted_pos.index(name)
            else:
                contro_dict[name] = sorted_neg.index(name) + sorted_pos.index(name)

    contro_dict = get_sorted_names(contro_dict, False)
    print("\n\nTop five most controversial dressed:")
    print(contro_dict[:5])


# the functions of finding humor people and jokes start
humor_keywords = ['haha', 'lol', 'hh', '233', 'funny', 'joke', 'hilarious', 'comedian', 'best joke', 'hysterical']


def isHumor(text):
    for x in humor_keywords:
        if text.find(x) != -1:
            return True
    return False


def find_humor(CLEANSED_DATA, awards, year):
    stop_words = generate_stopwords(awards, year)
    entity_freq_dict = {}

    for line in CLEANSED_DATA:
        match = isHumor(line)
        if match:
            for entity in identify_entities(line, stop_words).keys():
                if entity not in entity_freq_dict:
                    entity_freq_dict[entity] = 1
                else:
                    entity_freq_dict[entity] += 1
    return entity_freq_dict,stop_words


def get_joke(CLEANSED_DATA,stop_words):
    humordata = {}
    jokes = []
    k = 10
    index = 1
    sign = 0
    temp_joke = []

    for item in CLEANSED_DATA:
        line = item.lower()
        for key in humor_keywords:
            if key in line:
                tokens = [w for w in line.split() if not w in stop_words]
                for joke in nltk.ngrams(tokens, k):
                    if joke in humordata:
                        humordata[joke] += 1
                    else:
                        humordata[joke] = 1
    Dict = sorted(humordata.items(), key=lambda entry: entry[1], reverse=True)

    for i in range (0, len(Dict) - 1):
        if sign == 0:
            index = 1
            if len(temp_joke) != 0:
                joke_soace = ''
                for item in temp_joke:
                    joke_soace += item + ' '
                jokes.append(joke_soace)
            temp_joke = []
        if sign == 1:
            index = 0
        if index == 1:
            for key in Dict[i][0]:
                temp_joke.append(key)
            sign = 1
            index = 0
        for j in range (1, k):
            if Dict[i][0][j] != Dict[i + 1][0][j - 1] or Dict[i + 1][1] < 5:
                sign = 0
        if sign == 1:
             temp_joke.append(Dict[i + 1][0][k - 1])
    return jokes[0: 5]


def get_humor(year):
    global PREPROCESSED_FLAG
    if PREPROCESSED_FLAG == 0:
        preprocess(year)
        PREPROCESSED_FLAG = 1

    if year == '2013' or '2015':
        awards = OFFICIAL_AWARDS_1315
    elif year == '2018' or '2019':
        awards = OFFICIAL_AWARDS_1819

    entity_freq_dict, stop_words = find_humor(CLEANSED_DATA, awards, year)
    top_100 = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:100]
    # remove 'golden globes' from identified names
    entity_freq_dict = remove_goldeb_globes(top_100, entity_freq_dict)
    top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:20]
    # filter for names
    top_results, entity_freq_dict = filter_people_names(top_results, entity_freq_dict)
    top_10 = merge_names(top_results, entity_freq_dict)
    HUMORS = [name[0] for name in top_10][:2]

    JOKES = get_joke(CLEANSED_DATA, stop_words)
    print('Best jokes in ' + year + ':')
    for item in JOKES:
        print(item)
    print('\nBest jokers in ' + year + ':')
    print(HUMORS)
    return HUMORS, JOKES
# the functions of finding humor people and jokes end

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

    if year == '2013' or '2015':
        awards = OFFICIAL_AWARDS_1315
    elif year == '2018' or '2019':
        awards = OFFICIAL_AWARDS_1819

    entity_freq_dict = find_host(CLEANSED_DATA, awards, year)
    top_100 = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:100]
    # remove 'golden globes' from identified host names
    entity_freq_dict = remove_goldeb_globes(top_100, entity_freq_dict)
    top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:20]
    # filter for names
    top_results, entity_freq_dict = filter_people_names(top_results, entity_freq_dict)
    top_10 = merge_names(top_results, entity_freq_dict)

    global HOSTS
    HOSTS = [name[0] for name in top_10][:2]

    with open('hosts_{0}.pickle'.format(year), 'wb') as file:
        pickle.dump(HOSTS, file, protocol=pickle.HIGHEST_PROTOCOL)

    return HOSTS


def get_awards(year):
    '''Awards is a list of strings. Do NOT change the name
    of this function or what it returns.'''
    # Your code here
    # global PREPROCESSED_FLAG
    # if PREPROCESSED_FLAG == 0:
    #     preprocess(year)
    #     PREPROCESSED_FLAG = 1
    AWARDS = find_awards(year)
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

    if year == '2013' or '2015':
        awards = OFFICIAL_AWARDS_1315
    elif year == '2018' or '2019':
        awards = OFFICIAL_AWARDS_1819

    stop_words = generate_stopwords(awards, year)

    global award_nominees_dict

    c = 1
    for award in awards:
        print('-----', c, '-----')
        c += 1
        print("Find nominees for: ", award)
        award_nominees_dict[award] = find_nominees(CLEANSED_DATA, award, year, stop_words)
        print("My answer: ", award_nominees_dict[award])

    with open('nominees_{0}.pickle'.format(year), 'wb') as file:
        pickle.dump(award_nominees_dict, file, protocol=pickle.HIGHEST_PROTOCOL)

    nominees = award_nominees_dict
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
    stop_words = generate_stopwords(awards, year)
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
            top_results, entity_freq_dict = filter_people_names(top_results, entity_freq_dict)

        if not any(word in awards_reduced[key] for word in ['actor', 'actress', 'director', 'cecil']):
            top_results, entity_freq_dict = filter_category_names(top_results, entity_freq_dict)

        print('top results:')
        print(top_results)
        print('\ntop results after merging:')
        top_10 = merge_names(top_results, entity_freq_dict)
        # top_10 = top_results[:10]
        print(top_10)
        print()

        global award_winner_dict
        if len(top_10) != 0:
            award_winner_dict[awards[key].lower()] = top_10[0][0]
        else:
            award_winner_dict[awards[key].lower()] = ''

    with open('winners_{0}.pickle'.format(year), 'wb') as file:
        pickle.dump(award_winner_dict, file, protocol=pickle.HIGHEST_PROTOCOL)

    for item in award_winner_dict.items():
        print(item)

    winners = award_winner_dict
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
    stop_words = generate_stopwords(awards, year)
    award_num_keywords_map, awards_reduced = generate_award_num_keywords_map(awards)

    for key in award_num_keywords_map.keys():
        entity_freq_dict = find_award_presenter(awards, awards_reduced, key, award_num_keywords_map, stop_words)
        top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:100]
        # remove 'golden globes' from identified host names
        entity_freq_dict = remove_goldeb_globes(top_results, entity_freq_dict)
        top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:30]
        # filter for names if necessary
        top_results, entity_freq_dict = filter_people_names(top_results, entity_freq_dict)
        print('top results:')
        print(top_results)
        print('\ntop results after merging:')
        top_10 = merge_names(top_results, entity_freq_dict)
        print(top_10)

        global award_presenters_dict
        if len(top_10) == 0:
            award_presenters_dict[awards[key].lower()] = ['none found']
        elif len(top_10) == 1:
            award_presenters_dict[awards[key].lower()] = [top_10[0][0]]
        elif top_10[0][1] > 10*top_10[1][1]:
            award_presenters_dict[awards[key].lower()] = [top_10[0][0]]
        elif len(top_10) > 1:
            award_presenters_dict[awards[key].lower()] = [top_10[0][0], top_10[1][0]]

    presenters = award_presenters_dict
    with open('presenters_{0}.pickle'.format(year), 'wb') as file:
        pickle.dump(presenters, file, protocol=pickle.HIGHEST_PROTOCOL)

    for item in award_presenters_dict.items():
        print(item)
    return presenters


def pre_ceremony():
    '''This function loads/fetches/processes any data your program
    will use, and stores that data in your DB or in a json, csv, or
    plain text file. It is the first thing the TA will run when grading.
    Do NOT change the name of this function or what it returns.'''
    # Your code here
    # install all necessary libraries
    print('setting up the environment...')

    print('step 1: installing all necessary libraries...')
    os.system('pip install -r requirements.txt')

    print('\nstep 2: downloading spaCy language model used...')
    os.system('python3 -m spacy download en')

    print('\nstep 3: downloading NLTK package...')
    os.system("nltk.download('punkt')")

    print('\nstep 4: querying external data...')
    print('expected loading time: < 10 minutes')
    os.system('python3 scrape_people_names.py')
    os.system('python3 scrape_film_names.py')

    print("\nnote that for addition tasks, please refer to 'additional_analysis' method")
    print('this project is completed by 3 students of Group 16')
    print("Pre-ceremony processing complete.")
    return


def additional_analysis(year):
    global PREPROCESSED_FLAG
    if PREPROCESSED_FLAG == 0:
        preprocess(year)
        PREPROCESSED_FLAG = 1

    print('\n---humor analysis---')
    get_humor(year)

    print('\n---sentiment analysis---')
    sentiment_analysis(year)

    print('\n---red carpet dressing analysis---')
    red_carpet_analysis(year)


# individual task testing
if __name__ == '__main__':
    # pre_ceremony()
    year = '2013'
    # get_hosts(year)
    # get_presenters(year)
    # get_winner(year)
    # get_nominees(year)
    # get_awards(year)
    output_reesults(year)
