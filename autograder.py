'''
Version 0.6
Python 3
'''
import sys
import json
import time
import difflib
from pprint import pprint
from collections import Counter

from nltk.metrics import edit_distance

import main as gg_api

global toMovie
toMovie = {'johann johannsson': 'the theory of everything', 'alexandre desplat': 'the imitation game', 'trent reznor and atticus ross': 'gone girl', 'antonio sanchez': 'birdman', 'hans zimmer': 'interstellar', 'glory': 'selma', 'big eyes': 'big eyes', 'mercy is': 'noah', 'opportunity': 'annie', 'yellow flicker beat': 'the hunger games mockingjay part 1', 'alejandro gonzalez inarritu': 'birdman', 'wes anderson': 'the grand budapest hotel', 'gillian flynn': 'gone girl', 'richard linklater': 'boyhood', 'graham moore': 'the imitation game'}


def norm_text(textstring):
    """Takes a string of text and returns a string of normalized text."""
    return "".join([c.lower() for c in textstring if c.isalnum() or c.isspace()])


def text(resultstr, answerstr):
    """Accepts two normalized texts, as output by the norm_text
    function, and returns a score based on the match length relative
    to the longest text length."""

    result = resultstr.split()
    answer = answerstr.split()

    len_result = len(result)
    len_answer = len(answer)

    if (resultstr in answerstr) or (answerstr in resultstr):
        textscore = min(len_result, len_answer)/float(max(len_result, len_answer))
    else:
        s = difflib.SequenceMatcher(None, result, answer)

        longest = s.find_longest_match(0, len_result, 0, len_answer)
        longest = longest.size/float(max(len_result, len_answer))

        if longest > 0.3:
            matchlen = sum([m[2] for m in s.get_matching_blocks() if m[2] > 1])
            textscore = float(matchlen)/max(len_result, len_answer)
        else:
            textscore = longest

    return textscore


def spell_check(r, a, s, scores, weight=1):
    change = weight*(1-(edit_distance(r, a)/float(max(len(r), len(a)))))
    if s in scores:
        # penalty for returning multiple of the same result when
        # one instance is incorrectly spelled
        return (scores[s] + change)/2.0
    else:
        return change


def calc_translation(result, answer):
    '''Accepts two lists of strings, determines the best matches
    between them, and returns a translation dictionary and
    score.'''

    resultmap = {norm_text(r): r for r in result}
    answermap = {norm_text(a): a for a in answer}
    result = set(resultmap.keys())
    answer = set(answermap.keys())

    intersection = result.intersection(answer)
    translation = {resultmap[i]: answermap[i] for i in intersection}
    scores = dict(list(zip(list(translation.values()), [1]*len(intersection))))
    score_by_results = {}
    score_by_answers = {}

    # loop through results that didn't have a perfect match
    # and get a score for each of them.
    comp = list(result - intersection)

    for r in comp:
        score_by_results[r] = Counter()
        for a in answer:
            if a not in score_by_answers:
                score_by_answers[a] = Counter()

            score_by_results[r][a] = text(r, a)
            score_by_answers[a][r] = score_by_results[r][a]

    for r in score_by_results:
        cnt = 0
        ranking = score_by_results[r].most_common()
        flag = True
        while flag:
            # The answer that best matches the result
            answer_match = ranking[cnt][0]
            # The top result matching that answer
            max_result = score_by_answers[answer_match].most_common(1)[0]

            if score_by_results[r][answer_match] < 0.45:
                bestAnswer = False
                score = 0

                # Unacceptably low score.
                # Check if we have a case of returning the movie instead
                # of the person, or vice versa.
                for ha in toMovie:
                    tempScore = text(r, ha)
                    if tempScore > score:
                        score = tempScore
                        bestAnswer = ha

                if bestAnswer and score > 0.45:
                    translation[resultmap[r]] = toMovie[ha]
                    scores[toMovie[ha]] = spell_check(r, ha, toMovie[ha], scores, 0.5)

                flag = False
            elif (max_result[0] == r) or (score_by_results[r][answer_match] > score_by_answers[answer_match][max_result[0]]):
                # if the top result matching that answer is our current result or
                # if the current result's score is greater than the previous top result
                translation[resultmap[r]] = answermap[answer_match]
                scores[answermap[answer_match]] = spell_check(r, answer_match, answer_match, scores)

                flag = False

            cnt += 1
            if cnt == len(ranking):
                flag = False

    if scores:
        return sum(scores.values())/float(len(scores)), translation
    else:
        return 0, translation


def calc_score(result, answer):
    result = set(result)
    intersection = result.intersection(answer)
    len_intersection = len(intersection)
    len_union = len(result.union(answer))
    len_result = len(result)
    len_answer = len(answer)

    if len_union == 0:
        return 0
    elif len_result == len_answer and len_intersection == len_answer:
        m = 1.0
    elif len_intersection == len_result:
        # all results correspond to a correct answer, but some
        # answers are missing
        m = 0.95
    elif len_intersection == len_answer:
        # all answers correspond to a result, but there are
        # some extra results as well
        m = 0.9
    elif len_intersection > 0:
        # there is some post-translation intersection between
        # results and answers.
        m = 0.85
    else:
        return 0

    return (len_intersection / float(len_union)) * m


def score_structured(year, answers, info_type):
    # c_score is the completeness score
    spelling_score = 0
    c_score = 0
    results = getattr(gg_api, 'get_%s' % info_type)(year)
    length = 26

    if info_type == "nominees":
        tempans = answers['award_data']['cecil b. demille award']
        del answers['award_data']['cecil b. demille award']
        tempres = results['cecil b. demille award']
        del results['cecil b. demille award']
        length = 25

    for a in answers['award_data']:
        if info_type == 'winner':
            temp_spelling, translation = calc_translation([results[a]], [answers['award_data'][a][info_type]])
        else:
            temp_spelling, translation = calc_translation(results[a], answers['award_data'][a][info_type])
            c_score += calc_score([translation[res] if res in translation else res for res in results[a]], answers['award_data'][a][info_type])
        spelling_score += temp_spelling

    if info_type == "nominees":
        answers['award_data']['cecil b. demille award'] = tempans
        results['cecil b. demille award'] = tempres

    return spelling_score/length, c_score/length


def score_unstructured(year, answers, info_type):
    results = getattr(gg_api, 'get_%s' % info_type)(year)
    spelling_score, translation = calc_translation(results, answers[info_type])
    c_score = calc_score([translation[res] if res in translation else res for res in results], answers[info_type])

    return spelling_score, c_score


def main(years, grading):
    types = ['spelling', 'completeness']

    scores = {y: {g: {t:0 for t in types} for g in grading} for y in years}
    for y in years:
        with open('gg%sanswers.json' % y, 'r') as f:
            answers = json.load(f)

        answers['awards'] = list(answers['award_data'].keys())

        for g in grading:
            if g in ['hosts', 'awards']:
                scores[y][g]['spelling'], scores[y][g]['completeness'] = score_unstructured(y, answers, g)
            else:
                scores[y][g]['spelling'], scores[y][g]['completeness'] = score_structured(y, answers, g)

        if "winner" in grading:
            del scores[y]['winner']['completeness']
    pprint(scores)

if __name__ == '__main__':
    start_time = time.time()
    years = ['2013', '2015']
    grading = ["hosts", "awards", "nominees", "presenters", "winner"]

    if len(sys.argv) > 1:
        if '2013' in sys.argv:
            years = ['2013']
        elif '2015' in sys.argv:
            years = ['2015']

        newg = [g for g in grading if g in sys.argv]
        if len(newg) > 0:
            grading = newg

    main(years, grading)
    print('total processing time: {0:.2f} seconds'.format(time.time() - start_time))
