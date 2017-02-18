#! /usr/bin/env python
# -*- coding: utf-8 -*-
''' migrate_0-18-1.py
Migrate from a very old version of Django Zinnia Blog to 0.18.1
Going forward, Django migrate should work

This script must be run with an active venv context that has the
Django environment configured.
You should also disable pingbacks during the migration:
    ZINNIA_PING_EXTERNAL_URLS = False
    ZINNIA_SAVE_PING_DIRECTORIES = False
After migration, admin needs to set users passwords

Copyright 2012 Richard Esplin <richard-oss@esplins.org>
This script is licensed under 3-clause BSD license
'''
# Assuptions to make it easier:
## The site is small enough that performance doesn't matter
## Both sites use postgres for the DB
## New site is empty
## All data should be moved
## The media directory is already moved
## Category hierarchy doesn't matter
## No special templates are used

# Migrate
## Entries
## Authors
## Tags (imported as part of Entry)
## Categories
## Comments (with authors)
## Pingbacks
## Links to images in the media directory

# Method
# Extract directly from the old database
# Build a Django object
# Commit the Django object into the new DB

# TODO
# The comment count is off by one (it's one too many)
# Instead of manually mapping the old_db fields to fields in the model of the
# new site, you could extract the keys and send them as kwargs to the new
# model.


import sys, os
import psycopg2
import django
from django.db.models import Max
from django.db import connection as django_db

oldDB_host = "localhost"
oldDB_name = "richard_site_old"
oldDB_user = "richard_site_old"
oldDB_pass = "test"
django_settings = "richard_site.settings"

# pg_hba.conf must be enabled for host authentication:
# host    richard_site_old  richard_site_old  127.0.0.1/32   md5


def import_authors(conn_oldDB):
    from django.contrib.auth.models import User

    with conn_oldDB:
        with conn_oldDB.cursor() as cursor_oldDB:
            cursor_oldDB.execute("SELECT * FROM auth_user")
            old_authors = cursor_oldDB.fetchall() # Not good on large sites
    for a in old_authors:
        print("Author: %s, %s, %s" %(a['id'], a['username'], a['email']))
        a_model = User(id=a['id'], username=a['username'], first_name=a['first_name'],
                       last_name=a['last_name'], email=a['email'],
                       is_staff=a['is_staff'], is_active=a['is_active'],
                       is_superuser=a['is_superuser'],
                       last_login=a['last_login'], date_joined=a['date_joined'])
        a_model.save()
    # Fix postgresql sequence id's
    max_id = User.objects.all().aggregate(max=Max('id'))['max']
    print("Setting max User id to: %s" %(max_id+1))
    django_cursor = django_db.cursor()
    result = django_cursor.execute('ALTER SEQUENCE auth_user_id_seq '
                                   'RESTART %s', [max_id+1])


def import_sites(conn_oldDB):
    from django.contrib.sites.models import Site

    with conn_oldDB:
        with conn_oldDB.cursor() as cursor_oldDB:
            cursor_oldDB.execute("SELECT * FROM django_site")
            old_sites = cursor_oldDB.fetchall() # Not good on large sites
    for s in old_sites:
        print("Site: %s, %s, %s" %(s['id'], s['domain'], s['name']))
        s_model = Site(id=s['id'], domain=s['domain'], name=s['name'])
        s_model.save()
    # Fix postgresql sequence id's
    max_id = Site.objects.all().aggregate(max=Max('id'))['max']
    print("Setting max Site id to: %s" %(max_id+1))
    django_cursor = django_db.cursor()
    result = django_cursor.execute('ALTER SEQUENCE django_site_id_seq '
                                   'RESTART %s', [max_id+1])


def import_categories(conn_oldDB):
    from zinnia.models import Category

    with conn_oldDB:
        with conn_oldDB.cursor() as cursor_oldDB:
            cursor_oldDB.execute("SELECT * FROM zinnia_category")
            categories = cursor_oldDB.fetchall() # Not good on large sites
    for c in categories:
        print("Category: %s, %s, %s, %s, %s, %s"
              %(c['slug'], c['description'], c['id'], c['title'], c['parent_id'],
                c['level']))
        c_model = Category(slug=c['slug'], description=c['description'], id=c['id'],
                           title=c['title'], parent_id=c['parent_id'],
                           level=c['level'])
        c_model.save()
    # Fix postgresql sequence id's
    max_id = Category.objects.all().aggregate(max=Max('id'))['max']
    print("Setting max Category id to: %s" %(max_id+1))
    django_cursor = django_db.cursor()
    result = django_cursor.execute('ALTER SEQUENCE zinnia_category_id_seq '
                                   'RESTART %s', [max_id+1])


def import_entries(conn_oldDB):
    from zinnia.models import Entry
    from django.contrib.sites.models import Site
    from django.contrib.auth.models import User
    from zinnia.models import Category

    # Get a list of entries from old_site
    with conn_oldDB:
        with conn_oldDB.cursor() as cursor_oldDB:
            cursor_oldDB.execute("SELECT * FROM zinnia_entry")
            old_posts = cursor_oldDB.fetchall() # Not good on large sites
    for p in old_posts:
        #print("Entry: %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
        #      "%s, %s, %s, %s"
        #      %(p['status'], p['last_update'], p['comment_enabled'],
        #        p['tags'], p['image'], p['title'], p['excerpt'], p['slug'],
        #        p['content'], p['end_publication'], p['start_publication'],
        #        p['creation_date'], p['id'], p['pingback_enabled'],
        #        p['login_required'], p['password'], p['template'],
        #        p['featured']))
        print("Entry: %s" %(p['title']))
        if p['start_publication'] is None:
            print("No start_publication, using creation_date")
            publication_date = p['creation_date']
        else: publication_date = p['start_publication']
        e_model = Entry(status=p['status'], last_update=p['last_update'],
                        comment_enabled=p['comment_enabled'], tags=p['tags'],
                        image=p['image'], title=p['title'], excerpt=p['excerpt'],
                        slug=p['slug'], content=p['content'],
                        end_publication=p['end_publication'],
                        start_publication=p['start_publication'],
                        publication_date = publication_date,
                        creation_date=p['creation_date'], id=p['id'],
                        pingback_enabled=p['pingback_enabled'], 
                        login_required=p['login_required'], password=p['password'], 
                        featured=p['featured'], trackback_enabled=False)
        e_model.save()
        # Update Sites
        with conn_oldDB:
            with conn_oldDB.cursor() as cursor_oldDB:
                cursor_oldDB.execute("SELECT site_id FROM zinnia_entry_sites "
                                     "WHERE entry_id = %s", (e_model.id,))
                published_sites = cursor_oldDB.fetchall() # Not good on large sites
        for ps in published_sites:
            site_object = Site.objects.filter(id=ps['site_id'])[0]
            print("Adding to: %s" %site_object)
            e_model.sites.add(site_object.id)
        # Update Authors
        with conn_oldDB:
            with conn_oldDB.cursor() as cursor_oldDB:
                cursor_oldDB.execute("SELECT user_id FROM zinnia_entry_authors "
                                     "WHERE entry_id = %s", (e_model.id,))
                authors = cursor_oldDB.fetchall() # Not good on large sites
        for a in authors:
            user_object = User.objects.filter(id=a['user_id'])[0]
            print("Adding author: %s" %user_object)
            e_model.authors.add(user_object.id)
       # Update Categories
        with conn_oldDB:
            with conn_oldDB.cursor() as cursor_oldDB:
                cursor_oldDB.execute("SELECT category_id FROM zinnia_entry_categories "
                                     "WHERE entry_id = %s", (e_model.id,))
                categories = cursor_oldDB.fetchall() # Not good on large sites
        for c in categories:
            category_object = Category.objects.filter(id=c['category_id'])[0]
            print("Adding category: %s" %category_object)
            e_model.categories.add(category_object.id)
        e_model.save()

    # Fix postgresql sequence id's
    max_id = Entry.objects.all().aggregate(max=Max('id'))['max']
    print("Setting max Entry id to: %s" %(max_id+1))
    django_cursor = django_db.cursor()
    result = django_cursor.execute('ALTER SEQUENCE zinnia_entry_id_seq '
                                   'RESTART %s', [max_id+1])

    # Now that all entries exist, update related entries
    for e_model in Entry.objects.all():
        with conn_oldDB:
            with conn_oldDB.cursor() as cursor_oldDB:
                cursor_oldDB.execute("SELECT to_entry_id FROM zinnia_entry_related "
                                     "WHERE from_entry_id = %s", (e_model.id,))
                related_entries = cursor_oldDB.fetchall() # Not good on large sites
        for re in related_entries:
            related_entry_object = Entry.objects.filter(id=re['to_entry_id'])[0]
            print("Adding related entry: %s" %related_entry_object)
            e_model.related.add(related_entry_object.id)


def import_comments(conn_oldDB):
    from django_comments.models import Comment
    from zinnia.models import Entry
    from django_comments.models import CommentFlag

    with conn_oldDB:
        with conn_oldDB.cursor() as cursor_oldDB:
            cursor_oldDB.execute("SELECT * FROM django_comments")
            comments = cursor_oldDB.fetchall() # Not good on large sites
    for c in comments:
        #print("Comment: %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s"
        #      %(c['id'], c['content_type_id'], c['object_pk'], c['site_id'],
        #        c['user_id'], c['user_name'], c['user_email'], c['user_url'],
        #        c['comment'], c['submit_date'], c['ip_address'], c['is_public'],
        #        c['is_removed']))
        print("Comment by %s on %s" %(c['user_name'], c['object_pk']))
        c_model = Comment(id=c['id'], content_type_id=c['content_type_id'],
                          object_pk=c['object_pk'], site_id=c['site_id'],
                          user_id=c['user_id'], user_name=c['user_name'],
                          user_email=c['user_email'], user_url=c['user_url'],
                          comment=c['comment'], submit_date=c['submit_date'],
                          ip_address=c['ip_address'], is_public=c['is_public'],
                          is_removed=c['is_removed'])

        c_model.save()
        # Comment Flags
        isPingback = False
        with conn_oldDB.cursor() as cursor_oldDB:
            cursor_oldDB.execute("SELECT * FROM django_comment_flags "
                                 "WHERE comment_id = %s", (c_model.id,))
            c_flags = cursor_oldDB.fetchall() # Not good on large sites
            for f in c_flags:
                print("Creating comment flag: %s, %s, %s, %s" 
                      %(f['user_id'], f['comment_id'], f['flag'], f['flag_date']))
                # ID doesn't matter, so leave it off so sequence gets updated
                f_model = CommentFlag(user_id=f['user_id'],
                                      comment_id=f['comment_id'], flag=f['flag'],
                                      flag_date=f['flag_date'])
                f_model.save()
                c_model.flags.add(f_model)
                if f_model.flag == "pingback":
                    isPingback = True
        c_model.save()

        # Update entry's comment count
        entry_model = Entry.objects.filter(id=c_model.object_pk)[0]
        if not isPingback: entry_model.comment_count+=1
        entry_model.save()

    # Fix postgresql sequence id's
    max_id = Comment.objects.all().aggregate(max=Max('id'))['max']
    print("Setting max Comment id to: %s" %(max_id+1))
    django_cursor = django_db.cursor()
    result = django_cursor.execute('ALTER SEQUENCE django_comments_id_seq '
                                   'RESTART %s', [max_id+1])


def main():
    # Setup Django environment
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", django_settings)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(BASE_DIR)
    django.setup()

    # Create a reusable DB connection
    conn_oldDB = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'"
                                  %(oldDB_name, oldDB_user,
                                    oldDB_host, oldDB_pass),
                                  cursor_factory=psycopg2.extras.DictCursor)

    import_authors(conn_oldDB)
    import_sites(conn_oldDB)
    import_categories(conn_oldDB)
    import_entries(conn_oldDB)
    import_comments(conn_oldDB)

    # Cleanup
    conn_oldDB.close()


if __name__ == '__main__':
    sys.exit(main())


## DB Structure of Zinnia old_db ##
# auth_user                 
# ---------
#  id           | integer                  |
#  username     | character varying(30)    |
#  first_name   | character varying(30)    |
#  last_name    | character varying(30)    |
#  email        | character varying(75)    |
#  password     | character varying(128)   |
#  is_staff     | boolean                  |
#  is_active    | boolean                  |
#  is_superuser | boolean                  |
#  last_login   | timestamp with time zone |
#  date_joined  | timestamp with time zone |
# 
# django_comment_flags      
# --------------------
#  id         | integer                  |
#  user_id    | integer                  |
#  comment_id | integer                  |
#  flag       | character varying(30)    |
#  flag_date  | timestamp with time zone |
# 
# django_comments           
# -----------------
#  id              | integer                  | 
#  content_type_id | integer                  | 
#  object_pk       | text                     | 
#  site_id         | integer                  | 
#  user_id         | integer                  | 
#  user_name       | character varying(50)    | 
#  user_email      | character varying(75)    | 
#  user_url        | character varying(200)   | 
#  comment         | text                     | 
#  submit_date     | timestamp with time zone | 
#  ip_address      | inet                     | 
#  is_public       | boolean                  | 
#  is_removed      | boolean                  | 
# 
# django_site               
# --------------
#  id     | integer                |
#  domain | character varying(100) |
#  name   | character varying(50)  |
# 
# tagging_tag               
# --------------
#  id     | integer               |
#  name   | character varying(50) | 
# 
# tagging_taggeditem        
# ------------------
#  id              | integer | 
#  tag_id          | integer |
#  content_type_id | integer |
#  object_id       | integer |
# 
# zinnia_category           
# ---------------
#  slug        | character varying(255) |
#  description | text                   |
#  id          | integer                |
#  title       | character varying(255) |
#  parent_id   | integer                |
#  lft         | integer                |
#  rght        | integer                |
#  tree_id     | integer                |
#  level       | integer                |
# 
# zinnia_entry              
# --------------
#  status            | integer                  |
#  last_update       | timestamp with time zone |
#  comment_enabled   | boolean                  |
#  tags              | character varying(255)   |
#  image             | character varying(100)   |
#  title             | character varying(255)   |
#  excerpt           | text                     |
#  slug              | character varying(255)   |
#  content           | text                     |
#  end_publication   | timestamp with time zone |
#  start_publication | timestamp with time zone |
#  creation_date     | timestamp with time zone |
#  id                | integer                  |
#  pingback_enabled  | boolean                  |
#  login_required    | boolean                  |
#  password          | character varying(50)    |
#  template          | character varying(250)   |
#  featured          | boolean                  |
# 
# zinnia_entry_authors      
# ---------------------
#  id       | integer |
#  entry_id | integer |
#  user_id  | integer |
# 
# zinnia_entry_categories   
# -----------------------
#  id          | integer |
#  entry_id    | integer |
#  category_id | integer |
# 
# zinnia_entry_related      
# --------------------
#  id            | integer |
#  from_entry_id | integer |
#  to_entry_id    | integer |
# 
# zinnia_entry_sites
# -------------------
#  id       | integer |
#  entry_id | integer |
#  site_id  | integer |

# vim: expandtab ts=4 sw=4 softtabstop=4 filetype=python
