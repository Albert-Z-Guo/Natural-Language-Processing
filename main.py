import time
import json
import re

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
HOSTS = None


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
    return re.sub(r'[^\w\s\'#@]', ' ', line)


def identify_entities(text):
    tags = {}
    entities = list(nlp(text).ents)
    for entity in entities:
        if entity not in tags:
            tags[entity.text]=[entity.label_]
    return tags


def find_host(cleansed_data):
    pattern = re.compile(r'host')
    entity_freq_dict = {}
    for line in cleansed_data:
        match = re.search(pattern, line.lower())
        if match:
            for entity in identify_entities(line).keys():
                entity = remove_apostrophe(entity).strip()
                if len(entity) > 1:
                    if entity not in entity_freq_dict:
                        entity_freq_dict[entity] = 1
                    else:
                        entity_freq_dict[entity] += 1
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
                del e[name]

    top_10 = sorted(e.items(), key=lambda pair: pair[1], reverse=True)[:10]
    return top_10


def main():
    start_time = time.time()
    df = pd.read_json(path_or_buf='gg2013.json')
    # df = pd.read_json(path_or_buf='gg2015.json')

    data = df['text']
    # sample data if necessary
    sample_size = 200000
    if len(df) > sample_size:
        data = data.sample(n=sample_size)

    cleansed_data = []
    for tweet in data:
        line = remove_retweet_prefix(tweet)
        line = remove_hashtag(line)
        line = remove_at(line)
        line = remove_url(line)
        line = cleanse(line)
        cleansed_data.append(line)

    # find host
    print('finding hosts...')
    entity_freq_dict = find_host(cleansed_data)
    top_100 = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:100]
    names = [pair[0] for pair in top_100]
    # remove 'golden globes' from identified host names
    golden_globes = [name for name in names if fuzz.ratio(name.lower(), 'golden globes') > 60]
    for name in golden_globes:
        if name in entity_freq_dict:
            del entity_freq_dict[name]
    top_results = sorted(entity_freq_dict.items(), key=lambda pair: pair[1], reverse=True)[:50]
    top_results, entity_freq_dict = filter_names(top_results, entity_freq_dict)
    top_10 = merge_names(top_results, entity_freq_dict)
    global HOSTS
    HOSTS = [name[0] for name in top_10][:2]

    print(HOSTS)
    print('total running time: {0:.2f} seconds'.format(time.time() - start_time))


# the following global variable and functions are adapted from gg_api.py from autograder
OFFICIAL_AWARDS = ['cecil b. demille award', 'best motion picture - drama', 'best performance by an actress in a motion picture - drama', 'best performance by an actor in a motion picture - drama', 'best motion picture - comedy or musical', 'best performance by an actress in a motion picture - comedy or musical', 'best performance by an actor in a motion picture - comedy or musical', 'best animated feature film', 'best foreign language film', 'best performance by an actress in a supporting role in a motion picture', 'best performance by an actor in a supporting role in a motion picture', 'best director - motion picture', 'best screenplay - motion picture', 'best original score - motion picture', 'best original song - motion picture', 'best television series - drama', 'best performance by an actress in a television series - drama', 'best performance by an actor in a television series - drama', 'best television series - comedy or musical', 'best performance by an actress in a television series - comedy or musical', 'best performance by an actor in a television series - comedy or musical', 'best mini-series or motion picture made for television', 'best performance by an actress in a mini-series or motion picture made for television', 'best performance by an actor in a mini-series or motion picture made for television', 'best performance by an actress in a supporting role in a series, mini-series or motion picture made for television', 'best performance by an actor in a supporting role in a series, mini-series or motion picture made for television']


def get_hosts(year):
    '''Hosts is a list of one or more strings. Do NOT change the name
    of this function or what it returns.'''
    # Your code here
    return HOSTS


def get_awards(year):
    '''Awards is a list of strings. Do NOT change the name
    of this function or what it returns.'''
    # Your code here
    return awards


def get_nominees(year):
    '''Nominees is a dictionary with the hard coded award
    names as keys, and each entry a list of strings. Do NOT change
    the name of this function or what it returns.'''
    # Your code here
    return nominees


def get_winner(year):
    '''Winners is a dictionary with the hard coded award
    names as keys, and each entry containing a single string.
    Do NOT change the name of this function or what it returns.'''
    # Your code here
    return winners


def get_presenters(year):
    '''Presenters is a dictionary with the hard coded award
    names as keys, and each entry a list of strings. Do NOT change the
    name of this function or what it returns.'''
    # Your code here
    return presenters


def pre_ceremony():
    '''This function loads/fetches/processes any data your program
    will use, and stores that data in your DB or in a json, csv, or
    plain text file. It is the first thing the TA will run when grading.
    Do NOT change the name of this function or what it returns.'''
    # Your code here
    print("Pre-ceremony processing complete.")
    return


if __name__ == '__main__':
    main()
