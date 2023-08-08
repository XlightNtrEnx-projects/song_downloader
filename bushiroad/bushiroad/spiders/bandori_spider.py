from pathlib import Path
import logging
import scrapy
import datetime
from scrapy.http import Response
import os
from scrapy import Selector
import re
import urllib.parse

class BandoriSpider:
    pass

# to build bandori urls for each band
scheme = 'https://'
subdo = 'bandori.'
sld = 'fandom'
tld = '.com/'
subdi = 'wiki/'
band_names_url_encoded = ['Roselia', 'Poppin%27Party']

# build song folders for each band
expected_song_categories = ['Original Songs', 'Cover Songs', 'Other Songs (Original)', 'Other Songs (Cover)', 'Extra Songs']
songs_dir = 'songs'
for band_name in band_names_url_encoded:
    for song_category in expected_song_categories:
        os.makedirs(os.path.join(songs_dir, band_name, song_category), exist_ok=True)

# logger config
'''
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)
handler = logging.FileHandler(f'{os.path.join(log_dir, __name__ + datetime.datetime.today().strftime("%Y%m%d") + ".log")}')
handler.setFormatter(formatter)
logger = logging.getLogger(BandoriSpider.__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
''' 

class BandoriSpider(scrapy.Spider):
    name = "bandori"
    download_links_count = 0
    songs_saved = 0
    start_urls = [scheme + subdo + sld + tld + subdi + band_name for band_name in band_names_url_encoded]
    invalid_filename_characters = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']

    def parse(self, response: Response):
        # save html file to band_pages folder
        band_name: str = response.url.split("/")[-1] 
        self.save_band_page(response=response, band_name=band_name)
        # select container with all songs
        all_songs_selector: Selector = response.xpath('//span[@id="Songs"]/parent::h2/following-sibling::div[position()=1]')
        if len(all_songs_selector) != 1:
            self.logger.warning(f'An error has occured while selecting all the songs of {response.url}')
        # retrieve names of categories of songs: Original Songs, Cover Songs, Other Songs (Original), Other Songs (Cover), Extra Songs
        song_category_names: list[str] = self.get_names_of_categories_of_songs(response=response, all_songs_selector=all_songs_selector)
        # select group_of_songs_selectors
        group_of_songs_selectors: Selector = self.select_groups_of_songs_by_category(response=response, all_songs_selector=all_songs_selector)
        # starts extracting links to all songs
        links_extracted = 0
        for zipped in zip(song_category_names, group_of_songs_selectors, strict=True):
            songs: list[str] = zipped[1].xpath('li/span/a/@href').getall()
            if len(songs) > 0:
                for song in songs:
                    links_extracted += 1
                    yield scrapy.Request(scheme + subdo + sld + tld.replace('/', '') + song, self.parse_song_page, cb_kwargs={'song_category': zipped[0], 'band_name': band_name})
            else: 
                self.logger.warning(f'Could not find any {zipped[0]} song pages for {response.url}')
            self.logger.info(f'Extracted {len(songs)} {zipped[0]} links for {response.url}')
        self.logger.info(f'There are {links_extracted} songs for {band_name}')

    def parse_song_page(self, response: Response, song_category: str, band_name: str):
        dl_links = self.retrieve_all_dl_links(response=response, song_category=song_category, band_name=band_name)
        if dl_links is not None:
            if len(dl_links) > 0:
                for dl_link in dl_links:
                    self.download_links_count += 1
                    yield scrapy.Request(dl_link, self.parse_song_download_link, cb_kwargs={'song_category': song_category, 'band_name': band_name})

    def parse_song_download_link(self, response: Response, song_category: str, band_name: str):
        content_type = response.headers.get('Content-Type').decode('utf-8')
        if 'ogg' in content_type:
            file_name_url_encoded = re.match(r'^(https://static\.wikia\.nocookie\.net/bandori/images/[^/]+/[^/]+/)([^/]+)', response.url).group(2)
            file_name = urllib.parse.unquote(file_name_url_encoded)
            for invalid in self.invalid_filename_characters:
                if invalid in file_name:
                    valid = urllib.parse.quote(invalid)
                    self.logger.warning(f'Invalid character {invalid} detected for {file_name}')
                    self.logger.warning(f'Counterpart is {valid}')
                    file_name = file_name.replace(invalid, valid)
            file_path = f'{songs_dir}/{band_name}/{song_category}/{file_name}'
            if not os.path.exists(file_path):
                with open(file_path, 'wb') as music_file:
                    music_file.write(response.body)
                self.songs_saved += 1
        else:
            self.logger.warning(f'Unrecognized content type!')

    def get_names_of_categories_of_songs(self, response: Response, all_songs_selector: Selector):
        song_category_names = all_songs_selector.xpath('div[position()=1]/ul[@class="wds-tabs"]/li/div/a/text()').getall()
        song_category_names_length = len(song_category_names)
        expected_song_category_names_length = 5
        if song_category_names_length != expected_song_category_names_length:
            self.logger.warning(f'Found {song_category_names_length} instead of {expected_song_category_names_length} categories of songs for {response.url}')
        return song_category_names
    
    def save_band_page(self, response: Response, band_name: str):
        filename = f"{band_name}.html"
        filedir = 'band_pages'
        os.makedirs(filedir, exist_ok=True)
        pure_path = Path(filedir, filename)
        pure_path.write_bytes(response.body)

    def select_groups_of_songs_by_category(self, response: Response, all_songs_selector: Selector):
        group_of_songs_selectors = all_songs_selector.xpath('div[position()>1]/div/ul')
        group_of_songs_selectors_length = len(group_of_songs_selectors)
        expected_group_of_songs_selectors_length = 5 # Original Songs, etc etc
        if group_of_songs_selectors_length != expected_group_of_songs_selectors_length:
            self.logger.warning(f'Selected songs from {group_of_songs_selectors_length} instead of {expected_group_of_songs_selectors_length} categories for {response.url}')
        return group_of_songs_selectors

    def retrieve_all_dl_links(self, response: Response, song_category: str, band_name: str):
        dl_links_selector: Selector = response.xpath('//span[@id="Audio"]/parent::h2/following-sibling::table[position()=1]/tbody')
        if len(dl_links_selector) == 1: # First Selector
            dl_links = dl_links_selector.xpath('tr[position()>1]/td/center/audio/@src').getall()
            if len(dl_links) > 0:
                return dl_links
            else:
                self.logger.error(f'An error has occured while retrieving all download links of {song_category}: {response.url} for first selector')
                return None
        else: # Second selector
            dl_links_selector: Selector = response.xpath('//span[@id="Audios"]/parent::h2/following-sibling::div[position()=1][@class="tabber wds-tabber"]')
            if len(dl_links_selector) == 1:
                dl_links = dl_links_selector.xpath('div[position()>1]/table/tbody/tr[position()>1]/td/center/audio/@src').getall()
                if len(dl_links) > 0:
                    return dl_links
                else:
                    self.logger.error(f'An error has occured while retrieving all download links of {song_category}: {response.url} for second selector')
                    return None
            else: # Third selector
                dl_links_selector: Selector = response.xpath('//span[@id="Audios"]/parent::h2/following-sibling::table[position()=1]/tbody')
                if len(dl_links_selector) == 1:
                    dl_links = dl_links_selector.xpath('tr[position()>1]/td/center/audio/@src').getall()
                    if len(dl_links) > 0:
                        return dl_links
                    else:
                        self.logger.error(f'An error has occured while retrieving all download links of {song_category}: {response.url} for third selector')
                        return None
                else: # Fourth selector
                    self.logger.error(f'An error has occured while selecting all download links of {song_category}: {response.url}')
                    return None
                    '''
                    dl_links_selector: Selector = response.xpath('//span[@id="Audios"]/parent::h2/following-sibling::table[position()=1]/tbody')
                    if len(dl_links_selector) == 1:
                        links = dl_links_selector.xpath('tr[position()>1]/td/center/audio/@src').getall()
                        if len(links) > 0:
                            for link in links:
                                yield scrapy.Request(link, self.parse_song_download_link)
                        else:
                            self.logger.warning(f'An error has occured while retrieving all download links of {song_category}: {response.url} for third selector')  
                    else:  
                        self.logger.warning(f'An error has occured while selecting all download links of {song_category}: {response.url}')
                    '''
    
    def closed(self, reason):
        self.logger.info(f'Song download links found: {self.download_links_count}')
        self.logger.info(f'Songs saved: {self.songs_saved}')
