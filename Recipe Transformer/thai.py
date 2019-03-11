#-*- coding:utf-8 _*-  
""" 
@author:Xin TONG
@file: custine.py 
@time: 2019/03/08
@site:  
@software: PyCharm 
"""

import pprint
import requests
from bs4 import BeautifulSoup
import main as utils
from random import choice

#Used to check whether recipe is already thai or not
thai_essentials = [
    'curry',
    'coconut milk',
    'fish sauce',
    'chili pepper'
]

#Used to check whether to add fish sauce and coconut milk or not to recipe
entree = [
    'pasta',
    'capellini',
    'spaghetti',
    'ziti',
    'fettuccine',
    'lasagne',
    'linguine',
    'cavatappi',
    'ditalini',
    'macaroni',
    'penne',
    'rigatoni',
    'bowtie',
    'rotini',
    'rice',
    'stock',
]

#Used to determine where to add in the step to add thai ingredients
cooking = [
    'stir',
    'mix',
    'blend'
]

sauces = set()
asian_sauces = set()

with open('data/southeast_asian_sauces.txt', 'r') as file:
    for line in file.readlines():
        asian_sauces.add(line.strip())
file.close()

with open('data/sauces.txt', 'r') as file:
    for line in file.readlines():
        sauces.add(line.strip())
file.close()

spices = set()
asian_spices = set()

with open('data/southeast_asian_spices.txt', 'r') as file:
    for line in file.readlines():
        asian_spices.add(line.strip())
file.close()

with open('data/spices.txt', 'r') as file:
    for line in file.readlines():
        spices.add(line.strip())
file.close()

def is_thai(ingredients):
    thai = False
    for ingredient in ingredients:
        if ingredient in thai_essentials:
            return True
    return thai

def thaify_ingredients(ingredients,recipe_name):

    print("\nIngredients Change(s):")

    # If the recipe is an entree (pasta, rice, soup, the likes), then add coconut milk and fish sauce
    isentree = False
    num_change = 1
    # Thai garnishes
    lemongrass = False
    basil = False
    subsitute_dict = {}
    add_dict = []
    new_ingredients = set()

    for ingredient in ingredients:
        new_line = ingredient;
        line = ingredient.split(' ')
        for item in line:

            if item in entree:
                isentree = True
            if 'lemongrass' == item:
                lemongrass = True
            elif 'basil' == item:
                basil = True
            if item in sauces and item not in asian_sauces:
                sub_sauce = choice(list(asian_sauces))
                # get different substitution sauce
                print(str(num_change)+': "'+item+'" to '+sub_sauce+'"')
                subsitute_dict[item] = sub_sauce
                new_line = new_line.replace(item, sub_sauce)
                num_change = num_change+1
                continue;
            if item in spices and item not in asian_spices:
                sub_spice = choice(list(asian_spices))
                # get different substitution spice
                print(str(num_change)+': "'+item+'" to "'+sub_spice+'"')
                subsitute_dict[item] = sub_spice
                new_line = new_line.replace(item, sub_spice)
                num_change = num_change+1
        new_ingredients.add(new_line)

    # if it's a soup
    if 'soup' in recipe_name:
        isentree = True

    #if it's an entree
    if isentree == True:
        new_ingredients.add("2 tablespoon fish sauce")
        print(str(num_change) + ': Add "2 tablespoon fish sauce"')
        add_dict.append("2 tablespoon fish sauce")
        num_change = num_change + 1
        new_ingredients.add("5 tablespoon coconut milk")
        print(str(num_change) + ': Add "5 tablespoon coconut milk"')
        add_dict.append("5 tablespoon coconut milk")
        num_change = num_change + 1

    # Makeing it hot (for all recipes)
    new_ingredients.add("1/4 cups diced thai pepper")
    print(str(num_change) + ': Add "1/4 cups diced thai pepper"')
    add_dict.append("1/4 cups diced thai pepper")
    num_change = num_change + 1

    # If ingredient is already in the recipe, then don't add
    if lemongrass == False:
        new_ingredients.add("chopped lemongrass")
        print(str(num_change) + ': Add "chopped lemongrass"')
        add_dict.append("chopped lemongrass")
        num_change = num_change + 1
    if basil == False:
        new_ingredients.add("chopped basil")
        print(str(num_change) + ': Add "chopped basil"')
        add_dict.append("chopped basil")
    # print('Transfer ends after ' + str(num_change) + ' times of changes.')
    if num_change < 3:
        print("\n***Notice: We don't recommend you to transfer it")
    return new_ingredients,subsitute_dict, add_dict,num_change

def thaify_directions(directions,subsitute_dict, add_dict,num):
    new_directions = set()
    for line in directions:
        new_line = line
        for old_item in subsitute_dict.keys():
            if old_item in new_line:
                subsitute = subsitute_dict[old_item]
                new_line = new_line.replace(old_item,subsitute)
                # num = num + 1
                # print(str(num) + '. Change the ingredient "' + old_item + '" to "' + subsitute + '".')
        new_directions.add(new_line)

    str_temp = ""
    for record in add_dict:
        if str_temp == "":
            str_temp = str_temp+record
        else:
            str_temp = str_temp + ', '+record
    str_temp = 'Mix '+ str_temp + 'together with other materials.'
    new_directions.add(str_temp)
    num = num + 1
    print(str(num) + ': Add the direction "' + str_temp+'"')

    # print('Transfer ends after ' + str(num) + ' times of changes.')
    # print('The new directions:')
    # pprint.pprint(new_directions)
    return new_directions


def transform(recipe):
    new_ingredients, subsitute_dict, add_dict,num = thaify_ingredients(recipe.ingredients,recipe.name)
    new_directions = thaify_directions(recipe.directions, subsitute_dict, add_dict,num)
    recipe.directions = new_directions
    recipe.ingredients = new_ingredients
    recipe.name = recipe.name+"(Transfered to Thai)"
    return recipe


# def test():
#     url = 'https://www.allrecipes.com/recipe/44868/spicy-garlic-lime-chicken/'
#     recipe = utils.Recipe(url)
#     recipe_name = recipe.name
#     ingredients = recipe.ingredients
#     directions = recipe.directions
#     new_ingredients, subsitute_dict, add_dict = thaify_ingredients(ingredients, recipe_name)
#     pprint.pprint(new_ingredients)
#     pprint.pprint(subsitute_dict)
#     pprint.pprint(add_dict)
#     new_directions = thaify_directions(directions, subsitute_dict, add_dict)
#     pprint.pprint(new_directions)