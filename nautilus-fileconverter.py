converterVersion = "001000008" # Change the number if you want to trigger an update.
automaticUpdates = True # Replace the "True" with "False" if you don't want automatic updates.

from gi.repository import Nautilus, GObject
from typing import List
from PIL import Image, UnidentifiedImageError
from urllib.parse import urlparse, unquote
from pathlib import Path
import pathlib
import os, shlex
import urllib.request

pyheifImported = True

try:
    import pyheif
except ImportError:
    print(f"WARNING(Nautilus-file-converter): \"pyheif\" not found, if you want to convert from heif format, install the package using \"pip install pyheif\"." )
    pyheifImported = False

if automaticUpdates:
    with urllib.request.urlopen(
            "https://raw.githubusercontent.com/aloise/Nautilus-fileconverter/main/nautilus-fileconverter.py") as f:
        onlineFile = f.read().decode().strip()
    if converterVersion not in onlineFile:
        print("Updating...")
        currentPath = str(pathlib.Path(__file__).parent.resolve())
        if "/home/" in currentPath:
            fileUpdatePath = f"{currentPath}/{os.path.basename(__file__)}"
            with open(fileUpdatePath, 'w') as file:
                file.write(onlineFile)
        else:
            print("updating only supported in home!")

print = lambda *wish, **verbosity: None    # comment it out, if you wish debug printing

class FileConverterMenuProvider(GObject.GObject, Nautilus.MenuProvider):
    READ_FORMATS_IMAGE = ('image/jpeg',
                          'image/png',
                          'image/bmp',
                          'application/postscript',
                          'image/gif',
                          'image/x-icon',
                          'image/x-pcx',
                          'image/x-portable-pixmap',
                          'image/tiff',
                          'image/x-xbm',
                          'image/x-xbitmap',
                          'video/fli',
                          'image/vnd.fpx',
                          'image/vnd.net-fpx',
                          'application/octet-stream',
                          'windows/metafile',
                          'image/x-xpixmap',
                          'image/webp',
                          'image/avif',
                          'image/heif')

    READ_FORMATS_AUDIO = ('audio/mpeg',
                          'audio/mpeg3',
                          'video/x-mpeg',
                          'audio/x-mpeg-3',
                          'audio/x-wav',
                          'audio/wav',
                          'audio/wave',
                          'audio/x-pn-wave',
                          'audio/vnd.wave',
                          'audio/x-mpegurl',
                          'audio/mp4',
                          'audio/mp4a-latm',
                          'audio/mpeg4-generic',
                          'audio/x-matroska',
                          'audio/aac',
                          'audio/aacp',
                          'audio/3gpp',
                          'audio/3gpp2',
                          'audio/ogg',
                          'audio/opus',
                          'audio/flac',
                          'audio/x-vorbis+ogg')

    READ_FORMATS_VIDEO = ('video/mp4',
                          'video/webm',
                          'video/x-matroska',
                          'video/avi',
                          'video/msvideo',
                          'video/x-msvideo',
                          'video/quicktime')

    WRITE_FORMATS_IMAGE = [{'name': 'JPEG', 'extension': 'jpg', 'id': 'img_to_jpg'},
                           {'name': 'PNG', 'extension': 'png', 'id': 'img_to_png'}]

    WRITE_FORMATS_AUDIO = [{'name': 'MP3', 'extension': 'mp3', 'id': 'mp3'},
                           {'name': 'AAC', 'extension': 'aac', 'id': 'aac'},
                           {'name': 'FLAC', 'extension': 'flac', 'id': 'flac'},
                        #    {'name': 'M4A'},
                        #    {'name': 'OGG'}
                           ]

    WRITE_FORMATS_VIDEO = [{'name': 'MP4 - H.265 FullHD', 'id': 'mp4_h265_1080p', 'extension': 'mp4'},
                           {'name': 'MP4 - H.265 - Source Resolution', 'id': 'mp4_h265', 'extension': 'mp4'},
                        #    {'name': 'WebM'},
                        #   {'name': 'MKV'},
                        #    {'name': 'AVI'},
                           {'name': 'MP3', 'extension': 'mp3', 'id': 'mp3'},
                           {'name': 'AAC', 'extension': 'aac', 'id': 'aac'},
                        #    {'name': 'WAV'}
                           ]

    def get_file_items(self, *args) -> List[Nautilus.MenuItem]:
        files = args[-1]
        for file in files:
            print(file.get_mime_type())
            file_mime = file.get_mime_type()
            if file_mime in self.READ_FORMATS_IMAGE:
                return self.__submenu_builder(self.WRITE_FORMATS_IMAGE,
                                              callback=self.convert_video_audio,
                                              files=files)
            if file_mime in self.READ_FORMATS_AUDIO:
                return self.__submenu_builder(self.WRITE_FORMATS_AUDIO,
                                              callback=self.convert_video_audio,
                                              files=files)
            if file_mime in self.READ_FORMATS_VIDEO:
                return self.__submenu_builder(self.WRITE_FORMATS_VIDEO,
                                              callback=self.convert_video_audio,
                                              files=files)

    def __submenu_builder(self, formats, callback, files):
        top_menuitem = Nautilus.MenuItem(
            name="FileConverterMenuProvider::convert_to",
            label="Convert to...",
        )
        submenu = Nautilus.Menu()
        top_menuitem.set_submenu(submenu)
        for format in formats:
            sub_menuitem = Nautilus.MenuItem(
                name='ConvertToSubmenu_' + format['name'],
                label=(format['name']),
            )
            sub_menuitem.connect('activate', callback, format, files)
            submenu.append_item(sub_menuitem)
        return [top_menuitem]


    def __get_extension(self, format):
        if format['extension'] is not None:
            return f".{format['extension']}".lower()
        else:
            return f".{format.get('extension', format['name'])}".lower()

    def convert_video_audio(self, menu, format, files):
        # use same ffmpeg backend
        for file in files:
            file_mime = file.get_mime_type()
            from_file_path = Path(unquote(urlparse(file.get_uri()).path))
            to_file_path = from_file_path.with_suffix(self.__get_extension(format).lower())
            count = 0
            to_file_path_mod = from_file_path.with_name(f"{from_file_path.stem}")
            while to_file_path_mod.exists() or to_file_path.exists():
                count = count + 1
                to_file_path_mod = from_file_path.with_name(f"{from_file_path.stem}({count}){self.__get_extension(format).lower()}")
                to_file_path = to_file_path_mod
                
            convert_command = f"echo {file_mime}"
            
            if format['id'] == 'mp4_h265_1080p':
                convert_command = f"ffmpeg -vaapi_device /dev/dri/renderD128 -hwaccel vaapi -i {shlex.quote(str(from_file_path))} -map_metadata 0 -vf 'scale=1920:-2,format=nv12,hwupload' -c:v hevc_vaapi -b:v 10000k -maxrate 10000k -c:a aac -b:a 320k {shlex.quote(str(to_file_path))}"
            elif format['id'] == 'mp4_h265':
                convert_command = f"ffmpeg -vaapi_device /dev/dri/renderD128 -hwaccel vaapi -i {shlex.quote(str(from_file_path))} -map_metadata 0 -vf 'format=nv12,hwupload' -c:v hevc_vaapi -c:a aac -b:a 320k {shlex.quote(str(to_file_path))}"
            elif format['id'] == 'mp3':
                convert_command = f"ffmpeg -i {shlex.quote(str(from_file_path))} -vn -c:a libmp3lame -b:a 320k {shlex.quote(str(to_file_path))}"
            elif format['id'] == 'aac':
                convert_command = f"ffmpeg -i {shlex.quote(str(from_file_path))} -vn -c:a aac -b:a 320k {shlex.quote(str(to_file_path))}"
            elif format['id'] == 'flac':
                convert_command = f"ffmpeg -i {shlex.quote(str(from_file_path))} -vn -c:a flac -b:a 320k {shlex.quote(str(to_file_path))}"
            elif (format['id'] == 'img_to_jpg' or format['id'] == 'img_to_png') and file_mime == 'image/heif':
                convert_command = f"heif-convert {shlex.quote(str(from_file_path))} {shlex.quote(str(to_file_path))}"
            elif format['id'] == 'img_to_jpg' or format['id'] == 'img_to_png':
                convert_command = f"ffmpeg -i {shlex.quote(str(from_file_path))} {shlex.quote(str(to_file_path))}"    

            #os.system(f"gnome-terminal -- zsh -c \"{convert_command}; exec zsh\"")    
            os.system(f"nohup {convert_command}  | tee &")
