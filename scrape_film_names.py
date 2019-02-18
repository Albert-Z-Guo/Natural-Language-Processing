from time import time
from warnings import warn
import re

from bs4 import BeautifulSoup, ResultSet
from requests import get
import json

start_time = time()

film_names = {}

# scraping from IMDb
# films & tvs released between 2010-01-01 and 2019-01-01
# there are in total  283,154 names, we pick  approximately top 2400 which are the top 10%
for page in range(1, 50):
    url = "https://www.imdb.com/search/title?release_date=2010-01-01,2019-01-01&user_rating=6.0,10.0&start={0}&ref_=rlm".format(page)
    response = get(url)
    elapsed_time = time() - start_time
    # print('scraped {0} people... elapsed time: {1:.2f} seconds'.format(page, elapsed_time))

    # throw a warning for non-200 status codes
    if response.status_code != 200:
        warn('scraped {0} people... Status code: {}'.format(page, response.status_code))

    html_soup = BeautifulSoup(response.text, 'html.parser')
    actor_containers: ResultSet = html_soup.find_all('div', class_='lister-item mode-advanced')

    for container in actor_containers:
        name = container.h3.a.text.strip()
        year = re.findall("\d+", container.h3.find_all('span')[1].text)[0]
        if year in film_names:
            film_names[year].append(name)
        else:
            l = [name]
            film_names[year] = l

with open('film_names.json', 'w') as f:
    json.dump(film_names, f)
    print('write name data')
f.close()
end = time()
print('total scraping film names time: {0:.2f} seconds'.format(end - start_time))