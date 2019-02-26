import requests
from bs4 import BeautifulSoup
import re
import spacy
import json
import time
import urllib3
import urllib3.contrib.pyopenssl
urllib3.contrib.pyopenssl.inject_into_urllib3()
http = urllib3.PoolManager()

headers = requests.utils.default_headers()
headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
headers['Accept'] = 'application/json, text/javascript'
# python3 -m spacy download en
nlp = spacy.load('en')

# from lxml.html import fromstring
# import requests
# from itertools import cycle
# import traceback
#
# def get_proxies():
#     url = 'https://free-proxy-list.net/'
#     response = requests.get(url)
#     parser = fromstring(response.text)
#     proxies = set()
#     for i in parser.xpath('//tbody/tr')[:10]:
#         if i.xpath('.//td[7][contains(text(),"yes")]'):
#             proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
#             proxies.add(proxy)
#     return proxies
#
#
# proxies = get_proxies()
# print(proxies)
# proxy_pool = cycle(proxies)
#
# url = 'https://www.allrecipes.com/recipes/93/seafood/'
# for i in range(1,11):
#     #Get a proxy from the pool
#     proxy = next(proxy_pool)
#     print("Request #%d"%i)
#     try:
#         response = requests.get(url, proxies={"http": proxy, "https": proxy})
#         print(response.json())
#     except:
#         #Most free proxies will often get connection errors. You will have retry the entire request using another proxy to work.
#         #We will just skip retries as its beyond the scope of this tutorial and we are only downloading a single url
#         print("Skipping. Connnection error")

def tokenize(line):
    return [(token.text, token.tag_) for token in nlp(line)]

import nltk
# nltk.download('averaged_perceptron_tagger')

def tokenize_nltk(line):
    tokens = nltk.word_tokenize(line)
    token_tag_pairs = nltk.pos_tag(tokens)
    return token_tag_pairs



def extract_quantity_in_backets(line):
    # find '(abc)' where 'abc' is in arbitrary length
    pattern = re.compile(r'\([\w\s]*\)')
    match = re.findall(pattern, line)
    if len(match) != 0:
        return match

def extract_preparation(line):
    # find ', abc' where 'abc' is in arbitrary length
    pattern = re.compile(r', [\w\s]*')
    match = re.findall(pattern, line)
    if len(match) != 0:
        return match


def extract_quantity_measurement_preparation(line):
    quantity_split = []
    measurement = None

    # extract preparation
    preparation = extract_preparation(line)
    if preparation:
        line = re.sub(r'{0}'.format(preparation[0]), '', line)
        # remove ', ' prefix
        preparation = preparation[0][2:]

        # extract quantity in backets
    quantity_in_brackets = extract_quantity_in_backets(line)
    if quantity_in_brackets:
        line = re.sub(r'\({0}\)'.format(quantity_in_brackets[0]), '', line)
        quantity_in_brackets = quantity_in_brackets[0]

    # extract quantity from the first word
    line_split = line.split()
    quantity_split.append(line_split[0])

    # extract quantity from the second word if the word contains a digit
    if len(line_split) > 1:
        if any(char.isdigit() for char in line_split[1]):
            quantity_split.append(line_split[1])
            measurement = line_split[2]
        else:
            # to adjust for case like '1 egg' or '1/2 onion, chopped'
            if len(line_split) > 2:
                measurement = line_split[1]
    else:
        measurement = None

    # append quantity in backets at the end
    if quantity_in_brackets:
        quantity_split.append(quantity_in_brackets)

    return ' '.join(quantity_split), measurement, preparation


def extract_ingredient_name(line):
    quantity, measurement, preparation = extract_quantity_measurement_preparation(line)
    if measurement is None:
        measurement = ''

    if preparation:
        return line[len(quantity + ' ' + measurement): -(len(preparation) + 2)].strip()
    else:
        return line[len(quantity + ' ' + measurement):].strip()

def extract_descriptor(ingredient_name):
    descriptor = []
    token_tag_pairs = tokenize(ingredient_name)
    for pair in token_tag_pairs:
        if pair[1] == "JJ" or pair[1] == "VBN":
            descriptor.append(pair[0])
    if len(descriptor) != 0:
        return ' '.join(descriptor)


def check_noun_num(token_tag_pairs):
    tag_num_dict = {}
    for pair in token_tag_pairs:
        if pair[1] not in tag_num_dict:
            tag_num_dict[pair[1]] = 1
        else:
            tag_num_dict[pair[1]] += 1

    criterion_1 = 'NN' in tag_num_dict and tag_num_dict['NN'] >= 2
    criterion_2 = 'NNS' in tag_num_dict and tag_num_dict['NNS'] >= 2
    criterion_3 = 'NN' in tag_num_dict and 'NNS' in tag_num_dict and tag_num_dict['NN'] + tag_num_dict['NNS'] >= 2

    if criterion_1 or criterion_2 or criterion_3:
        return True
    else:
        return False
#
# url = 'https://www.allrecipes.com/recipe/23988/simple-spinach-lasagna/?internalSource=streams&referringId=87&referringContentType=Recipe%20Hub&clickId=st_trending_s'
#
# # test
# # url = 'https://www.allrecipes.com/recipe/235874/copycat-panera-broccoli-cheddar-soup/?clickId=right%20rail1&internalSource=rr_feed_recipe_sb&referringId=23988%20referringContentType%3Drecipe'
#
# page = requests.get(url)
# soup = BeautifulSoup(page.content, 'html.parser')
# print(soup)
#
# # extract ingredients section from the webpage
# ingredients = set([element.label.text.strip() for element in soup.find_all(class_='checkList__line')])
#
# # remove unnecessary elements
# ingredients.remove('')
# ingredients.remove('Add all ingredients to list')

def extract_ingredients_nouns(line):
    ingredients_nouns = set()
    token_tag_pairs = tokenize(line)
    for pair in token_tag_pairs:
        if pair[1] == 'NN' or pair[1] == 'NNS':
            # global ingredients_nouns
            ingredients_nouns |= {pair[0]}

    return list(ingredients_nouns)

def get_ingredient_lines_from_url(url):
    # page = http.request('GET', url)
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')

    # extract ingredients section from the webpage
    ingredients = set([element.label.text.strip() for element in soup.find_all(class_='checkList__line')])

    # remove unnecessary elements
    ingredients.remove('')
    ingredients.remove('Add all ingredients to list')

    return ingredients

def get_ingredient_from_url(url):
    ingredients = get_ingredient_lines_from_url(url)

    ingredient_list = []
    seasonings = []

    for line in ingredients:
        quantity, measurement, preparation = extract_quantity_measurement_preparation(line)
        if ':' in line:
            # exceptions like "topping:"
            continue
        ingredient_name = extract_ingredient_name(line)
        descriptor = extract_descriptor(ingredient_name)

        # ingredient_list.extend(extract_ingredients_nouns(ingredient_name))
        if measurement is not None and ('teaspoon' in measurement or 'tablespoon' in measurement):
           seasonings.extend(extract_ingredients_nouns(ingredient_name))
        else:
            ingredient_list.append(ingredient_name)

    return ingredient_list, seasonings

# for line in ingredients:
#     quantity, measurement, preparation = extract_quantity_measurement_preparation(line)
#     ingredient_name = extract_ingredient_name(line)
#     descriptor = extract_descriptor(ingredient_name)
#
#     print(line)
#     print('ingredient name:', ingredient_name)
#     print('descriptor:', descriptor)
#     print('quantity:', quantity)
#     print('measurement:', measurement)
#     print('preparation:', preparation)
#     print()

#     token_tag_pairs = tokenize(line)
#     print(token_tag_pairs)
#     print(check_noun_num(token_tag_pairs))
#     print()


def get_recipe_urls(url):
    html = requests.get(url)
    soup = BeautifulSoup(html.content, 'html.parser')
    tags = soup.find_all('div', class_='fixed-recipe-card__info')

    # pages = '?page=2'

    recipe_urls = []
    for tag in tags:
        url = tag.find('a')['href']
        print(url)
        recipe_urls.append(url)
    return recipe_urls


def get_all_ingredient(url, page = 1):
    ingredients = []
    seasonings = []
    recipe_urls = get_recipe_urls(url)
    for v_url in recipe_urls:
        temp, season= get_ingredient_from_url(v_url)
        ingredients += temp
        seasonings += season
        print(temp)
        time.sleep(3)
    # for i in range(1, page):
    #     new_url = url + '?page={}'.format(i)
    #     recipe_urls = get_recipe_urls(new_url)
    #     for v_url in recipe_urls:
    #         temp = get_ingredient_from_url(v_url)
    #         ingredients += temp
    #         # time.sleep(30)
    #     # time.sleep(30)

    print(ingredients)
    return ingredients, seasonings


with open('vegetarian_scrape_ingredient.json', 'r') as f:
    ingredients = json.load(f)
    print(ingredients.keys())

# ingredients['vegetarian_protein'] = []
seasonings = ingredients['seasonings']
page = '3'
temp = ingredients['vegetarian_protein']
vege_protein_url = 'https://www.allrecipes.com/recipes/16778/everyday-cooking/vegetarian/protein/?page='+page
ingre, season = get_all_ingredient(vege_protein_url)
seasonings += season
temp += ingre
ingredients['vegetarian_protein'] = temp
# vegetarian_recipes_url = 'https://www.allrecipes.com/recipes/87/everyday-cooking/vegetarian/?page='+page
# ingre_temp = ingredients[vege_key]
# ingre_temp += get_all_ingredient(vegetarian_recipes_url, 1)
# ingredients[vege_key] = list(set(ingre_temp))


# page = '2'
# vegetarian_recipes_url = 'https://www.allrecipes.com/recipes/87/everyday-cooking/vegetarian/?page='+page
# ingre_temp = ingredients[vege_key]
# ingre_temp += get_all_ingredient(vegetarian_recipes_url, 1)
# ingredients[vege_key] = list(set(ingre_temp))

# ingredients['seafood'] = []
temp = ingredients['seafood']
seafood_recipes_url = 'https://www.allrecipes.com/recipes/93/seafood/' + '?page=2'
ingre, season = get_all_ingredient(seafood_recipes_url, 2)
temp += ingre
seasonings += season
ingredients['seafood'] = temp

meat_ingredients = []
for index in range(200, 206):
    meat_and_poultry_recipes_url = "https://www.allrecipes.com/recipes/{}/meat-and-poultry/".format(index)
    ingre, season = get_all_ingredient(meat_and_poultry_recipes_url, 2)
    meat_ingredients += ingre
    seasonings += season
    time.sleep(5)
ingredients['meat_and_poultry'] = meat_ingredients

# proteins = []
# protein_vegentarian_url = 'https://www.allrecipes.com/recipes/16778/everyday-cooking/vegetarian/protein/'
# protein_urls = get_recipe_urls(protein_vegentarian_url)
# for u in protein_urls:
#     # temp = get_ingredient_from_url(u)
#     # proteins += temp
#     # print(temp)
#     for line in get_ingredient_lines_from_url(u):
#         quantity, measurement, preparation = extract_quantity_measurement_preparation(line)
#         if measurement is None or 'teaspoon' in measurement or 'tablespoon' in measurement:
#             continue
#         print(extract_ingredient_name(line))
#         print(quantity+' '+measurement)
#         print()

# vege_ingredient = ingredients[vege_key]
# seafood_ingredient = ingredients['seafood']
# meat_ingredient = ingredients['meat_and_poultry']
#
# # print(set(vege_ingredient)-set(seafood_ingredient))
# print(set(vege_ingredient) - set(meat_ingredient))

#

ingredients['seasonings'] = seasonings
with open('vegetarian_scrape_ingredient.json', 'w') as f:
    json.dump(ingredients, f)
f.close()
