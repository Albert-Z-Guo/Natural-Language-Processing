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
        print("Transfer ingredients to healthy style...")
        new_ingredients = set()
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
                        print(str(num_change)+'. Change the quantity of "'+record+'" from "'+old_quantity+'" to "'+str(new_quantity)+'".')
            # if in unhealthy dict, change into its healthy alternatives
            for item in self.to_healthy_dict.keys():
                if item in new_line:
                    new_item = self.to_healthy_dict[item]
                    num_change = num_change + 1
                    new_line = new_line.replace(item, new_item)
                    print(str(num_change) + '. Change the ingredient "' + item + '" to "' + new_item + '".')
            new_ingredients.add(new_line)
        print('Transfer ends after '+str(num_change)+' times of changes.')
        print('The new ingredients:')
        pprint.pprint(new_ingredients)
        return new_ingredients

    # Transfer directions to healthy style
    def tohealthy_directions(self,directions):
        print("Transfer directions to healthy style...")
        new_directions = set()
        num = 0
        for line in directions:
            new_line = line
            for item in self.to_healthy_dict.keys():
                if item in new_line:
                    new_item = self.to_healthy_dict[item]
                    num = num + 1
                    new_line = new_line.replace(item, new_item)
                    print(str(num) + '. Change the ingredient "' + item + '" to "' + new_item + '".')
            new_directions.add(new_line)
        print('Transfer ends after ' + str(num) + ' times of changes.')
        print('The new directions:')
        pprint.pprint(new_directions)
        return new_directions


def test():
    # url = 'https://www.allrecipes.com/recipe/216888/good-new-orleans-creole-gumbo/?internalSource=hub%20recipe&referringContentType=Search&clickId=cardslot%2013'
    # url = 'https://www.allrecipes.com/recipe/263873/instant-pot-keto-chicken-and-kale-stew/?internalSource=similar_recipe_banner&referringId=179908&referringContentType=Recipe&clickId=simslot_4'
    # url = 'https://www.allrecipes.com/recipe/78299/boilermaker-tailgate-chili/?internalSource=hub%20recipe&referringId=92&referringContentType=Recipe%20Hub&clickId=cardslot%2014'
    # url = 'https://www.allrecipes.com/recipe/25713/best-italian-sausage-soup/'
    url = 'https://www.allrecipes.com/recipe/242352/greek-lemon-chicken-and-potatoes/?internalSource=staff%20pick&referringId=17562&referringContentType=Recipe%20Hub'
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')

    # extract ingredients section from the webpage
    ingredients = set([element.label.text.strip() for element in soup.find_all(class_='checkList__line')])
    # remove unnecessary elements
    ingredients.remove('')
    ingredients.remove('Add all ingredients to list')

    # extract directions section from the webpage
    directions = [element.text.strip() for element in soup.find_all(class_='recipe-directions__list--item')]
    # remove unnecessary elements
    directions.remove('')

    # pprint.pprint(ingredients)
    # pprint.pprint(directions)
    th = healthy_transfer()
    th.tohealthy_ingredients(ingredients)
    th.tohealthy_directions(directions)

test()