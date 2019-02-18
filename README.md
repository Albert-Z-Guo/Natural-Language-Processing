# Natural-Language-Processing

## Project Description
### Golden Globes Host(s) and Awards Identification via Tweets

Tweets (2015) used in this project were retrieved if they matched the query:
```python
track = ['gg', 'golden globes', 'golden globe', 'goldenglobe', 'goldenglobes', 'gg2015', 'gg15',
         'goldenglobe2015', 'goldenglobe15', 'goldenglobes2015', 'goldenglobes15', 'redcarpet', 
         'red carpet', 'redcarpet15', 'redcarpet2015', 'nominees', 'nominee', 'globesparty', 'globesparties']
```
Tweets (2013) used in this project were retrieved similarly, but with fewer keywords.

See [Twitter API "track" parameter](https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters) for details.

Identification tasks include, but not limited to
1. Host(s)
2. Awards Names
3. Awards Presenters
4. Awards Nominees
5. Awards Winners

Team Members:
- Xin Tong [@XinTongBUPT](https://github.com/XinTongBUPT)
- Yunwen Wang [@OREOmini](https://github.com/OREOmini)
- Zunran Guo [@Albert-Z-Guo](https://github.com/Albert-Z-Guo) 

## Getting Started
### Installation
To install all the libraries/dependencies and prepare data used in this project, run
```
pip install -r requirements.txt
```
To download the [spaCy](https://spacy.io/) language model used in this project, run
```
python3 -m spacy download en
```
To download NLTK package used, run
```
nltk.download('punkt')
```
To retrieve external data used, run
```
python3 scrape_people_names.py
python3 scrape_film_names.py
```


### Performance Evaluation
To evaluate the performance of tasks on 2013's data, run:
```
python3 autograder.py 2013 [task]
```
where task options are `hosts`, `winner`, `presenters`, `awards`, `nominees`
