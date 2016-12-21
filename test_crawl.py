from crawler import *
from time import sleep 

def main():
	urls = [r'https://www.zomato.com/kolkata/kafe-6-2b-bhawanipur',
			r'https://www.zomato.com/kolkata/saldanha-bakery-wellesley',
			r'https://www.zomato.com/theteagrovedesapriyapark']
	driver = init_chromedriver()

	for url in urls:
		driver.get(url)
		source = get_source(driver)
		soup = source_to_soup(source)
		# print(soup.prettify())
		rev_count_block = soup.find_all('a', {'data-sort': 'reviews-dd'})[0]
		print(rev_count_block.contents[1].text)

if __name__ == '__main__':
	main()