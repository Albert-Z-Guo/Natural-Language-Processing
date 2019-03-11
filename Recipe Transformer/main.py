from recipe import Recipe
from vegetarian import Vegetarian
from non_vegetarian import NonVegetarian
import southeast_asian
import thai
import healthy
import indian


def display_recipe(recipe):
    print('\nRecipe name:\n' + recipe.name + '\n')
    recipe.decompose_ingredients()
    print('Tool(s) used:\n' + ', '.join(recipe.tools))
    if len(recipe.cooking_methods) == 0:
        print('\nNo primary cooking method(s) captured. The following cooking actions/ingredients are captured instead:')
        print(', '.join(verb.lower() for verb in recipe.directions_verbs))
    else:
        print('\nPrimary cooking method(s):\n' + ', '.join(recipe.cooking_methods))
    print('\nCooking steps:')
    recipe.decompose_steps()


if __name__ == '__main__':
    url = input('Please enter a recipe url: ')
    print('\nInput url:\n' + url)

    recipe = Recipe(url)
    display_recipe(recipe)

    option = None
    possible_options = ['x', '0', '1', '2', '3', '4', '5', '6', '7']

    while (option != 'x'):
        print('\nNow transform original recipe to:')
        print('\tx. No transformation. Exit program.')
        print('\t0. No transformation. Show original recipe.')
        print('\t1. Vegetarian')
        print('\t2. Non-vegetarian (if original recipe is vegetarian)')
        print('\t3. Healthy')
        print('\t4. Non-healthy (if original recipe is healthy)')
        print('\t5. Southeast Asian')
        print('\t6. Thai')
        print('\t7. Indian')

        option = input('\nPlease enter a character/number option: ')
        while (option not in possible_options):
            print('Invalid option! Try again.')
            option = input('\nPlease enter a character/number option: ')

        if option == 'x':
            print('Exit program.')

        if option == '0':
            display_recipe(recipe)

        if option == '1':
            vegetarian_recipe = Vegetarian(url)
            display_recipe(vegetarian_recipe)

        if option == '2':
            non_vegetarian_recipe = NonVegetarian(url)
            display_recipe(non_vegetarian_recipe)

        if option == '3':
            new_recipe = Recipe(url)
            heal = healthy.healthy_transfer()
            new_recipe = heal.transform(new_recipe)
            display_recipe(new_recipe)

        if option == '4':
            new_recipe = Recipe(url)
            heal = healthy.healthy_transfer()
            new_recipe = heal.transform_tounhealthy(new_recipe)
            display_recipe(new_recipe)

        if option == '5':
            new_recipe = Recipe(url)
            transform_status, new_recipe = southeast_asian.transform(new_recipe)
            # transform_status:
            # 0: No need to transform, already southeast asia
            # 1: Dispalay the recipe
            # 2: No display needed
            if transform_status == 0:
                print('\nAlready Southeast Style. No need to transform.')
            elif transform_status == 1:
                display_recipe(new_recipe)
            else:
                pass

        if option == '6':
            new_recipe = Recipe(url)
            new_recipe = thai.transform(new_recipe)
            display_recipe(new_recipe)

        if option == '7':
            new_recipe = Recipe(url)
            new_recipe = indian.transform(new_recipe)
            display_recipe(new_recipe)
