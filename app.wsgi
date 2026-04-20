import sys
import site
import os

site.addsitedir('/var/www/clean/env/lib/python3.13/site-packages')

sys.path.insert(0, '/var/www/clean')

os.chdir('/var/www/clean')

os.environ['VIRTUAL_ENV'] = '/var/www/clean/env'
os.environ['PATH'] = '/var/www/clean/env/bin:' + os.environ['PATH']

from app import app as application
