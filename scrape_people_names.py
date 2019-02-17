from time import time
from warnings import warn

from bs4 import BeautifulSoup, ResultSet
from requests import get


start_time = time()
people_names = []
file = open("people_names.txt", encoding="utf-8", mode="w")

# scraping from IMDb
# Birth Date between 1960-01-01 and 1993-12-31, Males/Females
for page in range(1, 36953, 100):
    url = "https://www.imdb.com/search/name?birth_date=1960-01-01,1993-12-31&gender=male,female&count=100&start={0}&ref_=rlm".format(page)
    response = get(url)
    elapsed_time = time() - start_time
    print('scraped {0} people... elapsed time: {1:.2f} seconds'.format(page, elapsed_time))

    # throw a warning for non-200 status codes
    if response.status_code != 200:
        warn('scraped {0} people... Status code: {}'.format(page, response.status_code))

    html_soup = BeautifulSoup(response.text, 'html.parser')
    actor_containers: ResultSet = html_soup.find_all('div', class_='lister-item mode-detail')

    for container in actor_containers:
        name = container.h3.a.text.strip()
        people_names.append(name)
        file.write(name + '\n')
file.closed
