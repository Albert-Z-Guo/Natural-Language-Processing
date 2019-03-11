import re
import pickle

import spacy
import requests
import unidecode
from bs4 import BeautifulSoup
from nltk import sent_tokenize
from nltk.stem import PorterStemmer

nlp = spacy.load('en')


class Recipe:
    def __init__(self, url):
        page = requests.get(url)
        self.soup = BeautifulSoup(page.content, 'html.parser')
        self.name = self.extract_name()
        self.prep_time, self.cook_time = self.extract_time()
        self.ingredients, self.directions = ingredients, directions = self.get_ingredient_list_and_directions()
        self.directions_nouns = self.extract_directions_nouns(self.directions)
        self.directions_verbs = self.extract_directions_verbs(self.directions)
        self.tools = self.extract_tools(self.directions_nouns)
        self.cooking_methods = self.extract_methods(self.directions_verbs)


    def tokenize(self, line):
        return [(token.text, token.tag_) for token in nlp(line)]


    def extract_name(self):
        return self.soup.find_all("h1", {"class": "recipe-summary__h1"})[0].text


    def extract_time(self):
        times = set([element.text.strip() for element in self.soup.find_all(class_='prepTime__item')])
        # remove uncessary elements
        times.remove('')
        prep_time = None
        cook_time = None
        for time in times:
            if 'prep' in time.lower():
                prep_time = time[4:]
            if 'cook' in time.lower():
                cook_time = time[4:]
        return prep_time, cook_time


    def convert_to_minutes(self):
        if self.cook_time is None:
            return 0
        if 'h' in self.cook_time:
            hour_index = self.cook_time.index('h')
            hours = int(self.cook_time[:hour_index].strip())
            if 'm' in self.cook_time:
                minutes = int(self.cook_time[hour_index+1 : -1].strip())
            else:
                minutes = 0
        else:
            hours = 0
            minutes = int(self.cook_time[: -1].strip())
        return 60*hours + minutes


    def get_ingredient_list_and_directions(self):
        ingredients = [element.label.text.strip() for element in self.soup.find_all(class_='checkList__line')]
        # remove exceptions like 'topping:'
        for i in ingredients:
            if ':' in i:
                ingredients.remove(i)
        ingredients = set(ingredients)
        # remove unnecessary elements
        unnecessary = ['', 'Add all ingredients to list']
        for i in unnecessary:
            if i in ingredients:
                ingredients.remove(i)

        # extract directions section from the webpage
        directions = [element.text.strip() for element in self.soup.find_all(class_='recipe-directions__list--item')]
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
        noun_types = ['NN', 'NNS', 'NNP', 'NNPS']
        adjective_type_exceptions = ['ground', 'skinless', 'boneless']
        noun_type_exceptions = ['parsley', 'garlic', 'chili', 'chile', 'substitute', 'cream', 'flanken', 'cilantro', 'such']
        # replace everything to '' except whitespace, alphanumeric character
        line = re.sub(r'[^\w\s]', '', line)
        token_tag_pairs = self.tokenize(line)
        for pair in token_tag_pairs:
            # if the word is not a noun or cardinal number
            if (not (pair[1] in noun_types) or pair[0] in adjective_type_exceptions) and pair[0] not in noun_type_exceptions:
                return False
        return True


    def extract_brackets(self, line):
        # find '(abc)' where 'abc' is in arbitrary length and 'abc' does not contain brackets
        pattern = re.compile(r'\([^\(\)]*\)')
        match = re.findall(pattern, line)
        if len(match) != 0:
            return match


    def extract_preparation(self, line):
        # find ', abc' or ' - abc' where 'abc' is in arbitrary length
        match = re.findall(re.compile(r'[^.], .*| - .*'), line)
        if len(match) != 0:
            if match[-1][-1] == ')':
                return match[-1][1:-1]
            else:
                return match[-1][1:]


    def extract_descriptor(self, ingredient_name):
        noun_type_exceptions = ['parsley', 'garlic', 'chili', 'chile', 'substitute', 'cream', 'flanken', 'such']
        adjective_type_exceptions = ['ground', 'skinless', 'boneless', 'Parmesan']
        descriptor = []
        token_tag_pairs = []

        for element in ingredient_name.split():
            # treat compound word with hyphen as an adjective
            if '-' in element:
                token_tag_pairs.append((element, 'JJ'))
            else:
                token_tag_pairs.append([(token.text, token.tag_) for token in nlp(element)][0])

        for pair in token_tag_pairs:
            # if the word is an adjective, an adverb, or a past participle of a verb, or exception like 'ground'
            if pair[1] == "JJ" or pair[1] == "RB" or pair[1] == "VBN" or pair[0] in adjective_type_exceptions:
                if pair[0] not in noun_type_exceptions:
                    descriptor.append(pair[0])
        if len(descriptor) != 0:
            return ' '.join(descriptor)


    def extract_all(self, line):
        noun_type_exceptions = ['can', 'tablespoon', 'oz', 'clove']
        not_measurements = ['jalapeno', 'roma']
        measurement = None
        quantity_in_brackets = None
        quantity_split = []
        pre_preparation = []

        # extract preparation
        preparation = self.extract_preparation(line)
        if preparation:
            line = line.replace(preparation, '')
            # remove 'x, ' prefix
            preparation = preparation[2:].strip()

        # extract backets
        brackets = self.extract_brackets(line)
        if brackets:
            # check the first bracket
            # if no numerical value or line_split length > 3
            if not any(char.isdigit() for char in brackets[0]) or len(brackets[0].split()) > 3:
                pre_preparation.append(brackets[0][1:-1])
            else:
                quantity_in_brackets = brackets[0]
            # check the rest brackets if any
            if len(brackets) > 1:
                for b in brackets[1:]:
                    pre_preparation.append(b[1:-1])
            for b in brackets:
                line = re.sub(r'\({0}\)'.format(b), '', line)

        line_split = line.split()
        # extract quantity from the first word if the word contains a digit
        if any(char.isdigit() for char in line_split[0]):
            quantity_split.append(line_split[0])

            # extract quantity from the second word if the word contains a digit
            if any(char.isdigit() for char in line_split[1]):
                quantity_split.append(line_split[1])
                # measurement index
                i = 2
                # check for special case
                if line_split[2] == 'oz':
                    quantity_split.append('oz')
                    i = 3
                # check measurement type
                if (self.nouns_only(line_split[i]) or line_split[i] in noun_type_exceptions) and line_split[i] not in not_measurements:
                    measurement = line_split[i]
            else:
                # check line_split length and measurement type for cases like '1 egg' or '1/2 onion, chopped' or '1 large tomato, seeded and chopped'
                if len(line_split) > 2 and (self.nouns_only(line_split[1]) or line_split[1] in noun_type_exceptions) and line_split[1] not in not_measurements:
                    measurement = line_split[1]
            line = re.sub(r'{0}'.format(' '.join(quantity_split)), '', line)

        if measurement:
            line = re.sub(r'{0}'.format(measurement), '', line)

        # append quantity in backets at the end
        if quantity_in_brackets:
            quantity_split.append(quantity_in_brackets)

        ingredient_name = line.strip()

        # extract descriptor from ingredient_name
        descriptor = self.extract_descriptor(ingredient_name)

        # extract ingredient
        ingredient = ingredient_name
        if descriptor:
            for i in descriptor.split():
                ingredient = re.sub(r'[ ]?\b{0}\b'.format(i), '', ingredient).strip()
        if ingredient == '':
            ingredient = ingredient_name

        # cases to add to descriptor
        if pre_preparation:
            if descriptor is None:
                descriptor = ', '.join(pre_preparation)
            else:
                descriptor += ', ' + ', '.join(pre_preparation)

        if preparation and 'or' in preparation:
            if descriptor is None:
                descriptor = preparation
            else:
                descriptor += ', ' + preparation
            preparation = None

        # add 'to taste' to quantity if any
        if 'to taste' in ingredient:
            quantity_split.append('to taste')
        quantity = ' '.join(quantity_split)
        if quantity == '':
            quantity = None

        # remove ' to taste' in ingredient if any
        ingredient = re.sub(r'(or)? to taste', '', ingredient)
        ingredient = ' '.join(ingredient.split())

        # if the extracted ingredient is not noun
        if not self.nouns_only(ingredient):
            ingredient_name = ingredient
            if preparation:
                ingredient_name += ' ' + preparation
            ingredient_name = ingredient_name.replace(' -', ',')
            preparation = self.extract_preparation(ingredient_name)
            ingredient_name = re.sub(r'{0}'.format(preparation), '', ingredient_name)
            if preparation:
                preparation = preparation[2:].strip()
            descriptor = self.extract_descriptor(ingredient_name)
            ingredient = ingredient_name
            if descriptor:
                for i in descriptor.split():
                    ingredient = re.sub(r'[ ]?\b{0}\b'.format(i), '', ingredient).strip()
                if ingredient == '':
                    ingredient = ingredient_name

        return quantity, measurement, descriptor, ingredient, preparation


    def decompose_ingredients(self):
        print('Ingredients:')
        for line in self.ingredients:
            quantity, measurement, descriptor, ingredient, preparation = self.extract_all(line)
            print('\t' + line)
            if quantity: print('\t  quantity   :', quantity)
            if measurement: print('\t  measurement:', measurement)
            if descriptor: print('\t  descriptor :', descriptor)
            if ingredient: print('\t  ingredient :', ingredient)
            if preparation: print('\t  preparation:', preparation)
            print()


    def extract_directions_ingredients(self, ingredients):
        ingredients_nouns = set()
        for line in ingredients:
            quantity, measurement, descriptor, ingredient, preparation = self.extract_all(line)
            ingredients_nouns |= {ingredient}
            # for better granularity, in case full name is not mentioned
            token_tag_pairs = self.tokenize(ingredient)
            for pair in token_tag_pairs:
                if len(pair[0]) > 1:
                    if (pair[1] == 'NN' or pair[1] == 'NNS') and pair[0] != 'ground':
                        ingredients_nouns |= {pair[0]}
        # start from the longest
        return sorted((list(ingredients_nouns)), key=len)[::-1]


    def extract_ingredients(self, direction):
        ingredients_set = self.extract_directions_ingredients(self.ingredients)
        direction_ingredients = set()
        used = set()
        sentences = sent_tokenize(direction)
        for sentence in sentences:
            for i in ingredients_set:
                if i in sentence and i not in used:
                    direction_ingredients |= {i}
                    # store used partial word in used
                    for word in i.split():
                        used |= {word}
        return direction_ingredients


    def extract_directions_nouns(self, directions):
        directions_nouns = set()
        if isinstance(directions, str):
            directions = [directions]
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
                        if (pair[1] == 'NN' or pair[1] == 'NNS') and pair[0] != 'ground':
                            directions_nouns |= {pair[0]}
        return directions_nouns


    def retrieve_tools_set(self):
        try:
            with open('data/tools.pickle', 'rb') as file:
                tools = pickle.load(file)
        except:
            url = 'https://www.mealime.com/kitchen-essentials-list'
            page = requests.get(url)
            soup = BeautifulSoup(page.content, 'html.parser')
            tools = [element.text for element in soup.find_all(class_='anchor-button')]
            # reduce each tool to its last word
            tools = set([PorterStemmer().stem(tool.split()[-1].strip()) for tool in tools])

            # save retrieved data
            with open('data/tools.pickle', 'wb') as file:
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
            with open('data/cooking_methods.pickle', 'rb') as file:
                cooking_methods = pickle.load(file)
        except:
            url = 'https://www.thedailymeal.com/cook/15-basic-cooking-methods-you-need-know-slideshow/slide-13'
            page = requests.get(url)
            soup = BeautifulSoup(page.content, 'html.parser')
            cooking_methods = [element.h2.text for element in soup.find_all(class_='image-title slide-title')]
            cooking_methods = set([PorterStemmer().stem(unidecode.unidecode(method.strip())) for method in cooking_methods])

            # save retrieved data
            with open('data/cooking_methods.pickle', 'wb') as file:
                pickle.dump(cooking_methods, file, protocol=pickle.HIGHEST_PROTOCOL)
        return cooking_methods


    def retrieve_other_cooking_methods_set(self):
        try:
            with open('data/other_cooking_methods.pickle', 'rb') as file:
                other_cooking_methods = pickle.load(file)
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
            with open('data/other_cooking_methods.pickle', 'wb') as file:
                pickle.dump(other_cooking_methods, file, protocol=pickle.HIGHEST_PROTOCOL)
        return other_cooking_methods


    def extract_directions_verbs(self, directions):
        directions_verbs = set()
        if isinstance(directions, str):
            directions = [directions]
        for direction in directions:
            sentences = sent_tokenize(direction)
            for sentence in sentences:
                token_tag_pairs = self.tokenize(sentence)
                for pair in token_tag_pairs:
                    if pair[1] == 'VB':
                        directions_verbs |= {pair[0].lower()}
        return directions_verbs


    def extract_methods(self, directions_verbs):
        methods = self.retrieve_cooking_methods_set()
        methods |= self.retrieve_other_cooking_methods_set()
        directions_methods = set()
        for verb in directions_verbs:
            if PorterStemmer().stem(verb) in methods:
                directions_methods |= {verb}
        return directions_methods


    def extract_direction_time(self, direction):
        times = []
        for sentence in sent_tokenize(direction):
            match = re.findall(re.compile(r'\d+.*second[s]?\b|\d+.*minute[s]?\b'), sentence)
            if len(match) != 0:
                for m in match:
                    times.append(m.replace('for ', ''))
        if len(times) == 0:
            return None
        return ' + '.join(times)


    def decompose_steps(self):
        prep_time = self.prep_time
        cook_time = self.cook_time
        directions = self.directions
        if len(directions) > 1:
            average_cook_time_per_step = round(self.convert_to_minutes() / (len(directions) - 1))

        for i, direction in enumerate(directions):
            print('Step:', i+1)
            print(direction)
            if i == 0:
                print('\tPrep time:', prep_time)
            else:
                if self.extract_direction_time(direction):
                    print('\testimated cook time: about {0}'.format(self.extract_direction_time(direction)))
                else:
                    print('\testimated cook time: about {0} minutes'.format(average_cook_time_per_step))

            single_direction_tools = self.extract_tools(self.extract_directions_nouns(direction))
            single_direction_methods = self.extract_methods(self.extract_directions_verbs(direction))
            single_direction_ingredients = self.extract_ingredients(direction)

            if len(single_direction_ingredients) > 0:
                print('\tIngredient(s):', ', '.join(single_direction_ingredients))
            if len(single_direction_tools) > 0:
                print('\tTool(s):', ', '.join(single_direction_tools))
            if len(single_direction_methods) > 0:
                print('\tMethod(s):', ', '.join(single_direction_methods))
