# zinnia-blog-util

Various utilities for working with django-blog-zinnia

https://github.com/Fantomas42/django-blog-zinnia/issues

These utilities are for my specific needs, but provide useful examples of
working with Django and Zinnia objects.


byteflow2zinnia
---------------
Created: 2012-10-16

Migrate from Django Byteflow Blog to Django Zinnia Blog

Moves users, tags, comments, and posts

Assuptions to make it easier:

* The site is small enough that performance doesn't matter
* both sites use postgres
* there is only one blog to migrate
* there is only one author for both sites
* just migrate the HTML
* new_blog is empty
* subscriptions are ignored
* all commenting in new site will be disabled
* all pingbacks in new site are disabled
* all tags should be moved
* no images are moved
* no end-publication dates
* created date is publication date

Items that need to be migrated:

* Entries
* Authors (nope: assumption)
* Tags
* Comments (with authors)
* Pingbacks (become comments)

Database documention

There is a lot of documentation on the database tables for both blogs at the
bottom of the script. Even if you don't need to migrate your data, you might
find the documentation to be helpful.


migrate_0-18-1
--------------
Created: 2017-01-21

Migrate from a very old version of Django Zinnia Blog to 0.18.1
Django migrate should work for future updates

This script must be run with an active venv context that has the
Django environment configured.
You should also disable pingbacks during the migration:
    ZINNIA_PING_EXTERNAL_URLS = False
    ZINNIA_SAVE_PING_DIRECTORIES = False
After migration, admin needs to set users passwords

Assuptions to make it easier:

* The site is small enough that performance doesn't matter
* Both sites use postgres for the DB
* New site is empty
* All data should be moved
* The media directory is already moved
* Category hierarchy doesn't matter
* No special templates are used

Migrates:

* Entries
* Authors
* Tags (imported as part of Entry)
* Categories
* Comments (with authors)
* Pingbacks
* Links to images in the media directory

Method:

* Extract directly from the old database
* Build a Django object
* Commit the Django object into the new DB
