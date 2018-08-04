#!/usr/bin/env python
"""
Gmail Filter Manager
"""

from __future__ import print_function

import os
import sys
import httplib2
from oauth2client.file import Storage
from oauth2client.tools import run_flow, argparser
from oauth2client.client import OAuth2WebServerFlow
from apiclient.discovery import build

__prog__ = os.path.basename(__file__)
__description__ = __doc__
__author__ = 'rcmdnk'
__copyright__ = 'Copyright (c) 2018 rcmdnk'
__credits__ = ['rcmdnk']
__license__ = 'MIT'
__version__ = 'v0.0.1'
__date__ = '14/Jul/2018'
__maintainer__ = 'rcmdnk'
__email__ = 'rcmdnk@gmail.com'
__status__ = 'Prototype'

AUTHENTICATION_FILE = os.environ['HOME'] + '/.config/gmail_filter/auth'
GOOGLE_CLIENT_ID = '937185253369-2er0fqahlnpn7tgou1i4mi2for07mhci.'\
    'apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'J2cnuhv-CS33SLnfUS-8lZfo'

class GmailFilterManager():

    def __init__(self):
        self.authentication_file = os.path.expanduser(AUTHENTICATION_FILE)
        self.google_client_id = GOOGLE_CLIENT_ID
        self.google_client_secret = GOOGLE_CLIENT_SECRET
        self.service = None
        self.address = None
        self.filters = None
        self.labels = None
        self.yaml_output = "mailFilters.yaml"

        self.dic_xml2api = {
            "hasTheWord": "query",
            "doesNotHaveTheWord": "negatedQuery",
            "sizeOperator": "sizeComparison",
        }
        self.dic_api2xml = {v: k for k, v in self.dic_xml2api.items()}

        self.dic_label_xml2api = {
            "shouldArchive": ("removeLabelIds", "INBOX"),
            "shouldMarkAsRead": ("removeLabelIds", "UNREAD"),
            "shouldStar": ("addLabelIds", "STARRED"),
            "shouldTrash": ("addLabelIds", "TRASH"),
            "shouldNeverSpam": ("removeLabelIds", "SPAM"),
            "shouldAlwaysMarkAsImportant": ("addLabelIds", "IMPORTANT"),
            "shouldNeverMarkAsImportant": ("removeLabelIds", "IMPORTANT"),
            "smartLabelToApply": ("addLabelIds", "CATEGORY_"),
        }
        self.dic_label_api2xml = {v: k for k, v
                                  in self.dic_label_xml2api.items()}

        self.dic_size_xml2api = {
            "s_sl": "larger",
            "s_ss": "smaller",
        }
        self.dic_size_api2xml = {v: k for k, v
                                 in self.dic_size_xml2api.items()}


    def authentication(self, storage):
        return run_flow(
            OAuth2WebServerFlow(
                client_id=self.google_client_id,
                client_secret=self.google_client_secret,
                scope=['https://www.googleapis.com/auth/gmail.modify']),
            storage, argparser.parse_args([]))

    def build_service(self, rebuild=False):
        conf_dir = os.path.dirname(self.authentication_file)
        if not os.path.isdir(conf_dir):
            os.makedirs(conf_dir)
        storage = Storage(self.authentication_file)
        credentials = storage.get()

        if rebuild or credentials is None or credentials.invalid:
            credentials = self.authentication(storage)

        http = httplib2.Http()
        http = credentials.authorize(http)

        service = build('gmail', 'v1', http=http)

        prof = service.users().getProfile(userId='me').execute()
        self.address = prof['emailAddress']
        #print("My address: %s" % self.address)

        return service

    def get_service(self):
        if self.service is None:
            self.service = self.build_service()
        return self.service

    def get_filters(self):
        if self.filters is not None:
            return
        self.filters = self.get_service().users().settings().filters().list(
            userId='me').execute()["filter"]

    def show_filters(self, raw=False):
        self.get_filters()
        if raw:
            for f in self.filters:
                print(f)
            return
        for f in self.filters:
            print("criteria:")
            for a in f["criteria"]:
                print("  %s: %s" % (a, f["criteria"][a]))
            print("action:")
            for a in f["action"]:
                print("  %s: %s" % (a, f["action"][a]))
            print("")

    def make_yaml(self):
        self.get_filters()
        data = {
            "filters": [],
            "namespaces": {
                "apps": "http://schemas.google.com/apps/2006",
                "atom": "http://www.w3.org/2005/Atom",
            }
        }

        for f in self.filters:
            xml_filter = {}
            for k, v in f["criteria"].items():
                key, value = self.criteria_api2xml(k, v)
                xml_filter[key] = value
                if key == "size":
                    xml_filter["sizeUnit"] = "s_sb"

            for k, v in f["action"].items():
                if k == "addLabelIds":
                    for label in v:
                        if ("addLabelIds", label) in self.dic_label_api2xml:
                            xml_filter[self.dic_label_api2xml[
                                ("addLabelIds", label)]] = "true"
                            continue
                        if not "label" in xml_filter:
                            xml_filter["label"] = []
                        xml_filter["label"].append(self.label_id2name(label))
                elif k == "removeLabelIds":
                    for label in v:
                        if ("removeLabelIds", label) in self.dic_label_api2xml:
                            xml_filter[self.dic_label_api2xml[
                                ("removeLabelIds", label)]] = "true"
                            continue
                else:
                    xml_filter[k] = v

            data["filters"].append(xml_filter)

        with open(self.yaml_output, "w") as stream:
            import ruamel.yaml
            yaml = ruamel.yaml.YAML()
            yaml.dump(data, stream=stream)

    def criteria_api2xml(self, key, value):
        key_out = key
        value_out = value
        if key in self.dic_api2xml:
            key_out = self.dic_api2xml[key]
        if key == "sizeComparison":
            value_out = self.dic_size_api2xml[value]
        return key_out, value_out

    def action_api2xml(self, key, value):
        key_out = key
        value_out = value
        if key in self.dic_label_api2xml:
            key_out = self.dic_api2xml[key]
        if key == "sizeComparison":
            value_out = self.dic_size_api2xml[value]

        if key == "query":
            xml_key = "hasTheWord"
        elif key == "query":
            xml_key = "hasTheWord"

    def get_labels(self):
        if self.labels is not None:
            return
        self.labels = self.get_service().users().labels().list(
            userId='me').execute()["labels"]

    def show_labels(self, raw=False):
        self.get_labels()
        if raw:
            for l in self.labels:
                print(l)
            return
        print("===User labels===")
        for l in sorted(filter(lambda x: x["type"] == "user", self.labels), key=lambda x: x["name"]):
            print("%s: %s" % (l["name"], l["id"]))
        print("\n===System labels===")
        for l in sorted(filter(lambda x: x["type"] != "user", self.labels), key=lambda x: x["name"]):
            print("%s: %s" % (l["name"], l["id"]))

    def label_id2name(self, label_id):
        self.get_labels()
        candidates = filter(lambda x: x["id"] == label_id, self.labels)
        if len(candidates) != 1:
            print("Wrong label id? id: %s, candidates: %s" % (label_id, str(candidates)))
            sys.exit(1)
        return candidates[0]["name"]

    def label_name2id(self, name):
        self.get_labels()
        candidates = filter(lambda x: x["name"] == name, self.labels)
        if len(candidates) != 1:
            print("Wrong label name? candidates: %s" % str(candidates))
            sys.exit(1)
        return candidates[0]["id"]

def main():
    gfm = GmailFilterManager()
    #gfm.show_filters(raw=True)
    #gfm.show_labels(raw=True)
    gfm.make_yaml()

if __name__ == '__main__':
    main()
