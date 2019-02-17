# from time import time
# from warnings import warn
#
# from bs4 import BeautifulSoup, ResultSet
# from requests import get
#
#
# start_time = time()
# people_names = []
#
# file = open("people_names.txt", encoding="utf-8", mode="w")
# for page in range(1, 11):
#     url = "https://www.imdb.com/list/ls058011111/?sort=list_order,asc&mode=detail&page=" + str(page)
#     response = get(url)
#     elapsed_time = time() - start_time
#     print('Page {0} Request... elapsed time: {1:.2f} seconds'.format(page, elapsed_time))
#
#     # throw a warning for non-200 status codes
#     if response.status_code != 200:
#         warn('Page {0} Request... Status code: {}'.format(page, response.status_code))
#
#     html_soup = BeautifulSoup(response.text, 'html.parser')
#     actor_containers: ResultSet = html_soup.find_all('div', class_='lister-item mode-detail')
#
#     for container in actor_containers:
#         name = container.h3.a.text.strip()
#         people_names.append(name)
#         file.write(name + '\n')
# file.closed

try:
    with open('people_names.txt', 'r') as file:
        people_names = []
        for row in file:
            people_names.append(row.strip())
    file.closed
except:
    pass
print(people_names[:10])
