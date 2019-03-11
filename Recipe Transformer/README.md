# Natural-Language-Processing

## Project Description
### Recipe Transformer
Tasks include:
1. Accept the URL of a recipe from AllRecipes.com, and fetch the page.
2. Parse the page into the recipe data representation:
   - Ingredients
     - Ingredient name
     - Quantity
     - Measurement (e.g. cup, teaspoon, pinch, etc.)
     - Descriptor (e.g. fresh, dried, extra-virgin etc.)
     - Preparation (e.g. finely chopped, crushed etc.)
   - Tools (e.g. pans, graters, whisks, etc.)
   - Methods
     - Primary cooking method (e.g. sauté, broil, boil, poach, etc.)
     - Other cooking methods (e.g. chop, grate, stir, mince, etc.)
   - Steps (parse the directions into a series of steps that each consist of ingredients, tools, methods, and times)
3. Ask the user what kind of transformation they want to do:
   - To and from vegetarian
   - To and from healthy
   - To Southeast Asian
   - To Thai
   - To Indian
4. Transform the recipe along the requested dimension.
5. Display the transformed recipe in a human-friendly format.

External data source used:
* Tools:
  - [Kitchen Essential List: 71 of the Best Kitchen Cookware, Utensils, Tools & More](https://www.mealime.com/kitchen-essentials-list)
* Primary Cooking Methods:
  - [15 Basic Cooking Methods You Need to Know Slideshow](https://www.thedailymeal.com/cook/15-basic-cooking-methods-you-need-know-slideshow/slide-13)
* Other Cooking Methods:
  - [Wikibooks: Cooking Techniques](https://en.wikibooks.org/wiki/Cookbook:Cooking_Techniques)
* Spices and sauces:
  - [Britannica: List of herbs and spices](https://www.britannica.com/topic/list-of-herbs-and-spices-2024392)
  - [World Spice Merchant](https://www.worldspice.com/spices)
  - [Wikipedia: List of sauces](https://en.wikipedia.org/wiki/List_of_sauces)
  - [22 Common Herbs and Spices in Asian Cuisine](https://delishably.com/spices-seasonings/Herbs-and-Spices-in-Asian-Cooking)
  - [World Spice Merchant: Asian](https://www.worldspice.com/spices/spices-asia)

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
To download the [spaCy](https://spacy.io/) language model used in this project, run
```
python3 -m spacy download en
```
To install [NLTK](http://www.nltk.org/index.html) packages used, such as `'punkt'`, run:
```
python3 -m nltk.downloader all
```
### Performance Evaluation
To evaluate Recipe Transformer's performance, run:
```
python3 main.py
```
