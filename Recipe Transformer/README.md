# Natural-Language-Processing

## Project Description
### Recipe Transformer

Tasks include:
1. Accept the URL of a recipe from AllRecipes.com, and programmatically fetch the page.
2. Parse it into the recipe data representation your group designs. Your parser should be able to recognize:
  - Ingredients
    - Ingredient name
    - Quantity
    - Measurement (cup, teaspoon, pinch, etc.)
    - Descriptor (e.g. fresh, extra-virgin et.)
    - Preparation (e.g. finely chopped etc.)
    - Tools (e.g. pans, graters, whisks, etc.)
    - Methods
  - Primary cooking method (e.g. sauté, broil, boil, poach, etc.)
  - Steps – parse the directions into a series of steps that each consist of ingredients, tools, methods, and times
3. Ask the user what kind of transformation they want to do.
  - To and from vegetarian
  - To and from healthy
  - Style of cuisine
4. Transform the recipe along the requested dimension, using your system’s internal representation for ingredients, cooking methods, etc.
5. Display the transformed recipe in a human-friendly format.

Team Members:
- Xin Tong [@XinTongBUPT](https://github.com/XinTongBUPT)
- Yunwen Wang [@OREOmini](https://github.com/OREOmini)
- Zunran Guo [@Albert-Z-Guo](https://github.com/Albert-Z-Guo) 

## Getting Started
### Environment Setup
To install all the libraries/dependencies and prepare data used in this project, run
```
pip install -r requirements.txt
```

### Performance Evaluation
