import pickle
import random

from recipe import Recipe


class ToNonVegetarian(Recipe):
    def __init__(self, url):
        Recipe.__init__(self, url)
        self.name += ' Transformed to Non-vegetarian'
        # load scraped data:
        # 4 pages of vegetarian protein recipes
        # 6 pages of meat recipes
        # 2 pages of seafood recipes
        with open('data/ingredients_categorized.pickle', 'rb') as file:
            ingredients_categorized = pickle.load(file)
        file.close()
        self.seafood_ingredient = ingredients_categorized['seafood']['ingredients']
        self.meat_ingredient = ingredients_categorized['meat']['ingredients']
        self.vegetarian_protein_ingredient = ingredients_categorized['vegetarian_protein']['ingredients']
        self.sub_dict = {}
        self.sub_dict_granular = {}

        # load selected meat list
        meat_dict = {}
        with open('data/selected_meat_ingredients.txt', 'r') as file:
            for line in file:
                meat_dict[line.strip()] = {}
        file.close()

        # populate ingredients' measurements, descriptors, and preparations from scraped data
        # we combined both meat and seafood
        for i in meat_dict:
            if i in ingredients_categorized['meat']['measurement']:
                meat_dict[i]['measurement'] = ingredients_categorized['meat']['measurement'][i]
            if i in ingredients_categorized['meat']['descriptor']:
                meat_dict[i]['descriptor'] = ingredients_categorized['meat']['descriptor'][i]
            if i in ingredients_categorized['meat']['preparation']:
                meat_dict[i]['preparation'] = ingredients_categorized['meat']['preparation'][i]

        for i in meat_dict:
            if i in ingredients_categorized['seafood']['measurement']:
                meat_dict[i]['measurement'] = ingredients_categorized['seafood']['measurement'][i]
            if i in ingredients_categorized['seafood']['descriptor']:
                meat_dict[i]['descriptor'] = ingredients_categorized['seafood']['descriptor'][i]
            if i in ingredients_categorized['seafood']['preparation']:
                meat_dict[i]['preparation'] = ingredients_categorized['seafood']['preparation'][i]

        # for ingredients not in scraped data, manually add general data
        for i in meat_dict:
            if i not in ingredients_categorized['meat']['measurement']:
                meat_dict[i]['measurement'] = ['pound']
            if i not in ingredients_categorized['meat']['descriptor']:
                meat_dict[i]['descriptor'] = ['fresh', 'raw', None]
            if i not in ingredients_categorized['meat']['preparation']:
                meat_dict[i]['preparation'] = ['cut into cubes']
        self.meat_dict = meat_dict

        # custom ingredients substitutions
        self.custom_to_vegetarian_dict = {'frankfurter':'vegetarian sausage',
                                            'meatball':'vegetarian meatball',
                                            'meatloaf':'tofu',
                                            'sausage':'vegetarian sausage',
                                            'bacon':'vegetarian bacon',
                                            'ham':'vegetarian ham',
                                            'skewer':'tofu skewer'}
        self.custom_from_vegetarian_dict = {v: k for k, v in self.custom_to_vegetarian_dict.items()}
        self.ingredients, self.sub_dict = self.generate_new_ingredients_and_sub_dict()
        self.sub_dict_granular = self.generate_sub_dict_granular()
        self.directions = self.generate_transformed_directions()


    def randomly_select(self, ls):
        if len(ls) == 0 or (len(ls) == 1 and ls[0] is None):
            return ''
        choice = random.choice(ls)
        if choice is None:
            return self.randomly_select(ls)
        else:
            return choice


    def substitue_with_meat(self, ingredient):
        if self.is_broth(ingredient):
            return 'chicken broth'
        if ingredient in self.custom_from_vegetarian_dict:
            return self.custom_from_vegetarian_dict[ingredient]
        return self.randomly_select(list(self.meat_dict.keys()))


    def is_broth(self, ingredient):
        if 'stock' in ingredient or 'consomme' in ingredient or 'bouillon' in ingredient or  'broth' in ingredient:
            return True
        return False


    def is_vegetable(self, ingredient):
        if ingredient in self.vegetarian_protein_ingredient:
            return True
        return False


    def generate_new_ingredients_and_sub_dict(self):
        sub_dict = {}
        new_ingredients = []
        replacement_num = 0

        for line in self.ingredients:
            quantity, measurement, descriptor, ingredient, preparation = self.extract_all(line)

            # if ingredient is vegetable
            if self.is_vegetable(ingredient):
                if replacement_num < 2:
                    sub = self.substitue_with_meat(ingredient)
                    sub_dict[ingredient] = {}

                    sub_quantity = '1/2'
                    sub_measurement = self.randomly_select(list(self.meat_dict[sub]['measurement']))
                    sub_descriptor = self.randomly_select(list(self.meat_dict[sub]['descriptor']))
                    sub_preparation = self.randomly_select(list(self.meat_dict[sub]['preparation']))

                    # record substitution information
                    sub_dict[ingredient]['substitution'] = sub
                    sub_dict[ingredient]['measurement'] = sub_measurement
                    sub_dict[ingredient]['descriptor'] = sub_descriptor
                    sub_dict[ingredient]['preparation'] = sub_preparation

                    # pick not None element only
                    replacement = []
                    for i in [sub_quantity, sub_measurement, sub_descriptor, sub]:
                        if i is not None:
                            replacement.append(i)
                    new_ingredients.append(' '.join(replacement))

                    # update replacement number
                    replacement_num += 1
                else:
                    new_ingredients.append(line)
            else:
                new_ingredients.append(line)
        return new_ingredients, sub_dict


    # expand sub_dict() for better granularity
    def generate_sub_dict_granular(self):
        sub_dict_granular = {}
        for ingredient in self.sub_dict.keys():
            if len(ingredient.split()) > 1:
                for word in ingredient.split():
                    sub_dict_granular[word] = {}
                    sub_dict_granular[word]['substitution'] = self.sub_dict[ingredient]['substitution']
                    sub_dict_granular[word]['measurement'] = self.sub_dict[ingredient]['measurement']
                    sub_dict_granular[word]['descriptor'] = self.sub_dict[ingredient]['descriptor']
                    sub_dict_granular[word]['preparation'] = self.sub_dict[ingredient]['preparation']
        return sub_dict_granular


    def generate_transformed_directions(self):
        replaced = set()
        new_directions = []

        for direction in self.directions:
            new_direction = direction
            bulk_substitution = False

            for ingredient in self.sub_dict.keys():
                if ingredient in direction:
                    new_direction = direction.replace(ingredient, self.sub_dict[ingredient]['substitution'])
                    bulk_substitution = True
                    for i in self.sub_dict[ingredient]['substitution'].split():
                        replaced |= {i}
                    print("\nReplaced '{0}' to '{1}'.".format(ingredient, self.sub_dict[ingredient]['substitution']))

            if not bulk_substitution:
                for word in self.sub_dict_granular.keys():
                    if word in new_direction and word not in replaced:
                        new_direction = new_direction.replace(word, self.sub_dict_granular[word]['substitution'])
                        for i in self.sub_dict_granular[word]['substitution'].split():
                            replaced |= {i}
                        print("\nReplaced '{0}' to '{1}'.".format(word, self.sub_dict_granular[word]['substitution']))

            new_directions.append(new_direction)
        return new_directions
