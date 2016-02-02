#!/usr/local/bin python
# -*- coding: utf-8 -*-

import HTMLParser
import argparse
import codecs
import flickrapi
import json
import locale
import os
import re
import sys
import unicodedata
import urllib
import glob

reload(sys)
sys.setdefaultencoding("utf-8")

__author__ = 'kenijo'

import keys

EXT_IMAGE = ('jpg', 'png', 'jpeg', 'gif', 'bmp')
EXT_VIDEO = ('avi', 'wmv', 'mov', 'mp4', 'm4v', '3gp', 'ogg', 'ogv', 'mts')
MIME_TYPES = {
   'image/jpeg':        'jpg',
   'image/pjpeg':       'jpg',
   'image/gif':         'gif',
   'image/gif':         'gif',
   'image/png':         'png',
   'video/x-motion-jpeg': 'mjpg',
   'video/quicktime':    'mov',
   'video/mp4':         'mp4',
   'video/mpeg':        'mpg',
   'application/x-dvi':  'dvi',
   'video/x-msvideo':    'avi',
   'video/x-ms-wmv':     'wmv'
}

# get the file ext
def file_ext(file):
    ext = str(file).lower().split('.').pop()
    if len(ext)<=4 :
       return ext
    else:
       return ''

# get the file basename
def file_basename(file):
    parts = str(file).lower().split('.')
    if len(parts[-1])<=4:
        parts.pop()
        return '.'.join(parts)
    else:
        return str(file)

# Check the content-type of the file and change the extension if necessary
def fix_file_ext(file, headers):
    if file_ext(file):
        return

    if 'content-disposition' in headers:
        new_ext = file_ext(headers['content-disposition'])
    else:
        new_ext = ''
            
    if new_ext=='':
      content_type = headers['content-type'].lower()
      if content_type not in MIME_TYPES:
          warning('Unknown mime type for ct:{}'.format(content_type) )
          return;
      new_ext = MIME_TYPES[content_type]

    new_file = file + '.' + new_ext
    os.rename(file, new_file)

def start_sync(sync_path, cmd_args):
    is_windows = os.name == 'nt'
    is_download = cmd_args.download

    if not os.path.exists(sync_path):
        error( 'Sync path does not exist' )
        exit(0)

    # Common arguments
    args = {'format': 'json', 'nojsoncallback': 1}
    api = flickrapi.FlickrAPI(keys.KEY, keys.SECRET)
    # api.token.path = 'flickr.token.txt'

    # Ask for permission
    (token, frob) = api.get_token_part_one(perms='write')

    if not token:
        raw_input("Please authorized this app then hit enter:")

    try:
        token = api.get_token_part_two((token, frob))
    except:
        print 'Please authorized to use'
        exit(0)

    args.update({'auth_token': token})

    # Build your local photo sets
    photo_sets = {}
    skips_root = []
    exclude_files = ['.*']
    exclude_folders = ['.*', '@eaDir']
    for r, dirs, files in os.walk(sync_path):
        if os.path.isfile(os.path.join(r, 'ignore.flickr')):
            dirs[:] = []
            continue;
                                       
        files = [f for f in files if f not in exclude_files]
        dirs[:] = [d for d in dirs if d not in exclude_folders]

        for file in files:
            if not file.startswith('.'):
                ext = file_ext(file)
                if ext in EXT_IMAGE or \
                   ext in EXT_VIDEO:

                    if r == sync_path:
                        skips_root.append(file)
                    else:
                        photo_sets.setdefault(r, [])
                        photo_sets[r].append(file)

    if skips_root:
        error('To avoid disorganization on flickr sets root photos are not synced, skipped photos')
        print 'To avoid disorganization on flickr sets root photos are not synced, skipped these photos:', skips_root
        print 'Try to sync at top most level of your photos directory'

    # custom set builder
    def get_custom_set_title(path):
        title = '-'.join( path.split('/') )

        if cmd_args.custom_set:
            m = re.match(cmd_args.custom_set, path)
            if m:
                if not cmd_args.custom_set_builder:
                    title = '-'.join(m.groups())
                elif m.groupdict():
                    title = cmd_args.custom_set_builder.format(**m.groupdict())
                else:
                    title = cmd_args.custom_set_builder.format(*m.groups())
        return title

    # Get your photosets online and map it to your local
    html_parser = HTMLParser.HTMLParser()
    photosets_args = args.copy()
    page = 1
    photo_sets_map = {}

    # Show 3 possibilities
    if cmd_args.custom_set:
        for photo_set in photo_sets:
            folder = photo_set.replace(sync_path, '')
            print 'Set Title: [{}]  Folder: [{}]'.format( get_custom_set_title(folder, folder ) )

        if raw_input('Is this your expected custom set titles (y/n):') != 'y':
            exit(0)

    while True:
        print 'Getting photosets page {}'.format(page)
        photosets_args.update({'page': page, 'per_page': 500})
        sets = json.loads(api.photosets_getList(**photosets_args))
        page += 1
        if not sets['photosets']['photoset']:
            break

        for set in sets['photosets']['photoset']:
            # Make sure it's the one from backup format
            desc = html_parser.unescape(set['description']['_content'])

            if desc:
                photo_sets_map[desc] = set['id']
                title = get_custom_set_title(desc)
                if cmd_args.update_custom_set and desc in photo_set and title != set['title']['_content']:
                    update_args = args.copy()
                    update_args.update({
                        'photoset_id': set['id'],
                        'title': title,
                        'description': desc
                    })
                    print 'Updating custom title [{}]...'.format( title )
                    json.loads(api.photosets_editMeta(**update_args))
                    print 'done'

    print 'Found {} photo sets'.format( len(photo_sets_map) )

    # For adding photo to set
    def add_to_photo_set(photo_id, folder):
        # If photoset not found in online map create it else add photo to it
        # Always upload unix style
        if is_windows:
            folder = folder.replace(os.sep, '/')

        if folder not in photo_sets_map:
            photosets_args = args.copy()
            custom_title = get_custom_set_title(folder)
            photosets_args.update({'primary_photo_id': photo_id,
                                   'title': custom_title,
                                   'description': folder})
            set = json.loads(api.photosets_create(**photosets_args))
            photo_sets_map[folder] = set['photoset']['id']
            print 'Created set [{}] and added photo'.format( custom_title )
        else:
            photosets_args = args.copy()
            photosets_args.update({'photoset_id': photo_sets_map.get(folder), 'photo_id': photo_id})
            result = json.loads(api.photosets_addPhoto(**photosets_args))
            if result.get('stat') == 'ok':
                print 'Success'
            else:
                error( result )

    # Get photos in a set
    def get_photos_in_set(folder):
        # bug on non utf8 machines dups
        folder = folder.decode('utf-8')

        photos = {}
        # Always upload unix style
        if is_windows:
            folder = folder.replace(os.sep, '/')

        if folder in photo_sets_map:
            photoset_args = args.copy()
            page = 1
            while True:
                photoset_args.update({'photoset_id': photo_sets_map[folder], 'page': page})
                photoset_args['extras'] = 'url_o,media,original_format'
                page += 1
                photos_in_set = json.loads(api.photosets_getPhotos(**photoset_args))
                if photos_in_set['stat'] != 'ok':
                    break

                for photo in photos_in_set['photoset']['photo']:
                    # print photo;

                    if is_download and photo.get('media') == 'video':
                        photo_args = args.copy()
                        photo_args['photo_id'] = photo['id']
                        photo_args['extras'] = 'url_o,media,original_format'
                        sizes = json.loads(api.photos_getSizes(**photo_args))
                        # print "sizes", sizes
                        if sizes['stat'] != 'ok':
                            continue

                        # original = filter(lambda s: s['label'].startswith('Site') and s['media'] == 'video', sizes['sizes']['size'])
                        original = filter(lambda s: s['source'].find('/orig') > 0 and s['media'] == 'video', sizes['sizes']['size'])
                        # print "original", original
                        if original:
                            source = original[-1]['source'].replace('/site/', '/orig/')
                            title = photo['title']
                            photos[title] = source
                
                        #     print photos
                        # Skipts download video for now since it doesn't work
                        #continue
                        #photos[photo['title']] = 'http://www.flickr.com/video_download.gne?id={}'.format( photo['id'] )
                        #print     photos[photo['title']]
                    else:
                        title = photo['title']
                        if not title:
                            title = photo['id']
                        if not title:
                            if photo['url_o']:
                                title, ext = os.path.splitext(os.path.basename(photo['url_o']))
                        if title:
                            photos[title] = photo['url_o'] if is_download else photo['id']

        return photos

    # If download mode lets skip upload but you can also modify this to your needs
    if is_download:
        # Download to corresponding paths
        os.chdir(sync_path)

        for photo_set in photo_sets_map:
            if photo_set and is_download == '.' or is_download != '.' and photo_set.startswith(is_download):
                folder = photo_set.replace(sync_path, '')
                print 'Getting photos in set [{}]'.format( folder )
                photos = get_photos_in_set(folder)
                # If Uploaded on unix and downloading on windows & vice versa
                if is_windows:
                    folder = folder.replace('/', os.sep)

                if not os.path.isdir(folder):
                    os.makedirs(folder)

                for photo in photos:
                    # Adds skips
                    if cmd_args.ignore_images and file_ext(photo) in EXT_IMAGE:
                        continue
                    elif cmd_args.ignore_videos and file_ext(photo) in EXT_VIDEO:
                        continue

                    path = os.path.join(folder, photo)
                    if os.path.exists(path):
                        # print 'Skipped [{}] already downloaded'.format( path )
                        pass
                    elif glob.glob(path + '.*'):
                        # print 'Skipped [{}] already matched'.format( path )
                        pass
                    else:
                        print 'Downloading photo [{}]'.format( path )
                        [filename, headers] = urllib.urlretrieve(photos[photo], os.path.join(sync_path, path) )
                        fix_file_ext(filename, headers)

    else:
        # Loop through all local photo set map and
        # upload photos that does not exists in online map
        for photo_set in sorted(photo_sets):
            folder = photo_set.replace(sync_path, '')
            display_title = get_custom_set_title(folder)
            
            # Create tags from folder names
            # Remove duplicate words from tags
            tags = ''
            if cmd_args.generate_tags:
                def unique_list(l):
                    ulist = []
                    [ulist.append(x) for x in l if x not in ulist]
                    return ulist
                tags = photo_set
                tags = tags.replace(sync_path, '')
                tags = re.sub(r'^\[([\d -]*?)\]', ' ', tags)
                tags = re.sub(r'\W*\b\w{1,3}\b', ' ', tags)
                tags=' '.join(unique_list(tags.split()))

            print 'Getting photos in set [{}]'.format( display_title )
            photos = get_photos_in_set(folder)
            print 'Found {} photos'.format( len(photos) )

            for photo in sorted(photo_sets[photo_set]):

                # Adds skips
                if cmd_args.ignore_images and file_ext(photo) in EXT_IMAGE:
                    continue
                elif cmd_args.ignore_videos and file_ext(photo) in EXT_VIDEO:
                    continue

                photo_exist = False
                photo_l = photo.lower()
                p_no_ext = file_basename(photo_l)
                for k, v in photos.iteritems():
                    k = k.lower()
                    k_no_ext = file_basename(k)
                    if (photo_l == str(k) or is_windows and photo.replace(os.sep, '/') == str(k) or
                        photo_l == str(k_no_ext) or is_windows and photo.replace(os.sep, '/') == str(k_no_ext) or
                        p_no_ext == str(k) or is_windows and p_no_ext.replace(os.sep, '/') == str(k)           or
                        p_no_ext == str(k_no_ext) or is_windows and p_no_ext.replace(os.sep, '/') == str(k_no_ext)            ):
                            photo_exist = True

                if photo_exist:
                    # print 'Skipped [{}] already exists in set [{}]'.format( photo, display_title )
                    pass
                else:
                    upload_args = {
                        'auth_token': token,
                        # (Optional) The title of the photo.
                        'title': file_basename(photo),
                        # (Optional) A description of the photo. May contain some limited HTML.
                        'description': folder,
                        # (Optional) A space-seperated list of tags to apply to the photo.
                        'tags': tags,
                        # (Optional) Set to 0 for no, 1 for yes. Specifies who can view the photo.
                        'is_public': 0,
                        'is_friend': 1,
                        'is_family': 1,
                        # (Optional) Set to 1 for Safe, 2 for Moderate, or 3 for Restricted.
                        'safety_level': 1,
                        # (Optional) Set to 1 for Photo, 2 for Screenshot, or 3 for Other.
                        'content_type': 1,
                        # (Optional) Set to 1 to keep the photo in global search results, 2 to hide from public searches.
                        'hidden': 2
                    }

                    file_path = os.path.join(photo_set, photo)
                    file_stat = os.stat(file_path)

                    if file_stat.st_size >= 1073741824:
                        error( 'Skipped [{}] over size limit'.format(photo) )
                        continue

                    try:
                        print 'Uploading {} [{}]'.format( photo, display_title )
                        upload = api.upload(file_path, None, **upload_args)
                        photo_id = upload.find('photoid').text
                        add_to_photo_set(photo_id, folder)
                        photos[photo] = photo_id
                    except flickrapi.FlickrError as e:
                        error( '{} on {} in {}'.format(e.message, photo, display_title) )
                    except BaseException as e:
                        error( '{} on {} in {}'.format(e.message, photo, display_title) )


    print 'All Synced'

def warning(*objs):
    sys.stderr.write("WARNING: {}\n".format(*objs) )
    sys.stderr.flush()

def error(*objs):
    sys.stderr.write("ERROR: {}\n".format(*objs) )
    sys.stderr.flush()

def main():
    parser = argparse.ArgumentParser(description='Sync current folder to your flickr account.')
    parser.add_argument('--download', type=str, help='download the photos from flickr specify a path or . for all')
    parser.add_argument('--ignore-videos', action='store_true', help='ignore video files')
    parser.add_argument('--ignore-images', action='store_true', help='ignore image files')
    parser.add_argument('--sync-path', type=str, default=os.getcwd(), help='specify the sync folder (default is current dir)')
    parser.add_argument('--generate-tags', action='store_true', help='generate tags based on the name of the photo set')
    parser.add_argument('--custom-set', type=str, help='customize your set name from path with regex')
    parser.add_argument('--custom-set-builder', type=str, help='build your custom set title (default just merge groups)')
    parser.add_argument('--update-custom-set', action='store_true', help='updates your set title from custom set')

    args = parser.parse_args()
    start_sync(args.sync_path.rstrip(os.sep) + os.sep, args)
