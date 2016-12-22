import re
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from time import sleep
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
import networkx as nx
from datetime import datetime

G_follow = nx.DiGraph()
G_follow.name = 'Zomato follower network'
# TIME = 5

# pickle the user and restaurant objects in files

# user_dict = {}  # stores the user objects with entity-id as the key
# rest_dict = {}  # stores the restaurant objects with entity-id as the key


class Restaurant:
    def __init__(self, link):
        self.link = link
        self.name = None
        self.entity_id = None
        self.cuisines = None
        self.review_count = None
        self.geo_loc = None
        self.get_info()
        # self.reviews = self.get_reviews()

    def __repr__(self):
        return '{} | {} | {} |'.format(self.name, self.entity_id, self.link)

    def __str__(self):
        return '{} | {} | {} | {} | {} | \n'.format(self.name, self.entity_id, self.geo_loc, self.link, self.cuisines)

    def get_reviews(self):
        """
        Get all the reviews of a restaurant
        :return: List of Review objects
        """
        driver = init_chromedriver()
        driver.get(self.link + r'/reviews')

        # click on the button 'All reviews'
        sleep(5)

        try:
            el = driver.find_element_by_css_selector('#selectors > a.item.default-section-title.everyone.empty')
            webdriver.ActionChains(driver).move_to_element(el).click(el).perform()
        except NoSuchElementException:
            pass
        # driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        sleep(5)
        load_more = '#reviews-container > div.notifications-content > div.res-reviews-container.res-reviews-area > div > div > div.mt0.ui.segment.res-page-load-more.zs-load-more > div.load-more.bold.ttupper.tac.cursor-pointer.fontsize2'
        while element_present(driver, load_more):
            try:
                el2 = driver.find_element_by_css_selector(load_more)
                driver.execute_script("return arguments[0].scrollIntoView();", el2)
                driver.execute_script("window.scrollBy(0, -150);")
                sleep(2)
                webdriver.ActionChains(driver).move_to_element(el2).click(el2).perform()
            except StaleElementReferenceException:
                break

        print('All reviews are loaded'.format(self.review_count))
        
        source = get_source(driver)
        # print(source)
        filename = driver.current_url.split('/')[-2]
        write_to_file(source, filename, 1) # 1 for Resto

        soup = source_to_soup(source)
        # print('-------------------------')
        # print(soup.prettify())
        # print('--------------------------')
        # review_blocks = soup.find_all('div', class_=re.compile('ui segments res-review-body'))
        # review_blocks = soup.find_all('div', {'data-snippet': 'restaurant-review'})
        review = (soup.find('div', class_='ui segment clearfix  br0 '))
        
        review_blocks = (soup.find_all('div', class_='ui segment clearfix  brtop '))
        if len(review_blocks) == 0 or self.review_count == 0:
            print('Error in parsing reviews...\n')
            return 
        print('Loaded {} reviews'.format(len(review_blocks)+1))
        

        with open('restaurant_reviews.txt', 'a', encoding='utf-8') as f:
            
            f.write('\n\n-------------\t{}\t------------------\n\n'.format(datetime.now()))
            f.write('{}\n\n'.format(self))
            
            reviews = []
            name_and_link = review.find('div', class_='header nowrap ui left')
            u_link = name_and_link.contents[1].attrs['href']
            u_entity_id = int(name_and_link.contents[1].attrs['data-entity_id'])
            rating_and_rev_text = review.find('div', text='Rated')
            
            r = Review()
            r.user = User(u_link, u_entity_id)
            r.restaurant = self
            r.time = review.find('time').attrs['datetime']
            r.rating = float(rating_and_rev_text.attrs['aria-label'].split()[-1])
            r.review_text = rating_and_rev_text.parent.contents[2].strip()
            reviews.append(r)
            
            print('({}) {} {}'.format('0', r.time , u_link))
            f.write('{}\n'.format(r))
            f.write('\n----------------------------------\n')
           
            for i, review in enumerate(review_blocks):
                name_and_link = review.find('div', class_='header nowrap ui left')
                u_link = name_and_link.contents[1].attrs['href']
                u_entity_id = int(name_and_link.contents[1].attrs['data-entity_id'])
                rating_and_rev_text = review.find('div', text='Rated')

                r = Review()
                r.user = User(u_link, u_entity_id)
                r.user_link = u_link
                r.restaurant = self
                r.time = review.find('time').attrs['datetime']
                r.rating = float(rating_and_rev_text.attrs['aria-label'].split()[-1])
                r.review_text = rating_and_rev_text.parent.contents[2].strip()
                reviews.append(r)
                
                print('({}) {} {}'.format(i + 1, r.time , u_link))
                f.write('({}) {}\n'.format(i + 1, r))

            f.write('\n----------------------------------\n')

        return reviews

    def get_info(self):
        """
        Populates the name, cuisines, entity_id,....
        :return: list of cuisines (str)
        """

        print('Visiting ', self.link)
        soup = extract_link(self.link)

        if soup is None:
            return

        self.name = soup.find('a', class_='ui large header left').text.strip()
        self.entity_id = int(soup.find(id='resinfo-wtt').attrs['data-entity-id'])
       # review_count = soup.find('a', {'href': '{}/reviews'.format(self.link), 'class': 'item respageMenu-item '}).text
        # reviews_count = list(soup.find('div', class_='review-sorting text-tabs selectors ui secondary pointing menu mt0').children)
        try:
            rev_count_block = soup.find_all('a', {'data-sort': 'reviews-dd'})[0]        
            self.review_count = int(rev_count_block.contents[1].text)
        except IndexError:
            rev_count = 0

        print('reviews #{}'.format(self.review_count))

        cuisine_block = soup.find('div', class_='res-info-cuisines clearfix')
        list_of_cuisines = []
        for cuisine in cuisine_block.find_all('a', class_='zred'):
            list_of_cuisines.append(cuisine.text.strip())

        self.cuisines = list_of_cuisines

        # geo location
        try:

            loc_text = soup.find(id='res-map-canvas').next_sibling.next_sibling.text.strip()
            lat, long = loc_text[loc_text.find('{') + 1: loc_text.find('}')].split(',')
            lat = float(lat[lat.find(':') + 2:])
            long = float(long[long.find(':') + 2:])
            self.geo_loc = (lat, long)
        except AttributeError:
            self.geo_loc = None   # restaurant's GPS location is not available

class Review:
    def __init__(self):
        self.user = None
        self.user_link = None
        self.restaurant = None
        self.time = None
        self.rating = None
        self.review_text = None

    def __repr__(self):
        return '{} | Rating: {} | {} | '.format(self.restaurant.name, self.rating, self.time)

    def __str__(self):
        return '{} | {} | {} | {} | {} | {} | {} |\n '.format(self.restaurant.name, self.user.name, self.user_link, self.user.entity_id, self.rating, self.time, self.review_text)


class User:
    def __init__(self, link, entity_id):
        self.name = None
        self.entity_id = entity_id
        self.location = None
        self.link = link
        self.reviews_count = None
        self.followers_count = None
        self.been_there_count = None
        self.reviews = None
        self.init_user()

    def __str__(self):
        return '{} | {} | {} | ' \
               '{} | reviews: {} | followers: {} | been there: {} | '.format(self.name,
                                                                          self.entity_id,
                                                                          self.location,
                                                                          self.link,
                                                                          self.reviews_count,
                                                                          self.followers_count,
                                                                          self.been_there_count)

    def __repr__(self):
        return '{} | {} | {} | '.format(self.name, self.entity_id, self.link)

    def followers(self):
        """
        Gets the followers of the user as a list of users
        :return: generator of followers
        """
        followers = []
        driver = init_chromedriver()
        driver.get(self.link + r'/network')

        sleep(10)
        while len(driver.find_elements_by_class_name('load-more')) > 1:  # one for Followers, other for Following
            print('Clicking load more!')
            element = driver.find_element_by_class_name('load-more')
            driver.execute_script("return arguments[0].scrollIntoView();", el2)
            driver.execute_script("window.scrollBy(0, -150);")
            ac = ActionChains(driver).move_to_element(element)
            ac.click().perform()
            sleep(5)
        sleep(20)

        source = get_source(driver)
        filename = driver.current_url.split('/')[-2]
        write_to_file(source, filename, 2)
        soup = source_to_soup(source)

        # now to find all the followers!!
        elements = soup.find_all('div', class_='header nowrap')
        print('{} has {} followers'.format(self.name, self.followers_count))
        
        with open('followers', 'a', encoding='utf-8') as f:
            f.write('\n\n-------------\t{}\t------------------\n\n'.format(datetime.now()))
            f.write('{}\nFollowers\n'.format(self))
            for i, element in enumerate(elements[: self.followers_count]):
                dic = element.contents[1].attrs
                follower = User(link=dic['href'], entity_id=int(dic['data-entity_id']))
                if follower is None:
                    continue

                f.write('({}) {}\n'.format(i + 1, follower))
                # print('({}) Adding edge between {} and {}'.format(i + 1, self.name, follower.name))
                # yield follower
                # followers.append(follower)
                # G.add_edge(self, follower)

        print('Successfully parsed all the followers')
        # print(followers[: 2])
        # print('-------------------')
        # return followers

    def get_reviews(self):
        """
        Get all the reviews
        :return: list of Review objects
        """
        driver = init_chromedriver()
        driver.get(self.link + r'/reviews')
        sleep(2)

        while True:
            while True:
                elements = driver.find_elements_by_css_selector(r'#reviews-container > div > div.bt.zs-load-more.mtop > div.load-more.ui.segment.tac')
                if len(elements) == 0:
                    break
                ac = ActionChains(driver).move_to_element(elements[0])
                ac.click().perform()
                sleep(5)

            print('Done loading {} reviews...'.format(self.reviews_count))
            # sleep(10)

            source = get_source(driver)
            filename = driver.current_url.split('/')[-2]
            write_to_file(source, filename, 3)
            soup = source_to_soup(source)

            # finding all reviews
            review_blocks = soup.find_all('div', class_='ui segment brtop')
            print('No of reviews: {}'.format(len(review_blocks)))

            if len(review_blocks) != 0:
                break

        self.reviews = []

        for review_block in review_blocks:
            review_header = review_block.find('div', class_='res-review-header')  # resto name, resto link, timestamp
            review_body = review_block.find('div', class_='res-review-body')

            name_and_link = review_header.find('a', {'data-entity_type': 'RESTAURANT'})

            restaurant = Restaurant(name_and_link.attrs['href'])
            restaurant.name = name_and_link.contents[0]
            restaurant.entity_id = name_and_link.attrs['data-entity_id']

            review = Review()
            review.restaurant = restaurant
            review.time = review_header.find('time').attrs['datetime']
            review.rating = float(review_body.find('div', string='Rated').attrs['aria-label'].split()[-1])
            review.review_text = review_body.find('div', class_='rev-text').text.strip().replace('Rated ', '')

            self.reviews.append(review)

        print('Parsed {} reviews'.format(len(self.reviews)))

    def init_user(self):
        """
            initializes the user - populates name, id, location, no of reviews, followers, been there
            :return: an User object
        """
        soup = extract_link(self.link)
        if soup is None:
            return None

        name_and_link = list(soup.find('div', class_='user-header-info-middle').children)[1].contents[1].contents[0]
        self.name = name_and_link.contents[0].strip()
        self.link = name_and_link.attrs['href']

        try:
            self.location = soup.find('div', class_='meta ').contents[0].strip()
        except AttributeError:
            self.location = None
        self.reviews_count = int(list(soup.find('a', {'data-tab': 'reviews'}).children)[1].contents[0])
        self.followers_count = int(list(soup.find('a', {'data-tab': 'network'}).children)[1].contents[0])
        self.been_there_count = int(list(soup.find('a', {'data-tab': 'beenthere'}).children)[1].contents[0])


def source_to_soup(page_source):
    """
    takes in page source, removes br tags and makes a Beautiful Soup object
    """
    page_source = re.sub('<br>', '', page_source)
    page_source = re.sub('<br/', '', page_source)
    page_source = re.sub('<br />', '', page_source)
    return BeautifulSoup(page_source, 'html.parser')


def extract_link(url):
    """
    Creates a BeautifulSoup object from the link
    :param url: the link
    :return: a BeautifulSoup object equivalent of the url
    """
    headers = {"Host": "www.zomato.com",
               "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:50.0) Gecko/20100101 Firefox/50.0",
               "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.5",
               "Accept-Encoding": "gzip, deflate, br",
               "Referer": "https://www.zomato.com/",
               "Connection": "keep-alive"}

    if url.startswith('file'):
        with open(url.replace('file:\\\\', ''), encoding='utf-8') as fp:
            page_source = fp.read()

    else:
        r = requests.get(url, headers=headers)
        if r.status_code == 404:
            return None
        page_source = r.text

    page_source = re.sub('<br>', '', page_source)
    page_source = re.sub('<br />', '', page_source)
    page_source = re.sub('<br/>', '', page_source)
    soup = BeautifulSoup(page_source, 'html.parser')

    return soup


def init_chromedriver():
    """
    Initializes the chromedriver to not to load images
    :return: A chromedriver object
    """
    chrome_options = webdriver.ChromeOptions()
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    return webdriver.Chrome('./chromedriver', chrome_options=chrome_options)


def element_present(driver, css_sel):
    try:
        driver.find_element_by_css_selector(css_sel)
        return True
    except NoSuchElementException:
        return False


def get_source(driver):
    """
    Returns the page source - waits until it detects <html> tag
    :param driver:
    :return: the page source
    """
    sleep(5)
    while True:
        source = driver.page_source
        if '<html' in source:
            return source
        else:
            print('Waiting for page to load')
            sleep(5)


def write_to_file(source, filename, type):
    """
    Writes the source to a file. 
    Type = 1 for Restaurant review, 2 for user follower, 
    3 for user review
    """
    path = './scraped_pages'
    #path = '/home/administrator/zomato_crawler/results/scraped_pages'
    if type == 1:
        path += '/Restaurants/' + filename
    elif type == 2:
        path += '/Users/Followers/' + filename
    elif type == 3:
        path += '/Users/Reviews/' + filename

    with open(path, 'w', encoding='utf-8') as f:
        f.write(source)

    print('Source saved for {}'.format(filename))    


def f():
    links = [r'https://www.zomato.com/users/sushenjit-ghosh-32007192',
             r'https://www.zomato.com/users/kashif-ahmed-1115831',
             r'https://www.zomato.com/sanjaynpunjabi',
             r'https://www.zomato.com/users/abhirup-chakravarty-13825351',
             r'https://www.zomato.com/users/bhupender-bora-36305051']
    user = User(link=links[-2], entity_id=13825351)
    print(user)
    user.get_reviews()
    # user_reviews = user.reviews

    for follower in user.followers():
        follower.get_reviews()
        # follower_reviews = follower.reviews
        print(follower.name)
        # common_reviews = user_reviews & follower_reviews
        
        for user_rev, foll_rev in zip(user.reviews, follower.reviews):
            print('User review: {}'.format(user_rev))
            print('Follower review: {}'.format(foll_rev))
    
         
            if user_rev.entity_id == foll_rev.entity_id:
                print('\n----\nCommon reviews: ')
                print('User review: {}'.format(user_rev))
                print('Follower review: {}'.format(foll_rev))
        break


def g():
    links = [r'https://www.zomato.com/users/sushenjit-ghosh-32007192',
             r'https://www.zomato.com/users/kashif-ahmed-1115831',
             r'https://www.zomato.com/sanjaynpunjabi',
             r'https://www.zomato.com/users/abhirup-chakravarty-13825351',
             r'https://www.zomato.com/users/bhupender-bora-36305051']
    #r'https://www.zomato.com/kolkata/arsalan-park-circus-area',
    restaurants = [
                   r'https://www.zomato.com/kolkata/desi-lane-alipore',
                   r'https://www.zomato.com/kolkata/an-idea-park-circus-area',
                   r'https://www.zomato.com/kolkata/monkey-bar-camac-street-area',
                   r'https://www.zomato.com/kolkata/saldanha-bakery-wellesley',
                   r'https://www.zomato.com/kolkata/kafe-6-2b-bhawanipur',
                   r'https://www.zomato.com/kolkata/the-firefly-24x7-cafe-rajarhat-new-town',
                   r'https://www.zomato.com/kolkata/eagle-boys-pizza-ruby-hospital-area',
                   r'https://www.zomato.com/kolkata/arsalan-park-circus-area']

    ##not working with last link, always scraping one less
    #u = User(links[1], 1115831)
    #print(set(u.followers()))
    # Restaurant(restaurants[0])
    # Restaurant(restaurants[1])
    user_link = []
    #for i in restaurants:
    r = Restaurant(restaurants[-1])
    rev = r.get_reviews()

    #storing user links for resto
    # for i,review in enumerate(rev):
    #     print("hii",type(review)
        #user_link.append(review)

    #iterating the user list for follower network
    #for i,user in enumerate(user_link):

def h():
    user_links = [r'https://www.zomato.com/users/saumajeet-deb-689078']
    u = User(user_links[0], 689078) 
    u.followers()   

def main():
    # h()
    g()

if __name__ == '__main__':
    main()
