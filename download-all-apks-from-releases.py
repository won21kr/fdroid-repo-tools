#!/usr/bin/env python

import binascii
import os
import requests
import sys
import subprocess
import tempfile
import urllib2
from BeautifulSoup import BeautifulSoup


def download_all_apks_and_sigs(url, dldir):
    page = urllib2.urlopen(url)
    soup = BeautifulSoup(page)

    for link in soup.html.body.findAll('a'):
        apklink = link.get('href')
        if not apklink.endswith('.apk'):
            continue
        if apklink.endswith('-latest.apk'): # these are just symlinks
            continue
        if apklink[0] != '/' and not apklink.startswith('http'):
            apklink = url + '/' + apklink
        print(apklink)
        apkasc = None
        apksig = None
        try:
            apk = urllib2.urlopen(apklink).read()
            apkname = os.path.basename(apklink)
            with open(os.path.join(dldir, apkname), 'w') as f:
                f.writelines(apk)
            apkasc = urllib2.urlopen(apklink + '.asc').read()
            with open(os.path.join(dldir, apkname + '.asc'), 'w') as f:
                f.writelines(apkasc)
        except urllib2.HTTPError as e:
            try:
                apksig = urllib2.urlopen(apklink + '.sig').read()
                with open(os.path.join(dldir, apkname + '.sig'), 'w') as f:
                    f.writelines(apksig)
            except urllib2.HTTPError as e:
                print('FAILED: ' + os.path.basename(apklink) + ' has no signature file!')
                print(e)
                sys.exit(1)

if len(sys.argv) == 2:
    tmpdir = sys.argv[1]
else:
    tmpdir = tempfile.mkdtemp(prefix='.gp-releases-audit-')
    download_all_apks_and_sigs('https://guardianproject.info/releases', tmpdir)
    download_all_apks_and_sigs('https://guardianproject.info/releases/archive', tmpdir)
print('its all in ' + tmpdir)


# verify the GPG sigs on all of the APKs
for root, _, files in os.walk(tmpdir):
    for name in files:
        if name.endswith('.apk'):
            print(name + ':')
            apk = os.path.join(root, name)
            if os.path.exists(apk + '.sig'):
                sig = apk + '.sig'
            elif os.path.exists(apk + '.asc'):
                sig = apk + '.asc'
            else:
                print('FAILED: "' + name + '" has no GPG signature file!')
                sys.exit(1)
            if subprocess.call(['gpg2', '--verify', sig]) != 0:
                print('FAILED: ' + sig)
                sys.exit(1)
            print('Uploading to https://androidobservatory.org:')
            files = {'apk': (name, open(os.path.join(root, name), 'rb'))}
            r = requests.post('https://androidobservatory.org/upload',
                              files=files, verify=True)
            print('Uploading to https://www.virustotal.com:')
            files = {'file': (name, open(os.path.join(root, name), 'rb'))}
            r = requests.post('https://www.virustotal.com/en/file/upload/',
                              files=files, verify=True)
