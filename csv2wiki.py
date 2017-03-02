#!/usr/bin/env python
#
# NOTES: 
#
#  - If you run create/delete multiple times, you may need to run
#
#      $ php maintenance/rebuildall.php
#
#    in your mediawiki instance to link pages to their categories properly.
#    This script takes about 10 minutes to run for a wiki with <300 pages.
#
#  - If you get errors saving some pages, read this:
#
#    If your MediaWiki instance has Extension:SpamBlacklist enabled,
#    then you may get errors when trying to create pages that contain
#    certain kinds of URLs or email addresses (namely, URLs or email
#    addresses that SpamBlacklist thinks look spammy). 
#    
#    One solution is to just turn off Extension:SpamBlacklist entirely.
#    But even if you don't have that kind of administrative access,
#    you might still have enough access to *configure* the extension, 
#    in which case you can whitelist everything via a catchall regexp.
#    Visit one or of of these pages:
#
#      https://mywiki.example.com/index.php?title=MediaWiki:Spam-whitelist
#      https://mywiki.example.com/index.php?title=MediaWiki:Email-whitelist
#
#    You'll see a commented-out explanation of how the whitelist works.
#    Just add a line with ".*", as in this example...
#
#      # External URLs matching this list will *not* be blocked even if they would
#      # have been blocked by blacklist entries.
#      #
#      # Syntax is as follows:
#      #   * Everything from a "#" character to the end of the line is a comment
#      #   * Every non-blank line is a regex fragment which will only match hosts inside URLs
#      .*
#
#    ...to be able to save a page with any URL (and things work
#    similarly on the Email-whitelist page).
#
# Copyright (C) 2017 Open Tech Strategies, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import csv
from mwclient import Site
from mwclient import errors
import getopt, sys


def create_pages(csv_file, site_url, username, password):
    """
    Create one wiki page for each line in a supplied CSV_FILE.  The CSV
    should have a header row and at least one row of content.

    SITE_URL: The url of the Mediawiki instance
    (e.g. localhost/mediawiki).

    USERNAME: The username for the Mediawiki instance.  Must have
    permission to read, create, and edit pages.

    PASSWORD: The password that corresponds to the Mediawiki username.
    """
    site = Site(('http', site_url), path='/',)
    site.login(username, password)
    
    toc_page = site.pages['List of Proposals']
    toc_text = ""
    categories = []
    
    # read in csv
    with open(csv_file, 'rb') as csvfile:
        reader = csv.reader(csvfile, delimiter=',', quotechar='"')
        is_header = True
        row_num = 0
        for row in reader:
            if is_header:
                # if this is the first row, save headers
                header_array = []
                for cell in row:
                    header_array.append(cell)
                is_header = False
            else:
                # Looping over the cells in the row.  Name the sections
                # according to headers.
                cell_num = 0
                for cell in row:
                    if cell_num == 0:
                        # For this new line, generate a mediawiki page
                        title = 'Proposal_'+ str(row_num) + ': ' + cell
                        print("CREATING: " + title)
                        page = site.pages[title]
                        # Add the new page to the list of pages
                        toc_text += '* [[' + title + ']] \n'
                        # Set the contents of each cell to their own section.
                    if cell is not "":
                        # A section can only be created with some text
                        # 
                        if cell_num == (len(row) - 1):
                            # For the last column, create a category (NOTE:
                            # this is overly customized to a certain set of
                            # CSVs; feel free to remove this conditional for
                            # other CSVs)
                            cell_text = '[[Category:' + cell + ']]'
                            
                            # Add this to the list of categories, unless
                            # it's already there:
                            if cell not in categories:
                                categories.append(cell)
                        else:
                            cell_text = cell
                            # TODO: it's probably bad practice to save each page
                            # many times, and it's definitely slowing down the
                            # script.
                            #
                            # What's the deal with save/edit/text?  Send
                            # just one API request per page.
                        try:
                            page.save(cell_text, section=cell_num, sectiontitle=header_array[cell_num])
                        except errors.APIError:
                            page.save(cell_text, section='new', sectiontitle=header_array[cell_num])
                                
                    cell_num += 1
                
            row_num += 1
        
    # create the TOC page.
    toc_page.save(toc_text)
    
    # generate the category pages
    for category in categories:
        print(category)
        page_title = 'Category:' + category
        page = site.pages[page_title]
        page.save("")

    return

def delete_pages(site_url, username, password, search_string='Proposal '):
    """
    Deletes wiki pages matching SEARCH_STRING.

    SITE_URL: The url of the Mediawiki instance
    (e.g. localhost/mediawiki).

    USERNAME: The username for the Mediawiki instance.  Must have
    permission to delete pages.

    PASSWORD: The password that corresponds to the Mediawiki username.
    """
    site = Site(('http', site_url), path='/',)
    site.login(username, password)
    
    search_result = site.search(search_string)
    for result in search_result:
        # get as a page
        print("DELETING: " + result['title'])
        page = site.pages[result['title']]
        # delete with extreme prejudice
        page.delete()

    return

def usage():
# It would be simple to change the main() function to accept a different
# url via user input.
#
# TODO: add a wrapper class to take different wiki types
#
# Usage:
# $ python csv2wiki.py [create | delete] <filename> <username> <password>
#
    error_message = """ 
    This WIP parses a CSV and transforms each line into a MediaWiki
    page. It takes a file with configuration options as an argument.  To
    use it, run:

        To create pages:
            ./csv2wiki --file <config_file> 

        To delete pages: 
            ./csv2wiki --delete --file <config_file>

    This script currently assumes that you are working with a local
    instance of Mediawiki located at 'localhost/mediawiki'.  

    The create_pages script is meant to be run once per CSV/wiki pair.
    It might have unexpected results if run more than once.  Run with
    the --delete option to remove all existing pages.
    
    Creating 250 wiki pages takes about 5 minutes using this script.
    See the source for troubleshooting tips.
    """
    print(error_message)
    return

def parse_config_file(config_file):
    """
    Parses a CONFIG_FILE into configuration parameters for use in other functions.
    """
    return

def main():
    """
    By default, creates wiki pages from a supplied CSV.  Optionally,
    deletes those pages instead.

    """
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'hd:f:', ("help", "delete", "file"))
    except getopt.GetoptError as err:
        sys.stderr.write("ERROR: '%s' \n" % err)
        usage()
        sys.exit(2)

    filename = None
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            return
        elif o in ("-d", "--delete"):
            search_keyword = a
            try:
                delete_pages('localhost/mediawiki', sys.argv[2], sys.argv[3])
                return
            except IndexError as err:
                sys.stderr.write("ERROR: '%s' \n" % err)
                usage()
                return
        elif o in ("-f", "--file"):
            filename = a
        else:
            sys.stderr.write("ERROR: Unhandled option " + o)

    if filename is None:
        usage()
    else:
        config_settings = parse_config_file(filename)
    
    # by default, run create:
    try:
        create_pages(config_settings)
    except IndexError as err:
        sys.stderr.write("ERROR: '%s' \n" % err)
        usage()
    return


if __name__ == '__main__':
    main()

