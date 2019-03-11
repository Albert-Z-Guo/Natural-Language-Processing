#-*- coding:utf-8 _*-  
""" 
@author:Xin TONG
@file: healthy.py 
@time: 2019/03/06
@site:  
@software: PyCharm 
"""
import requests
from bs4 import BeautifulSoup
import pprint

"""
For not healthy to healthy, we use the following food 'hacks':
    - https://www.goredforwomen.org/live-healthy/heart-healthy-cooking-tips/healthy-substitutions/
    - https://www.nhlbi.nih.gov/health/educational/lose_wt/eat/shop_lcal_fat.htm
    - https://www.swansonvitamins.com/blog/natural-health-tips/food-replacement-hacks
    - https://www.health24.com/Diet-and-nutrition/Weight-loss/Low-calorie-lower-fat-alternative-foods-20120721
    - https://www.healthline.com/nutrition/42-foods-low-in-calories#section1
    - https://www.eatthis.com/healthy-food-substitutes/
    - https://www.buzzfeed.com/rachelysanders/healthy-ingredient-swaps-substitutions
"""

class healthy_transfer(object):

    def __init__(self):

        self.to_healthy_dict = {
            'chocolate':'cocoa nibs',
            'muffin':'croissant',
            'sour cream':'greek non-fat yogurt',
            'white flour':'corn flour',
            'wheat flour':'gluten-free flour',
            'cheese':'low-fat cottage cheese',
            'creamer':'slim milk',
            'whole milk':'slim milk',
            'oatmeal':'quinoa',
            'granola': 'nuts',
            'pita': 'veggies',
            'jam': 'smashed avocado',
            'mayo': 'mustard',
            'pasta':'spaghetti squash',
            'sausage': 'bacon',
            'sushi rolls': 'sashimi',
            'burritos': 'bowls',
            'regular': 'fat-free dressing',
            'fries':'salad',
            'juice': 'soda water',
            'couscous': 'quinoa',
            'white rice': 'quinoa',
            'rice': 'quinoa',
            'iceberg': 'romaine',
            'vegetable oil': 'coconut oil',
            'butter':'coconut oil',
            'white sugar': 'stevia',
            'breadcrumbs': 'chia seeds',
            'bread crumbs': 'chia seeds',
            'pasta': 'spaghetti squash floss',
            'tortilla': 'lettuce leaves',
            'flour tortilla': 'corn tortilla',
            'flavored yogurt': 'greek yogurt',
            'canned fruit': 'fresh fruits',
            'white wine': 'red wine',
            'tonic water': 'soda water',
            'soy sauce': 'low-sodium soy sauce',
            'noodles': 'spaghetti squash floss',
            'bread': 'whole grain bread',
            'turkey': 'grass fed beef',
            'ice cream': 'frozen non-fat yogurt',
            'heavy cream':'slim milk',
            'syrup':'honey',
            'pork': 'tofu',
            'flour':'almond flour',
            'sugar': 'stevia',
            'salt': 'himalayan salt',
            'milk':'slim milk',
            'egg':'egg whites',
            'potato':'kale',
            'beef':'grass-fed beef',
            'steak':'eye of round steak',
            'chicken':'boneless, skinless chicken',
            'pork':'boneless, skinless pork',
            'turkey':'boneless, skinless turkey breast',
            'fish':'salmon',
            'mayo':'greek non-fat yogurt',
            'tortillas':'lettuce',
            'sauce':'low-fat sauce',
            'dressing':'low-fat dressing',
        # method
            'boil':'steam',
            'deep-fry':'bake',
            'fry':'bake',
            'fried':'baked',
            'deep-fried':'deep-baked',
            'oiled':'grilled'
        }

        self.from_healthy_dict = dict((v,k) for k,v in self.to_healthy_dict.items())

    # Transfer ingredients to healthy style
    def tohealthy_ingredients(self,ingredients):
        # print("\nTransfer ingredients to healthy style...")
        print("\nIngredients Change(s):")
        new_ingredients = set()
        is_healthy = False
        num_change = 0
        for line in ingredients:
            new_line = line
            # if unhealthy, helf the quantity
            for record in ["cheese", "cream", "butter", "sugar", "oil", "salt", "flour"]:
                if record in new_line:
                    list = new_line.split(' ')
                    new_quantity = 0
                    if '/' in list[0]:
                        temp = list[0].split('/')
                        new_quantity = float(temp[0]) / float(temp[1]) / 2
                    if list[0].isdigit():
                        new_quantity = float(list[0]) / 2
                    if new_quantity > 0:
                        old_quantity = list[0]
                        list[0] = str(new_quantity)
                        new_line = ' '.join(list)
                        num_change = num_change + 1
                        print(str(num_change)+': Change the quantity of "'+record+'" from "'+old_quantity+'" to "'+str(new_quantity)+'".')
            # if in unhealthy dict, change into its healthy alternatives
            for item in self.to_healthy_dict.keys():
                if item in new_line:
                    new_item = self.to_healthy_dict[item]
                    num_change = num_change + 1
                    new_line = new_line.replace(item, new_item)
                    print(str(num_change) + ': "' + item + '" to "' + new_item + '".')
            new_ingredients.add(new_line)
        # print('\nTransfer ends after '+str(num_change)+' times of changes.')
        if num_change < 3:
            is_healthy = True
        return new_ingredients,is_healthy,num_change

    # Transfer directions to healthy style
    def tohealthy_directions(self,directions,num):
        # print("\nTransfer directions to healthy style...")
        # print("\nDirections Change(s):")
        new_directions = set()
        for line in directions:
            new_line = line
            for item in self.to_healthy_dict.keys():
                if item in new_line:
                    new_item = self.to_healthy_dict[item]
                    # num = num + 1
                    new_line = new_line.replace(item, new_item)
                    # print(str(num) + ': "' + item + '" to "' + new_item + '".')
            new_directions.add(new_line)
        # print('\nTransfer ends after ' + str(num) + ' times of changes.')
        return new_directions

    def transform(self, recipe):
        new_ingredients,is_healthy,num = self.tohealthy_ingredients(recipe.ingredients)
        new_directions = self.tohealthy_directions(recipe.directions,num)
        if is_healthy == True:
            print("\n***Notice: the recipe is healthy enough, you don't need to transfer it!")
        recipe.directions = new_directions
        recipe.ingredients = new_ingredients
        recipe.name = recipe.name + "(Transfered to healthy)"
        return recipe

    # Transfer ingredients to unhealthy style
    def tounhealthy_ingredients(self, ingredients):
        # print("\nTransfer ingredients to unhealthy style...")
        new_ingredients = set()
        add_dict = []
        dict = {"cheese":False, "cream":False, "butter":False, "sugar":False, "oil":False, "salt":False, "flour":False}
        is_healthy = True
        num_change = 0
        print("\nIngredients Change(s):")
        for line in ingredients:
            new_line = line
            # if unhealthy, helf the quantity
            for record in ["cheese", "cream", "butter", "sugar", "oil", "salt", "flour"]:
                if record in new_line:
                    dict[record] = True
                    list = new_line.split(' ')
                    new_quantity = 0
                    if '/' in list[0]:
                        temp = list[0].split('/')
                        new_quantity = float(temp[0]) / float(temp[1]) * 2
                    if list[0].isdigit():
                        new_quantity = float(list[0]) * 2
                    if new_quantity > 0:
                        old_quantity = list[0]
                        list[0] = str(new_quantity)
                        new_line = ' '.join(list)
                        num_change = num_change + 1
                        print(str(
                            num_change) + ': Change the quantity of "' + record + '" from "' + old_quantity + '" to "' + str(
                            new_quantity) + '".')
            # if in unhealthy dict, change into its healthy alternatives
            for item in self.from_healthy_dict.keys():
                if item in new_line:
                    new_item = self.from_healthy_dict[item]
                    num_change = num_change + 1
                    new_line = new_line.replace(item, new_item)
                    print(str(num_change) + ': "' + item + '" to "' + new_item + '".')
            new_ingredients.add(new_line)

        # If ingredient is already in the recipe, then don't add
        if dict["cheese"] == False:
            new_ingredients.add("chopped cheese")
            num_change = num_change + 1
            print(str(num_change) + ': Add "chopped cheese"')
            add_dict.append("chopped cheese")
        if dict["cream"] == False:
            new_ingredients.add("2 tablespoon heavy cream")
            num_change = num_change + 1
            print(str(num_change) + ': Add "2 tablespoon heavy cream"')
            add_dict.append("2 tablespoon heavy cream")
        if dict["sugar"] == False:
            new_ingredients.add("2 tablespoon sugar")
            num_change = num_change + 1
            print(str(num_change) + ': Add "2 tablespoon sugar"')
            add_dict.append("2 tablespoon sugar")
        if dict["butter"] == False:
            new_ingredients.add("choppe butter")
            num_change = num_change + 1
            print(str(num_change) + ': Add "chopped butter"')
            add_dict.append("choppe butter")
        if dict["salt"] == False:
            new_ingredients.add("2 tablespoon salt")
            num_change = num_change + 1
            print(str(num_change) + ': Add "2 tablespoon salt"')
            add_dict.append("2 tablespoon salt")
        # print('\nTransfer ends.')
        if num_change < 3:
            is_healthy = False
        return new_ingredients,is_healthy, add_dict,num_change

    # Transfer directions to unhealthy style
    def tounhealthy_directions(self,directions, add_dict,num):
        # print("\nTransfer directions to unhealthy style...")
        # print("\nDirections Change(s):")
        new_directions = set()
        for line in directions:
            new_line = line
            for item in self.from_healthy_dict.keys():
                if item in new_line:
                    new_item = self.from_healthy_dict[item]
                    # num = num + 1
                    new_line = new_line.replace(item, new_item)
                    # print(str(num) + ': "' + item + '" to "' + new_item + '".')
            new_directions.add(new_line)

        # add some unhealthy ingredient
        str_temp = ""
        for record in add_dict:
            if str_temp == "":
                str_temp = str_temp + record
            else:
                str_temp = str_temp + ', ' + record
        str_temp = 'Mix ' + str_temp + ' together with other materials.'
        new_directions.add(str_temp)
        num = num + 1
        print(str(num) + ': Add the direction "' + str_temp + '"')
        # print('\nTransfer ends.')
        return new_directions

    def transform_tounhealthy(self, recipe):
        new_ingredients,is_healthy, add_dict,num = self.tounhealthy_ingredients(recipe.ingredients)
        new_directions = self.tounhealthy_directions(recipe.directions,add_dict,num)
        if is_healthy == False:
            print("\n***Notice: the recipe is unhealthy enough, you don't need to transfer it!")
        recipe.directions = new_directions
        recipe.ingredients = new_ingredients
        recipe.name = recipe.name + "(Transfered to unhealthy)"
        return recipe


# def test():
#     # url = 'https://www.allrecipes.com/recipe/216888/good-new-orleans-creole-gumbo/?internalSource=hub%20recipe&referringContentType=Search&clickId=cardslot%2013'
#     # url = 'https://www.allrecipes.com/recipe/263873/instant-pot-keto-chicken-and-kale-stew/?internalSource=similar_recipe_banner&referringId=179908&referringContentType=Recipe&clickId=simslot_4'
#     # url = 'https://www.allrecipes.com/recipe/78299/boilermaker-tailgate-chili/?internalSource=hub%20recipe&referringId=92&referringContentType=Recipe%20Hub&clickId=cardslot%2014'
#     # url = 'https://www.allrecipes.com/recipe/25713/best-italian-sausage-soup/'
#     url = 'https://www.allrecipes.com/recipe/242352/greek-lemon-chicken-and-potatoes/?internalSource=staff%20pick&referringId=17562&referringContentType=Recipe%20Hub'
#     page = requests.get(url)
#     soup = BeautifulSoup(page.content, 'html.parser')
#
#     # extract ingredients section from the webpage
#     ingredients = set([element.label.text.strip() for element in soup.find_all(class_='checkList__line')])
#     # remove unnecessary elements
#     ingredients.remove('')
#     ingredients.remove('Add all ingredients to list')
#
#     # extract directions section from the webpage
#     directions = [element.text.strip() for element in soup.find_all(class_='recipe-directions__list--item')]
#     # remove unnecessary elements
#     directions.remove('')

# test()