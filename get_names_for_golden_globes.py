import pandas as pd
import re
from urllib.request import urlopen
from bs4 import BeautifulSoup
import json
import pprint
from nltk.tokenize import RegexpTokenizer

year = '2013'
Html = urlopen('https://www.goldenglobes.com/winners-nominees/'+year+'/all').read()
soup = BeautifulSoup(Html,"html.parser")
film_match = soup.findAll("a", {"href": re.compile("/film/+")})
name_match = soup.findAll("a", {"href": re.compile("/person/+")})
tv_match = soup.findAll("a", {"href": re.compile("/tv-show/+")})
song_match = soup.findAll("a", {"href": re.compile("/song/+")})

entities_dict = {'film': [], 'name': [], 'song': [], 'tv': []}
count = 0
for year in range(2013, 2019):
    Html = urlopen('https://www.goldenglobes.com/winners-nominees/' + str(year) + '/all').read()
    soup = BeautifulSoup(Html, "html.parser")
    film_match = soup.findAll("a", {"href": re.compile("/film/+")})
    name_match = soup.findAll("a", {"href": re.compile("/person/+")})
    tv_match = soup.findAll("a", {"href": re.compile("/tv-show/+")})
    song_match = soup.findAll("a", {"href": re.compile("/song/+")})

    for match in film_match:
        if match.string is not None:
            entities_dict['film'].append(str(match.string))

    for match in name_match:
        if match.string is not None:
            entities_dict['name'].append(str(match.string))

    for match in song_match:
        if match.string is not None:
            entities_dict['song'].append(str(match.string))

    for match in tv_match:
        if match.string is not None:
            entities_dict['tv'].append(str(match.string))

pprint.pprint(entities_dict)
# Writing JSON data
with open('name_entities.json', 'w') as f:
    json.dump(entities_dict, f)
    print('write name data')
f.close()
