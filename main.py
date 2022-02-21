import csv
import pickle
import re
from datetime import datetime

import requestium
from fake_useragent import UserAgent
from lxml import html
from selenium import webdriver

from functions import *
from proxies import add_proxies_to_driver

ua = UserAgent()


class WayfairParser:
    def __init__(self, use_proxies=False):
        print('[START] Создание сессии')
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--log-level=3')
        self.proxies = None
        capabilities = None
        if use_proxies:
            self.proxies, capabilities = add_proxies_to_driver(chrome_options)
        self.session = requestium.Session(webdriver_path='./chromedriver', browser='chrome',
                                          default_timeout=15)
        self.session.headers.update({'user-agent': ua.chrome})
        # Чтобы добавить chrome_options
        self.session._driver = requestium.requestium.RequestiumChrome(
            './chromedriver',
            options=chrome_options,
            desired_capabilities=capabilities,
            default_timeout=15
        )
        self.session.driver.set_page_load_timeout(10)
        print('[START] Установка cookies')
        self.set_cookies()
        print('[START] Парсер запущен')

    def set_cookies(self):
        # Установка/создание cookies сессии
        check_file("cookies.txt")
        try:
            self.session.driver.get('https://www.wayfair.com/')
            if 'please verify that you are not a robot' in self.session.driver.page_source:
                input('Обнаружена капча...')
            else:
                for cookie in list(pickle.load(open(f"files/cookies.txt", "rb"))):
                    if isinstance(cookie, dict):

                        cookie_add = {'name': cookie.get('name'), 'value': cookie.get('value'),
                                      'path': cookie.get('path'),
                                      'secure': cookie.get('secure')}
                    else:
                        cookie_add = {'name': cookie.name, 'value': cookie.value, 'path': cookie.path,
                                      'secure': cookie.secure}
                    self.session.driver.add_cookie(cookie_add)
            self.session.transfer_driver_cookies_to_session()
        except:
            print("[INFO] Cookies не заданы")
            try:
                self.session.driver.get('https://www.wayfair.com/')
                if 'please verify that you are not a robot' in self.session.driver.page_source:
                    input('Обнаружена капча...')
                time.sleep(2)
                with open(f'files/cookies.txt', 'wb') as f:
                    pickle.dump(self.session.cookies, f)
                self.session.transfer_driver_cookies_to_session()
            except Exception as E:
                print("[ERROR] Ошибка получения cookies", E)
                return 0

    def get_page(self, url, page_number):
        # Парсинг определенной страницы с заданным url
        print('[GET]', url)
        # r = self.session.get(url, proxies=self.proxies)
        r = self.session.get(f"https://www.wayfair.com/a/manufacturer_browse/get_data?"
                             f"category_id=0"
                             f"&caid=0"
                             f"&maid={re.findall('-b[1-9]+', url)[0][2:]}"
                             f"&filter=a1234567890%7E2147483646"
                             f"&removed_nested_option="
                             f"&solr_event_id=0"
                             f"&registry_type=0"
                             f"&ccaid=0"
                             f"&curpage={page_number}"
                             f"&itemsperpage=48"
                             f"&refid="
                             f"&sku="
                             f"&search_id="
                             f"&collection_id=0"
                             f"&show_favorites_button=true"
                             f"&registry_context_type_id=0"
                             f"&product_offset=0"
                             f"&load_initial_products_only=false"
                             f"&only_show_grid=false"
                             f"&is_initial_render=false")
        save_file('last_page.html', r.text)
        if not r.ok:
            save_file('error.html', r.text)
            print('[ERROR] Ошибка запроса к сайту')
            return 0
        if 'curpage' in url and 'curpage' not in r.url:
            return []
        if not r.text:
            return []
        if 'We can\'t seem to find any products that match your search' in r.text:
            return []
        site_data = html.fromstring(r.text)
        element = site_data.xpath("//script[@id='wfAppData']")
        if element:
            site_json = json.loads(element[0].text)
            react_data_keys = list(site_json['wf']['reactData'].keys())
            products = site_json['wf']['reactData'][react_data_keys[0]]['bootstrap_data']['browse'][
                'browse_grid_objects']
        else:
            elements = site_data.xpath("//script")
            current_element = ''
            for element in elements:
                if 'browse_grid_objects' in str(element.text):
                    current_element = element.text
            current_element = current_element[current_element.find('{'):current_element.rfind('}') + 1]
            try:
                site_json = json.loads(current_element)
            except:
                return []
            products = site_json['application']['props']['browse']['browse_grid_objects']
        self.session.transfer_driver_cookies_to_session()
        with open(f'files/cookies.txt', 'wb') as f:
            pickle.dump(self.session.cookies, f)
        return products

    def get_pages(self, url):
        # Парсинг всех страниц определенного бренда
        if not url.split():
            return []
        if 'a1234567890~2147483646' not in url:
            url = url.replace('.html', '-a1234567890~2147483646.html')
        all_products = []
        for page_number in range(1, 200):
            current_page_url = url
            if page_number != 1:
                if '?' not in current_page_url:
                    current_page_url += f'?curpage={page_number}'
                else:
                    current_page_url += f'&curpage={page_number}'
            current_page_url = current_page_url.replace('sb0', 'sb1')
            current_page_products = trying(lambda: self.get_page(current_page_url, page_number))
            print('[INFO] Найдено товаров', len(current_page_products))
            if current_page_products == []:
                break
            all_products += current_page_products
        return all_products


def save_to_csv(products):
    # Сохранение списка спарсеных страниц
    with open(datetime.strftime(datetime.now(), "files/%d_%m_%Y-%H-%M-%S.csv"), 'w', encoding='UTF8',
              newline='') as csvfile:
        writer = csv.writer(csvfile)
        for number, product in enumerate(products):
            try:
                print(f"{number + 1}.", 'SKU:', product['sku'])
                print('URL', product['url'])
                print('Название:', product['product_name'])
                print('Бренд:', product['manufacturer'])
                row_to_write = [product['sku'], product['url'], product['product_name'], product['manufacturer']]
                if not product['raw_pricing_data']['pricing']:
                    print('Цена не указана')
                    row_to_write.append('None')
                else:
                    print('Цена:',
                          f"{product['raw_pricing_data']['pricing']['customerPrice']['quantityPrice']['value']}$")
                    row_to_write.append(
                        product['raw_pricing_data']['pricing']['customerPrice']['quantityPrice']['value'])
                print('Время доставки:', product['free_ship_text'])
                row_to_write.append(product['free_ship_text'])
                writer.writerow(row_to_write)
            except Exception as E:
                print("[ERROR] Ошибка получения информации о товаре", E)
                print(product)


def main():
    wp = WayfairParser(use_proxies=False)

    products = []
    for current_file_url in get_file('urls_waifair.txt', is_list=True):
        products += wp.get_pages(current_file_url)

    wp.session.driver.close()
    wp.session.close()

    save_to_csv(products)


if __name__ == '__main__':
    main()

