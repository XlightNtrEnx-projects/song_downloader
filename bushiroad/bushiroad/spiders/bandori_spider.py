import scrapy
from scrapy.http import Response
import os
import re
import urllib.parse

class BandoriSpider:
    pass

def clean(string):
    cleaned = string
    invalid_filename_characters = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_filename_characters:
        if char in cleaned:
            valid = urllib.parse.quote(char)
            cleaned = cleaned.replace(char, valid)
    return cleaned
        
# to build urls for each category
scheme = 'https://'
subdo = 'bandori.'
sld = 'fandom'
tld = '.com'
subdi = '/wiki/Category:'
song_categories_url_encoded = ['Original_Songs', 'Cover_Songs', 'Extra_Songs']

# build song folders for each band
songs_dir = 'songs'
expected_band_names_of_category_page = ['Poppin\'Party', 'Afterglow', 'Pastel*Palettes', 'Roselia', 'Hello, Happy World!', 'Morfonica', 'RAISE A SUILEN', 'MyGO!!!!!', 'Others']
for name in expected_band_names_of_category_page:
    for category in song_categories_url_encoded:
        os.makedirs(os.path.join(songs_dir, clean(name), category), exist_ok=True)

class BandoriSpider(scrapy.Spider):
    name = "bandori"
    song_dl_count = 0
    songs_downloaded_and_saved = 0
    songs_found = 0
    start_urls = [scheme + subdo + sld + tld + subdi + category for category in song_categories_url_encoded]

    def parse(self, response: Response):
        category = self.get_song_category_of_category_page(response=response)
        band_names = self.get_band_names_of_category_page(response=response, category=category)
        # for each band, yield a request to each song link
        for band_name in band_names:
            song_links = self.get_song_links_for_band_of_category_page(response=response, band_name=band_name, category=category)
            for song_link in song_links:
                url: str = scheme + subdo + sld + tld + song_link
                cb_kwargs = {'category': category, 'band_name': band_name}
                yield scrapy.Request(url, self.parse_song_page, cb_kwargs=cb_kwargs)

    def parse_song_page(self, response: Response, category: str, band_name: str):
        dl_links = self.get_dl_links_of_song_page(response=response, category=category, band_name=band_name)
        file_names = self.get_file_names_of_dl_links(response=response, dl_links=dl_links) # url-decoded
        file_names = [clean(re.match(r'(.+)(\.[^.]+)', file_name).group(1).rstrip('.') + re.match(r'(.+)(\.[^.]+)', file_name).group(2)) for file_name in file_names] # trailing dots stripped then cleaned
        folder_name = self.get_folder_name(response=response, file_names=file_names) # folder_name is shortest file_name with extension removed 
        file_dir_path = f'{songs_dir}/{clean(band_name)}/{category}/{clean(folder_name)}'
        os.makedirs(file_dir_path, exist_ok=True)
        for (dl_link, file_name) in zip(dl_links, file_names, strict=True):
            file_path = os.path.join(file_dir_path, file_name)
            if not os.path.exists(file_path):
                cb_kwargs={'category': category, 'band_name': band_name, 'file_path': file_path}
                yield scrapy.Request(dl_link, self.parse_song_download_link, cb_kwargs=cb_kwargs)

    def parse_song_download_link(self, response: Response, category: str, band_name: str, file_path: str):
        content_type = response.headers.get('Content-Type').decode('utf-8')
        if 'ogg' in content_type:
            with open(file_path, 'wb') as music_file:
                music_file.write(response.body)
            self.songs_downloaded_and_saved += 1
            self.logger.info(f'Saved to {file_path}')
        else:
            self.logger.error(f'Unrecognized content type!')
    
    def get_song_category_of_category_page(self, response: Response):
        # original_songs, etc
        category: str = response.url.replace('https://bandori.fandom.com/wiki/Category:', '')
        if category not in song_categories_url_encoded:
            self.logger.error(f'Unexpected category {category} extracted from category page url at {response.url}')
            raise ValueError(f'Unexpected category {category} extracted from category page url at {response.url}')
        return category
    
    def get_band_names_of_category_page(self, response: Response, category: str):
        names = response.xpath('//tbody/tr/td[@class="navbox-group"]/text()').getall()
        for name in names:
            if name not in expected_band_names_of_category_page:
                self.logger.error(f'Unexpected band "{name}" found from {category} category page at {response.url}')
                raise ValueError(f'Unexpected band "{name}" found from {category} category page at {response.url}')
        if len(names) > 0:
            return names
        else: 
            self.logger.error(f'Could not find any bands from {category} category page at {response.url}')
            raise ValueError(f'Could not find any bands from {category} category page at {response.url}')

    def get_song_links_for_band_of_category_page(self, response: Response, band_name: str, category: str):
        # black shout, louder, etc for roselia; kizuna music, popping dream, etc for poppin'party
        links = response.xpath(f'//td[text()="{band_name}"]/following-sibling::td[position()=1]/div/a/@href').getall()
        if len(links) > 0:
            self.logger.info(f'Parsing {len(links)} {category} song links for {band_name}')
            self.songs_found += len(links)
            return links
        else: 
            self.logger.error(f'Could not find any songs for {band_name} from {category} category page at {response.url}')
            raise ValueError(f'Could not find any songs for {band_name} from {category} category page at {response.url}')

    def get_dl_links_of_song_page(self, response: Response, category: str, band_name: str):
        xpaths = ['//span[@id="Audio"]/parent::h2/following-sibling::table[position()=1][@class="article-table"]/tbody/tr[position()>1]/td/center/audio/@src',
                  '//span[@id="Audio"]/parent::h2/following-sibling::div[position()=1][@class="tabber wds-tabber"]/div[position()>1]/table/tbody/tr[position()>1]/td/center/audio/@src',
                  '//span[@id="Audios"]/parent::h2/following-sibling::div[position()=1][@class="tabber wds-tabber"]/div[position()>1]/table/tbody/tr[position()>1]/td/center/audio/@src',
                  '//span[@id="Audios"]/parent::h2/following-sibling::table[position()=1]/tbody/tr[position()>1]/td/center/audio/@src']
        dl_links = []
        for xpath in xpaths:
            dl_links = response.xpath(xpath).getall()
            dl_links_length = len(dl_links)
            if dl_links_length > 0:
                self.song_dl_count += dl_links_length
                return dl_links
        self.logger.error(f'Unable to get download links from song page {response.url} of {band_name} {category}')
        return dl_links
    
    def get_file_names_of_dl_links(self, response: Response, dl_links: list[str]):
        file_names = [urllib.parse.unquote(re.match(r'^(https://static\.wikia\.nocookie\.net/bandori/images/[^/]+/[^/]+/)([^/]+)', dl_link).group(2)) for dl_link in dl_links]
        file_names_length = len(file_names)
        dl_links_length = len(dl_links)
        if file_names_length != dl_links_length:
            self.logger.error(f'Retrieved {file_names_length} file names although there are {dl_links_length} dl_links at {response.url}')
            raise ValueError(f'Retrieved {file_names_length} file names although there are {dl_links_length} dl_links at {response.url}')
        return file_names
    
    def get_folder_name(self, response: Response, file_names: list[str]):
        if len(file_names) != 0:
            folder_name = file_names[0]
            for file_name in file_names:
                if len(file_name) < len(folder_name):
                    folder_name = file_name
            folder_name = re.match(r'(.+)(\.[^.]+)', folder_name).group(1)
            return folder_name
        else: 
            return ''
    
    def closed(self, reason):
        self.logger.info(f'Songs found: {self.songs_found}')
        self.logger.info(f'Song download links found: {self.song_dl_count}')
        self.logger.info(f'Links downloaded from and saved: {self.songs_downloaded_and_saved}')
