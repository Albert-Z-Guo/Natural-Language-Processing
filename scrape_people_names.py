import pickle
from time import time
from warnings import warn

from bs4 import BeautifulSoup, ResultSet
from requests import get


def scrape():
    start_time = time()
    people_names = set()

    # scraping from IMDb
    # Birth Date between 1955-01-01 and 1993-12-31, Males/Females (Sorted by Popularity Ascending)
    # there are in total 205,045 names, we pick 20504, which are the top 10%
    for page in range(1, 20504, 100):
        url = "https://www.imdb.com/search/name?birth_date=1955-01-01,1993-12-31&gender=male,female&count=100&start={0}&ref_=rlm".format(page)
        response = get(url)
        elapsed_time = time() - start_time
        print('scraped {0} people... elapsed time: {1:.2f} seconds'.format(page, elapsed_time))

        # throw a warning for non-200 status codes
        if response.status_code != 200:
            warn('scraped {0} people... Status code: {}'.format(page, response.status_code))

        html_soup = BeautifulSoup(response.text, 'html.parser')
        containers: ResultSet = html_soup.find_all('div', class_='lister-item mode-detail')

        for container in containers:
            name = container.h3.a.text.strip()
            people_names |= {name}

    with open('people_names.pickle', 'wb') as file:
        pickle.dump(people_names, file, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == '__main__':
    scrape()
