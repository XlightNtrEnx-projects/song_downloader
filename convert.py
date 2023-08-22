from pydub import AudioSegment
import os
import logging
import datetime


formatter = logging.Formatter(
    u'%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_path = os.path.join('convert_logs', f'convert_{datetime.date.today()}.log')
handler = logging.FileHandler(log_path, encoding='utf8')
handler.setFormatter(formatter)
logger = logging.getLogger('convert')
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


converted = 0
files_scanned = 0


dir_walk = os.path.join('bushiroad', 'songs')
for root, d_names, f_names in os.walk(dir_walk):
    if len(f_names) > 0:
        f_name = f_names[0]
        files_scanned += 1
        f_path = os.path.join(root, f_name)
        (f_path_no_ext, ext) = os.path.splitext(f_path)
        (band_name, category) = root.split(os.sep)[
            2:4]  # f'bushiroad/songs/{band_name}/{song_category}/{song_name}/{song_name}_{song_type}.ogg'
        new_f_path = os.path.split(f_path)[0].replace(dir_walk, os.path.join(
            'output', 'base_songs_mp3')) + f' {band_name}_{category}' + '.mp3'  # f'output/base_songs_mp3/{band_name}/{song_category}/{song_name} {band_name}_{song_category}'
        if not os.path.exists(new_f_path):
            ogg = AudioSegment.from_ogg(f_path)
            os.makedirs(os.path.split(new_f_path)[0], exist_ok=True)
            logger.info(f'Converted {f_name} and saved it to {new_f_path}')
            ogg.export(new_f_path, format='mp3')
            converted += 1
        else:
            logger.debug(
                f'Did not convert {f_name} as it already exists at {new_f_path}')


logger.info(f'Total songs found: {files_scanned}')
logger.info(f'Total songs converted: {converted}')
