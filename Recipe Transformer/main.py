import re
import pickle

import spacy
import requests
from bs4 import BeautifulSoup
from nltk import sent_tokenize
from nltk.stem import PorterStemmer

nlp = spacy.load('en')

class Recipe:
    def tokenize(self, line):
        return [(token.text, token.tag_) for token in nlp(line)]


    def extract_time(self, url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        times = set([element.text.strip() for element in soup.find_all(class_='prepTime__item')])
        # remove uncessary elements
        times.remove('')
        for time in times:
            if 'prep' in time.lower():
                prep_time = time[4:]
            if 'cook' in time.lower():
                cook_time = time[4:]
        return prep_time, cook_time


    def convert_to_minutes(self, time):
        if 'h' in cook_time:
            hour_index = cook_time.index('h')
            hours = int(cook_time[:hour_index].strip())
            minutes = int(cook_time[hour_index+1 : -1].strip())
        else:
            hours = 0
            minutes = int(cook_time[: -1].strip())
        return 60*hours + minutes


    def get_ingredient_list_and_directions(self, url):
        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')
        # extract ingredients section from the webpage
        ingredients = set([element.label.text.strip() for element in soup.find_all(class_='checkList__line')])
        # remove unnecessary elements
        unnecessary = ['', 'Add all ingredients to list']
        for i in unnecessary:
            if i in ingredients:
                ingredients.remove(i)

        # extract directions section from the webpage
        directions = [element.text.strip() for element in soup.find_all(class_='recipe-directions__list--item')]
        # remove unnecessary elements
        directions.remove('')
        return ingredients, directions


    def numerical(self, line):
        # replace everything to '' except whitespace, alphanumeric character
        line = re.sub(r'[^\w\s]', '', line)
        token_tag_pairs = self.tokenize(line)
        for pair in token_tag_pairs:
            # if the word is not numerical
            if not pair[1] == "CD":
                return False
        return True


    def nouns_only(self, line):
        # replace everything to '' except whitespace, alphanumeric character
        line = re.sub(r'[^\w\s]', '', line)
        token_tag_pairs = self.tokenize(line)
        for pair in token_tag_pairs:
            # if the word is not a noun or cardinal number
            if not (pair[1] == "NN" or pair[1] == "NNS"):
                return False
        return True


    def extract_quantity_in_backets(self, line):
        # find '(abc)' where 'abc' is in arbitrary length and 'abc' does not contain brackets
        pattern = re.compile(r'\([^\(\)]*\)')
        match = re.findall(pattern, line)
        if len(match) != 0:
            # if no numerical value or line_split length > 3
            if not any(char.isdigit() for char in match[0]) or len(match[0].split()) > 3:
                return None
            return match


    def extract_preparation(self, line):
        # find ', abc' where 'abc' is in arbitrary length
        pattern = re.compile(r'[\b]?, [^\(\)]*')
        match = re.findall(pattern, line)
        if len(match) != 0:
            return match


    def extract_all(self, line):
        type_exceptions = ['can', 'tablespoon', 'oz']
        quantity_split = []
        measurement = None

        # extract preparation
        line = line.replace(' -', ',')
        preparation = self.extract_preparation(line)
        if preparation:
            preparation = preparation[0].strip()
            line = re.sub(r'{0}'.format(preparation), '', line)
            # remove ', ' prefix
            preparation = preparation[2:]

        # extract quantity in backets
        quantity_in_brackets = self.extract_quantity_in_backets(line)
        if quantity_in_brackets:
            line = re.sub(r'\({0}\)'.format(quantity_in_brackets[0]), '', line)
            quantity_in_brackets = quantity_in_brackets[0]

        line_split = line.split()
        # extract quantity from the first word if the word contains a digit
        if any(char.isdigit() for char in line_split[0]):
            quantity_split.append(line_split[0])

            # extract quantity from the second word if the word contains a digit
            if any(char.isdigit() for char in line_split[1]):
                quantity_split.append(line_split[1])
                # check measurement type
                # to avoid case like '1 large tomato, seeded and chopped'
                if self.nouns_only(line_split[2]) or line_split[2] in type_exceptions:
                    measurement = line_split[2]
            else:
                # check line_split length for case like '1 egg' or '1/2 onion, chopped'
                if len(line_split) > 2 and (self.nouns_only(line_split[1]) or line_split[1] in type_exceptions):
                    measurement = line_split[1]
            line = re.sub(r'{0}'.format(' '.join(quantity_split)), '', line)

        if measurement:
            line = re.sub(r'{0}'.format(measurement), '', line)

        # append quantity in backets at the end
        if quantity_in_brackets:
            quantity_split.append(quantity_in_brackets)
        quantity = ' '.join(quantity_split)

        # extract ingredient name
        line = re.sub(r'[ ]?®', '', line)
        line = re.sub(r'[ ]?™', '', line)
        ingredient_name = line.strip()

        # if 'or to taske' or 'or as needed' in preparation
        if preparation is not None and 'or ' in preparation:
            quantity += ' ' + preparation
            preparation = None

        return quantity, measurement, ingredient_name, preparation


    def extract_directions_nouns(self, directions):
        directions_nouns = set()
        for direction in directions:
            sentences = sent_tokenize(direction)
            for sentence in sentences:
                # check for special cases where spaCy cannot recognize well
                if ' oven' in sentence:
                    directions_nouns |= {'oven'}
                token_tag_pairs = self.tokenize(sentence)
                for pair in token_tag_pairs:
                    # avoid case like 'degrees C'
                    if len(pair[0]) > 1:
                        if pair[1] == 'NN' or pair[1] == 'NNS':
                            directions_nouns |= {pair[0]}
        return directions_nouns


    def retrieve_tools_set(self):
        try:
            with open('tools.pickle', 'rb') as file:
                tools = pickle.load(file)
                print('loaded tools set successfully')
        except:
            url = 'https://www.mealime.com/kitchen-essentials-list'
            page = requests.get(url)
            soup = BeautifulSoup(page.content, 'html.parser')
            tools = [element.text for element in soup.find_all(class_='anchor-button')]
            # reduce each tool to its last word
            tools = set([PorterStemmer().stem(tool.split()[-1].strip()) for tool in tools])

            # save retrieved data
            with open('tools.pickle', 'wb') as file:
                pickle.dump(tools, file, protocol=pickle.HIGHEST_PROTOCOL)

        return tools


    def extract_tools(self, directions_nouns):
        tools = self.retrieve_tools_set()
        directions_tools = set()
        for noun in directions_nouns:
            if PorterStemmer().stem(noun) in tools:
                directions_tools |= {noun}
        return directions_tools


    def retrieve_cooking_methods_set(self):
        try:
            with open('cooking_methods.pickle', 'rb') as file:
                cooking_methods = pickle.load(file)
                print('loaded cooking_methods set successfully')
        except:
            url = 'https://www.thedailymeal.com/cook/15-basic-cooking-methods-you-need-know-slideshow/slide-13'
            page = requests.get(url)
            soup = BeautifulSoup(page.content, 'html.parser')
            cooking_methods = [element.h2.text for element in soup.find_all(class_='image-title slide-title')]
            cooking_methods = set([PorterStemmer().stem(method.strip()) for method in cooking_methods])

            # save retrieved data
            with open('cooking_methods.pickle', 'wb') as file:
                pickle.dump(cooking_methods, file, protocol=pickle.HIGHEST_PROTOCOL)

        return cooking_methods


    def retrieve_other_cooking_methods_set(self):
        try:
            with open('other_cooking_methods.pickle', 'rb') as file:
                other_cooking_methods = pickle.load(file)
                print('loaded other_cooking_methods set successfully')
        except:
            url = 'https://en.wikibooks.org/wiki/Cookbook:Cooking_Techniques'
            page = requests.get(url)
            soup = BeautifulSoup(page.content, 'html.parser')
            unwanted = ['Contents', '[', 'edit', ']', '\n']
            other_cooking_methods = set()
            dump = soup.find_all(class_='mw-parser-output')
            for i in dump:
                for j in i.contents:
                    if hasattr(j, 'contents'):
                        for k in j.contents:
                            if hasattr(k, 'contents'):
                                for l in k.contents:
                                    if hasattr(l, 'contents'):
                                        for method in l:
                                            if method.string is not None and method not in unwanted:
                                                other_cooking_methods |= {PorterStemmer().stem(method.string.split()[-1])}

            # remove uncessary methods after complexity reduction
            other_cooking_methods.remove('cook')
            other_cooking_methods.remove('chocol')

            # save retrieved data
            with open('other_cooking_methods.pickle', 'wb') as file:
                pickle.dump(other_cooking_methods, file, protocol=pickle.HIGHEST_PROTOCOL)

        return other_cooking_methods


    def extract_directions_verbs(self, directions):
        directions_verbs = set()
        for direction in directions:
            sentences = sent_tokenize(direction)
            for sentence in sentences:
                token_tag_pairs = self.tokenize(sentence)
                for pair in token_tag_pairs:
                    if pair[1] == 'VB':
                        directions_verbs |= {pair[0]}
        return directions_verbs


    def extract_methods(self, directions_verbs):
        methods = self.retrieve_cooking_methods_set()
        other_methods = self.retrieve_other_cooking_methods_set()
        methods |= other_methods
        directions_methods = set()
        for verb in directions_verbs:
            if PorterStemmer().stem(verb) in methods:
                directions_methods |= {verb}
        return directions_methods


# test
recipe = Recipe()
print(recipe.extract_all('1 (15 ounce) can garbanzo beans (chickpeas), drained and rinsed'))
url = 'https://www.allrecipes.com/recipe/180735/traditional-style-vegan-shepherds-pie/'
ingredients, directions = recipe.get_ingredient_list_and_directions(url)
directions_nouns = recipe.extract_directions_nouns(directions)
directions_verbs = recipe.extract_directions_verbs(directions)
print(recipe.extract_tools(directions_nouns))
print(recipe.retrieve_cooking_methods_set())
print(recipe.retrieve_other_cooking_methods_set())
print(recipe.extract_directions_verbs(directions))
print(recipe.extract_methods(directions_verbs))
