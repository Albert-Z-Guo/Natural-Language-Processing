#-*- coding:utf-8 _*-  
""" 
@author:Xin TONG
@file: india_transformation.py 
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
india_essentials = [
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


banned  = ['cow', 'beef', 'steak', 'filet', 'mignon', 'brisket', 'pork','hotdog', 'ribs']


def indiafy_ingredients(ingredients,recipe_name):

    print("\nIngredients Change(s):")

    # If the recipe is an entree (pasta, rice, soup, the likes), then add coconut milk and fish sauce
    num_change = 1
    # Thai garnishes
    india_dict = { "curry":False,
                   "chili":False,
                   "chilies":False,
                   "cumin":False,
                   "cardamom":False,
                   "cinnamon":False,
                   "turmeric":False
                   }
    subsitute_dict = {}
    add_dict = []
    new_ingredients = set()

    for ingredient in ingredients:
        new_line = ingredient;
        line = ingredient.split(' ')
        for item in line:
            if item == "curry":
                india_dict["curry"] == True
                continue
            for indias in india_dict.keys():
                if item in indias:
                    india_dict[item] =True
                    continue
            # गाय हमारी माता हे !!!! don't eat cows; also pork
            if item in banned:
                sub_meat = "lamb"
                print(str(num_change) + ': "' + item + '" to "' + sub_meat +'"')
                subsitute_dict[item] = sub_meat
                new_line = new_line.replace(item, sub_meat)
                num_change = num_change + 1
                continue;
            if item in sauces and item not in asian_sauces:
                sub_sauce = choice(list(asian_sauces))
                # get different substitution sauce
                print(str(num_change)+': "'+item+'" to "'+sub_sauce +'"')
                subsitute_dict[item] = sub_sauce
                new_line = new_line.replace(item, sub_sauce)
                num_change = num_change+1
                continue;
            if item in spices and item not in asian_spices:
                sub_spice = choice(list(asian_spices))
                # get different substitution spice
                print(str(num_change)+': "'+item+'" to "'+sub_spice +'"')
                subsitute_dict[item] = sub_spice
                new_line = new_line.replace(item, sub_spice)
                num_change = num_change+1
        new_ingredients.add(new_line)


    #if it doesn't have curry
    if india_dict["curry"] == False:
        new_ingredients.add("2 tablespoon curry")
        print(str(num_change) + ': Add "2 tablespoon curry"')
        add_dict.append("2 tablespoon curry")
        num_change = num_change + 1

    # Makeing it hot (for all recipes)
    if india_dict["chili"] == False and india_dict["chilies"] == False:
        new_ingredients.add("1/4 cups dried chilies")
        print(str(num_change) + ': Add "1/4 cups dried chilies"')
        add_dict.append("1/4 cups dried chilies")
        num_change = num_change + 1

    # If ingredient is already in the recipe, then don't add
    if india_dict["cardamom"] == False:
        new_ingredients.add("chopped cardamom")
        print(str(num_change) + ': Add "chopped cardamom"')
        add_dict.append("chopped cardamom")
        num_change = num_change + 1
    if india_dict["cinnamon"] == False:
        new_ingredients.add("chopped cinnamon")
        print(str(num_change) + ': Add "chopped cinnamon"')
        add_dict.append("chopped cinnamon")
        num_change = num_change + 1
    if india_dict["turmeric"] == False:
        new_ingredients.add("chopped turmeric")
        print(str(num_change) + ': Add "chopped turmeric"')
        add_dict.append("chopped turmeric")
        num_change = num_change + 1
    # print('Transfer ends after ' + str(num_change) + ' times of changes.')
    # if num_change < 2:
    #     print("Notice!!! We don't recommend you to do that!")
    return new_ingredients,subsitute_dict, add_dict,num_change

def indiafy_directions(directions,subsitute_dict, add_dict,num):
    new_directions = set()
    for line in directions:
        new_line = line
        for old_item in subsitute_dict.keys():
            if old_item in new_line:
                subsitute = subsitute_dict[old_item]
                new_line = new_line.replace(old_item,subsitute)
                # num = num + 1
                # print(str(num) + ': Change the ingredient "' + old_item + '" to "' + subsitute + '".')
        new_directions.add(new_line)

    str_temp = ""
    for record in add_dict:
        if str_temp == "":
            str_temp = str_temp+record
        else:
            str_temp = str_temp + ', '+record
    str_temp = 'Mix '+ str_temp + 'together with other materials.'
    new_directions.add(str_temp)
    print(str(num) + ': Add the direction "' + str_temp+'"')

    # print('Transfer ends after ' + str(num) + ' times of changes.')
    # print('The new directions:')
    # pprint.pprint(new_directions)
    return new_directions


def transform(recipe):
    new_ingredients, subsitute_dict, add_dict,num = indiafy_ingredients(recipe.ingredients,recipe.name)
    new_directions = indiafy_directions(recipe.directions, subsitute_dict, add_dict,num)
    recipe.directions = new_directions
    recipe.ingredients = new_ingredients
    recipe.name = recipe.name + "(Transformed to Indian)"
    return recipe


# def test():
#     url = 'https://www.allrecipes.com/recipe/44868/spicy-garlic-lime-chicken/'
#     recipe = utils.Recipe(url)
#     recipe_name = recipe.name
#     ingredients = recipe.ingredients
#     directions = recipe.directions
#     new_ingredients, subsitute_dict, add_dict = indiafy_ingredients(ingredients, recipe_name)
#     pprint.pprint(new_ingredients)
#     pprint.pprint(subsitute_dict)
#     pprint.pprint(add_dict)
#     new_directions = indiafy_directions(directions, subsitute_dict, add_dict)
#     pprint.pprint(new_directions)

# test()