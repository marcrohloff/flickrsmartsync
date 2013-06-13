.. -*- mode: rst; coding: utf-8 -*-

======================================================================
flickrsmartsync - Sync/backup your photos to flickr easily
======================================================================

:Authors: Faisal Raja <support@altlimit.com>
:Version: 0.1.2
:Date:    2013-06-13
:Blog Post: http://blog.altlimit.com/2013/05/backupsync-your-photos-to-flickr-script.html
:PyPI: https://pypi.python.org/pypi/flickrsmartsync


Overview
======================================================================
flickrsmartsync is a tool you can use to easily sync up or down your
photos in a drive/folder to flickr since now it has a free 1TB storage
you can probably sync all your photo collection.

It has the following features:

upload
  by default without any command it will upload all photos wherever
  you run it from. It will be grouped into sets.

download
  when you specify a download . means it will download all and recreate
  the same folder structure you uploaded it from, specifying a path
  will download only the folder/path.


Installation
---------------
You need to have setuptools/easy_install installed. Installation
should be as easy as typing::
  
  easy_install flickrsmartsync
  or
  pip install flickrsmartsync

This should download flickrsmartsync and it's dependencies flickrapi
and install them.

Limitations
---------------
- it only supports upload and download at a time and not both


flickrsmartsync - command line tool
======================================================================
flickrsmartsync provides a command line utility called flickrsmartsync, which
by default uploads anything under the path its ran from and passing
--download [remote_path] will download the remote path.

Example Usage::

  User: MyPhotosDrive faisal$ flickrsmartsync
  ...Will start uploading all photos under that drive

  User: MyPhotosDrive faisal$ flickrsmartsync --download .
  ...Will start downloading all photos on flickr to that drive

  User: MyPhotosDrive faisal$ flickrsmartsync --download 2008/2008-01-01
  ...Will start downloading all paths starting with that path


Change-Log
======================================================================
2013-06-13	Initial release 0.1
-----------------------------------------------

LICENSE
======================================================================
MIT