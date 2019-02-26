# Natural-Language-Processing

## Project Description
### Golden Globes Awards Identification via Tweets

Tweets (2015) used in this project were retrieved if they matched the query:
```python
track = ['gg', 'golden globes', 'golden globe', 'goldenglobe', 'goldenglobes', 'gg2015', 'gg15',
         'goldenglobe2015', 'goldenglobe15', 'goldenglobes2015', 'goldenglobes15', 'redcarpet', 
         'red carpet', 'redcarpet15', 'redcarpet2015', 'nominees', 'nominee', 'globesparty', 'globesparties']
```
Tweets (2013) used in this project were retrieved similarly, but with fewer keywords.

See [Twitter API "track" parameter](https://developer.twitter.com/en/docs/tweets/filter-realtime/guides/basic-stream-parameters) for details.

Identification tasks include:
1. Host(s)
2. Awards Names
3. Awards Presenters
4. Awards Nominees
5. Awards Winners
6. Red Carpet (Who was best dressed, worst dressed, most discussed, most controversial?)
7. Humor (What were the best jokes of the night, and who said them?)
8. Sentiment (What were the most common sentiments used with respect to the hosts, winners, presenters, and nominees?)

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
To download [NLTK](https://www.nltk.org/) package used, run
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


### To do:
- clean and modularize main.py
- take time series into account (e.g. searching within a time span say 2 minutes)
