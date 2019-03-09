from recipe import Recipe
from to_vegetarian import ToVegetarian
from to_non_vegetarian import ToNonVegetarian
import southeast_asian_transformation as southeast_asian
import thai_transformation as thai
import healthy_transformation as healthy
import india_transformation as india


def display_recipe(recipe):
    print('\nRecipe name:\n' + recipe.name + '\n')
    recipe.decompose_ingredients()
    print('Tool(s) used:\n' + ', '.join(recipe.tools))
    if len(recipe.cooking_methods) == 0:
        print('\nNo major cooking method(s) captured. The following cooking actions are captured instead:')
        print(', '.join(list(verb.lower() for verb in recipe.directions_verbs)))
    else:
        print('\nMajor cooking method(s):\n' + ', '.join(recipe.cooking_methods))
    print('\nCooking steps:')
    recipe.decompose_steps()


if __name__ == '__main__':
    # url = input('Please enter a recipe url: ')
    # url = 'https://www.allrecipes.com/recipe/180735/traditional-style-vegan-shepherds-pie/'
    # url = 'https://www.allrecipes.com/recipe/73634/colleens-slow-cooker-jambalaya/'
    # url = 'https://www.allrecipes.com/recipe/45736/chicken-tikka-masala'
    # vegetarian
    url = 'https://www.allrecipes.com/recipe/59661/spinach-enchiladas/'
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

        option = input('Please enter a character/number option: ')
        while (option not in possible_options):
            print('Invalid option! Try again.')
            option = input('Please enter a character/number option: ')

        if option == 'x':
            print('Exit program.')

        if option == '0':
            display_recipe(recipe)

        if option == '1':
            vegetarian_recipe = ToVegetarian(url)
            display_recipe(vegetarian_recipe)

        if option == '2':
            non_vegetarian_recipe = ToNonVegetarian(url)
            display_recipe(non_vegetarian_recipe)

        if option == '3':
            new_recipe = Recipe(url)
            heal = healthy.healthy_transfer()
            new_recipe = heal.transform(new_recipe)
            display_recipe(new_recipe)

        if option == '4':
            pass

        if option == '5':
            # Southeast Asian transform

            # get new copy of recipe
            new_recipe = Recipe(url)

            # transform_status:
            # 0: No need to transform, already southeast asia
            # 1: No futher modification needed, but can generate a new recipe
            # 2: Success
            transform_status, new_recipe = southeast_asian.transform(new_recipe)
            print(transform_status)
            if transform_status == 0:
                print('Already Southeast Style. No need to transform.')
            elif transform_status == 1:
                print('WARNING: Cannot be transform to southeast asia style!')
                op = input('Do you still want to process?(y/n):')
                if (op == 'y'):
                    display_recipe(new_recipe)
                elif (op == 'n'):
                    pass
                else:
                    print('Please try another transform category.')
            else:
                display_recipe(new_recipe)
            pass

        if option == '6':
            new_recipe = Recipe(url)
            new_recipe = thai.transform(new_recipe)
            display_recipe(new_recipe)

        if option == '7':
            new_recipe = Recipe(url)
            new_recipe = india.transform(new_recipe)
            display_recipe(new_recipe)
