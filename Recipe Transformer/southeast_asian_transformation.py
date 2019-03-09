import main as utils
import random
import copy
import pprint
import re

sauces = set()
asian_sauces = set()

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

with open('data/southeast_asian_sauces.txt', 'r') as file:
    for line in file.readlines():
        asian_sauces.add(line.strip())
file.close()

with open('data/sauces.txt', 'r') as file:
    for line in file.readlines():
        sauces.add(line.strip())
file.close()

custom_to_eastasian_dict = {
    'butter': 'pork fat',   
    'consomme': 'dashi',
    'bouillon': 'dashi',
    'milk': 'coconut milk',
    'cream': 'coconut cream'
}
east_asian_keywords = ['asia', 'east asia', 'south asian', 'thai', 'chinese', 'japan', 'korea', 'malaysia', 'indonesia','vietnam']
subsitute_dict = {}

def randomly_select(ls):
    if len(ls) == 0 or (len(ls) == 1 and ls[0] is None):
        return ''
    choice = random.choice(ls)
    if choice is None:
        return randomly_select(ls)
    else:
        return choice

def transform(recipe):
    recipe_name = recipe.name

    # if such words shows up in the recipe name, no transformation needed
    for word in east_asian_keywords:
        if word in recipe_name.lower():
            need_eastasian_transform = False
            print(word)
            return 0, recipe

    eastasian_ingredient_appearance_count = transform_ingredients(recipe)
    transform_directions(recipe)

    if len(subsitute_dict.keys()) <= 1:
        force_transform(recipe)
        return 1, recipe

    # if (eastasian_ingredient_appearance_count > 4):
    #     need_eastasian_transform = False
    
    return 2, recipe

def transform_ingredients(recipe):
    # count the appearing time for easiesian ingredients to determine whether it needs transformation
    eastasian_ingredient_appearance_count = 0
    new_ingredients = []

    for line in recipe.ingredients:
        quantity, measurement, descriptor, ingredient, preparation = recipe.extract_all(line)
        new_ingredient = ingredient
        ingredient  = ingredient.lower()
        
        if ingredient in asian_spices or ingredient in asian_sauces:
            eastasian_ingredient_appearance_count+=1
        
        if ingredient in spices and ingredient not in asian_spices:
            sub_spice = randomly_select(list(asian_spices))
            # get different substitution spice
            while sub_spice in subsitute_dict:
                sub_spice = randomly_select(list(asian_spices))
            # record substitution information
            subsitute_dict[ingredient] = {}
            subsitute_dict[ingredient]['substitution'] = sub_spice
            subsitute_dict[ingredient]['measurement'] = measurement
            subsitute_dict[ingredient]['descriptor'] = None
            subsitute_dict[ingredient]['preparation'] = None

            new_ingredient = ' '.join([quantity, measurement, sub_spice])
            
        elif ingredient in sauces and ingredient not in asian_sauces:
            sub_sauce = randomly_select(list(asian_sauces))
            # get different substitution sauce
            while sub_sauce in subsitute_dict:
                sub_sauce = randomly_select(list(asian_sauces))
            subsitute_dict[ingredient] = {}
            subsitute_dict[ingredient]['substitution'] = sub_sauce
            subsitute_dict[ingredient]['measurement'] = measurement
            subsitute_dict[ingredient]['descriptor'] = None
            subsitute_dict[ingredient]['preparation'] = None

            new_ingredient = ' '.join([quantity, measurement, sub_spice])
            
        else:
            for i in list(custom_to_eastasian_dict.keys()):
                if (i in ingredient or ingredient in i) and custom_to_eastasian_dict[i] != ingredient:
                    sub = custom_to_eastasian_dict[i]
                    subsitute_dict[ingredient] = {}
                    subsitute_dict[ingredient]['substitution'] = sub
                    subsitute_dict[ingredient]['measurement'] = measurement
                    subsitute_dict[ingredient]['descriptor'] = descriptor
                    subsitute_dict[ingredient]['preparation'] = preparation
                    
                    # for situations like 'salted butter' / 'beef bouillon'
                    if i != ingredient and len(ingredient.split()) > 1:
                        subsitute_dict[i] = {}
                        subsitute_dict[i]['substitution'] = sub
                        subsitute_dict[i]['measurement'] = measurement
                        subsitute_dict[i]['descriptor'] = descriptor
                        subsitute_dict[i]['preparation'] = preparation

                    replacement = []
                    for i in [quantity, measurement, descriptor, sub]:
                        if i is not None:
                            replacement.append(i)   

                    new_ingredient = ' '.join(replacement)

        new_ingredients.append(new_ingredient)
    recipe.ingredients = new_ingredients
    return eastasian_ingredient_appearance_count

def transform_directions(recipe):
    new_directions = []
    for direction in recipe.directions:
        new_direction = direction
        for ingredient in subsitute_dict.keys():
            if ingredient in new_direction.lower():
                new_direction = re.sub(ingredient, subsitute_dict[ingredient]['substitution'], new_direction, flags=re.IGNORECASE)
            
        new_directions.append(new_direction)

    recipe.directions = new_directions

def force_transform(recipe):
    if len(subsitute_dict.keys()) == 1:
        add_mix_southeast_asian_spice(recipe)
    else:
        add_southeast_asian_sauce(recipe)
        add_mix_southeast_asian_spice(recipe)

def add_mix_southeast_asian_spice(recipe):
    # randomly choose 2 asia spice to add
    spice_list = []
    while len(spice_list) < 2:
        spice_list.append(randomly_select(list(asian_spices)))
        
    for spice in spice_list:
        new_ingredient = '1 tablespoon '+spice
        recipe.ingredients.append(new_ingredient)
        
    new_direction = 'Mix {0} and {1} well and add to our cuisine for more flavor.'.format(spice_list[0], spice_list[1])
    recipe.directions.append(new_direction)
    print(new_direction)

def add_southeast_asian_sauce(recipe):
    sauce = randomly_select(list(asian_sauces))
    recipe.ingredients.append('2 teaspoon of '+ sauce)
    new_direction = 'Add some {} to adjust the taste.'.format(sauce)
    recipe.directions.insert(-1, new_direction)
    

