#!/usr/bin/python
#
# Migrate from Django Byteflow Blog to Django Zinnia Blog
# Moves users, tags, comments, and posts 
#
# Copyright 2012 Richard Esplin <richard-oss@esplins.org>
# This script is licensed under the same terms as Zinnia

# Assuptions to make it easier:
## The site is small enough that performance doesn't matter
## both sites use postgres
## there is only one blog to migrate
## there is only one author for both sites
## just migrate the HTML
## new_blog is empty
## subscriptions are ignored
## all commenting in new site will be disabled
## all pingbacks in new site are disabled
## all tags should be moved
## no images are moved
## no end-publication dates
## created date is publication date

# Migrate
## Entries
## Authors (nope: assumption)
## Tags
## Comments (with authors)
## Pingbacks

import psycopg2

olddb_host = "localhost"
olddb_name = "richard_site_old"
olddb_user = "richard_site"
olddb_pass = "Waa5uban"

newdb_host = "localhost"
newdb_name = "richard_site"
newdb_user = "richard_site"
newdb_pass = "Waa5uban"

newdb_auth_id = 1
newdb_site_id = 1

#TODO
category_list = {"":"",} #tags in Byteflow that should be categories in Zinnia

def convert_tags(tag_string):
  '''Byteflow tags have spaces and are comma separated.
     Zinnia tags are space separated.
     So convert spaces to underscores.
  '''
  tag_string = tag_string.replace(", ","@@") #deal with space after comma
  tag_string = tag_string.replace(" ","_")
  tag_string = tag_string.replace("@@"," ")
  return tag_string

if __name__ == "__main__":
  conn_old = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'"
                              %(olddb_name, olddb_user,
                                olddb_host, olddb_pass))
  cursor_old = conn_old.cursor()
  conn_new = psycopg2.connect("dbname='%s' user='%s' host='%s' password='%s'"
                              %(newdb_name, newdb_user, newdb_host, newdb_pass))
  cursor_new = conn_new.cursor()

  # Get a list of entries from old_site
  cursor_old.execute("SELECT id, name, slug, text, html, date, upd_date,"
                     +"is_draft, tags FROM blog_post")
  old_posts = cursor_old.fetchall() # Not good on large sites

  # For each item in old_site
  for p in old_posts:
    p_id = p[0]
    p_name = p[1]
    p_slug = p[2]
    p_text = p[3]
    p_html = p[4]
    p_date = p[5]
    p_upd_date = p[6]
    if p[7]: p_is_draft = 0
    else: p_is_draft = 2
    p_tags = convert_tags(p[8])
    # Move entry
    statement = "INSERT INTO zinnia_entry (%s) VALUES (%s) RETURNING id" \
                %("status, last_update, comment_enabled, tags, image, title, "
                  + "excerpt, slug, content, end_publication, start_publication, "
                  + "creation_date, pingback_enabled, login_required, password, "
                  + "template, featured", 
                  "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                  + "%s, %s, %s")
    val_list = (p_is_draft, p_upd_date, False, p_tags, "", p_name, "", p_slug,
                p_html, None, p_date, p_date, False, False, "",
                "entry_detail.html", True)
    cursor_new.execute(statement, val_list)
    new_id = cursor_new.fetchone()[0]
    conn_new.commit()
    # Link to author
    statement = "INSERT INTO zinnia_entry_authors (%s) VALUES (%s)" \
                %("entry_id, user_id", "%s, %s")
    val_list = (new_id, newdb_auth_id)
    cursor_new.execute(statement, val_list)
    conn_new.commit()
    # Link to site
    statement = "INSERT INTO zinnia_entry_sites (%s) VALUES (%s)" \
                %("entry_id, site_id", "%s, %s")
    val_list = (new_id, newdb_site_id)
    cursor_new.execute(statement, val_list)
    conn_new.commit()
    # Link to tags
    for t in p_tags.split():
      statement = "SELECT id FROM tagging_tag WHERE name=(%s)" %("%s")
      val_list = (t,)
      cursor_new.execute(statement, val_list)
      try:
        t_id = cursor_new.fetchone()[0]
      except TypeError:
        statement = "INSERT INTO tagging_tag (%s) VALUES (%s) RETURNING id" \
                    %("name", "%s")
        val_list = (t,)
        cursor_new.execute(statement, val_list)
        t_id = cursor_new.fetchone()[0]
        conn_new.commit()
      statement = "INSERT INTO tagging_taggeditem(%s) VALUES (%s)" \
                  %("tag_id, content_type_id, object_id", "%s, %s, %s")
      val_list = (t_id, 13, new_id)
      cursor_new.execute(statement, val_list)
      conn_new.commit()
    # Move comments
    statement = "SELECT id FROM comment_nodes WHERE object_id=(%s)" %("%s")
    val_list = (p_id,)
    cursor_old.execute(statement, val_list)
    comments = cursor_old.fetchall()
    for vals in comments:
      c_id = vals[0]
      statement = "SELECT user_id, pub_date, body FROM comment_nodes WHERE id=(%s)"\
                  %("%s")
      val_list = (c_id,)
      cursor_old.execute(statement, val_list)
      comment_details = cursor_old.fetchall()[0]
      statement = "SELECT first_name, email, site FROM auth_user WHERE id=(%s)" \
                  %("%s")
      val_list = (comment_details[0],) # user id
      cursor_old.execute(statement, val_list)
      user_details = cursor_old.fetchall()[0]
      statement = "INSERT INTO django_comments(%s) VALUES (%s)" \
                  %("content_type_id, object_pk, site_id, user_id, user_name, "
                    + "user_email, user_url, comment, submit_date, ip_address, "
                    + "is_public, is_removed",
                    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s")
      val_list = (13, new_id, newdb_site_id, None, user_details[0], user_details[1],
                  user_details[2], comment_details[2], comment_details[1],
                  "0.0.0.0", True, False)
      cursor_new.execute(statement, val_list)
      conn_new.commit()
    # Pingbacks
    statement = "SELECT id FROM pingback WHERE object_id=(%s)" %("%s")
    val_list = (p_id,)
    cursor_old.execute(statement, val_list)
    pingbacks = cursor_old.fetchall()
    for vals in pingbacks:
      pb_id = vals[0]
      statement = "SELECT url, date, title, content FROM pingback WHERE id=(%s)" \
                   %("%s")
      val_list = (pb_id,)
      cursor_old.execute(statement, val_list)
      pb_details = cursor_old.fetchall()[0]
      statement = "INSERT INTO django_comments(%s) VALUES (%s) RETURNING id" \
                  %("content_type_id, object_pk, site_id, user_id, user_name, "
                    + "user_email, user_url, comment, submit_date, ip_address, "
                    + "is_public, is_removed",
                    "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s")
      val_list = (13, new_id, newdb_site_id, None, pb_details[2][:49], "",
                  pb_details[0], pb_details[3], pb_details[1], 
                  "0.0.0.0", True, False)
      cursor_new.execute(statement, val_list)
      pb_new_id = cursor_new.fetchone()[0]
      statement = "INSERT INTO django_comment_flags(%s) VALUES (%s)" \
                  %("user_id, comment_id, flag, flag_date",
                    "%s, %s, %s, %s")
      val_list = (newdb_auth_id, pb_new_id, "pingback", pb_details[1])
      cursor_new.execute(statement, val_list)
      conn_new.commit()



## Byteflow: blog_post ##
# id              | integer                  | 5
# site_id         | integer                  | 1
# author_id       | integer                  | 6
# name            | character varying(256)   | Django-cms: Not Too Shabby
# slug            | character varying(256)   | django-cms
# text            | text                     | **Summary:** Herein . . . \r   +
# render_method   | character varying(15)    | markdown
# html            | text                     | <p><strong>Summary . . . 
# date            | timestamp with time zone | 2009-03-04 10:47:28-07
# upd_date        | timestamp with time zone | 2009-09-21 16:35:48.503664-06
# is_draft        | boolean                  | f
# enable_comments | boolean                  | f
# tags            | character varying(255)   | application reviews, just trying ...
#------------
## Zinnia: zinnia_entry ##
# status            | integer                  | 2=published 1=hidden 0=draft
# last_update       | timestamp with time zone | 2012-10-13 08:40:59.090307-06
# comment_enabled   | boolean                  | t
# tags              | character varying(255)   | tag two tag_three
# image             | character varying(100)   | 
# title             | character varying(255)   | Test Entry
# excerpt           | text                     | summary text
# slug              | character varying(255)   | test-entry
# content           | text                     | <p>A test paragraph</p>
# end_publication   | timestamp with time zone | 
# start_publication | timestamp with time zone | 2012-10-13 08:22:27-06
# creation_date     | timestamp with time zone | 2012-10-13 01:18:26-06
# id                | integer                  | 1
# pingback_enabled  | boolean                  | t
# login_required    | boolean                  | f
# password          | character varying(50)    | 
# template          | character varying(250)   | entry_detail.html
# featured          | boolean                  | t

## Byteflow: comment_nodes
# id              | integer                  | auto sequence
# user_id         | integer                  | id of commenter
# pub_date        | timestamp with time zone | 2009-07-29 11:41:24-06
# upd_date        | timestamp with time zone | 2009-07-29 11:41:24-06
# body            | text                     | Wait, I run . . .
# body_html       | text                     | <p>Wait, I run . . .
# reply_to_id     | integer                  | blank on no reply
# approved        | boolean                  | t
# content_type_id | integer                  | 11
# object_id       | integer                  | 3
# lft             | integer                  | 1
# rght            | integer                  | 4
#------------
## Zinnia: django_comments
# id              | integer                  | auto sequence
# content_type_id | integer                  | type_id of entry=13
# object_pk       | text                     | id of entry
# site_id         | integer                  | 1
# user_id         | integer                  | 1
# user_name       | character varying(50)    | Richard Last
# user_email      | character varying(75)    | test@example.com
# user_url        | character varying(200)   | http://example.com
# comment         | text                     | Another Comment
# submit_date     | timestamp with time zone | 2012-10-13 19:50:10.805563-06
# ip_address      | inet                     | 192.168.0.1
# is_public       | boolean                  | t
# is_removed      | boolean                  | f

## Byteflow: pingback
# id              | integer                  | auto sequence
# url             | character varying(200)   | http://lukepeter . . .
# date            | timestamp with time zone | 2010-01-17 . . . 
# approved        | boolean                  | t
# title           | character varying(100)   | Luke.com: Byte
# content         | text                     | If you are new to 
# content_type_id | integer                  | 11
# object_id       | integer                  | 1
#------------
## Zinnia: django_comment_flags -- only needs entry on pingback or trackback
# id         | integer                  | auto sequence
# user_id    | integer                  | 1
# comment_id | integer                  | id of comment from django_comments
# flag       | character varying(30)    | "pingback" | "trackback"
# flag_date  | timestamp with time zone | 2012-10-13 19:50:10.805563-06

## Byteflow and Zinnia: auth_user
# id           | integer                  | auto sequence
# username     | character varying(30)    | dave-m.org
# first_name   | character varying(30)    | Dave
# last_name    | character varying(30)    | S
# email        | character varying(75)    | dave@m.org
# password     | character varying(128)   | sha1
# is_staff     | boolean                  | f
# is_active    | boolean                  | f
# is_superuser | boolean                  | f
# last_login   | timestamp with time zone | 2009-09 . . .
# date_joined  | timestamp with time zone | 2009-09 . . .
# site         | character varying(200)   | http://the
# email_new    | character varying(75)    | 
