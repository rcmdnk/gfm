#!/usr/bin/env python
"""
Gmail Filter Manager
https://github.com/rcmdnk/gfm
"""

from __future__ import print_function

import os
import sys
import xml.etree.ElementTree as ET
import argparse
import xml.dom.minidom
import httplib2
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
import ruamel.yaml
from oauth2client.file import Storage
from oauth2client.tools import run_flow, argparser
from oauth2client.client import OAuth2WebServerFlow
from apiclient.discovery import build

__prog__ = "gfm"
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

AUTH_FILE = os.environ['HOME'] + '/.config/gmail_filter/auth'
GOOGLE_CLIENT_ID = '937185253369-2er0fqahlnpn7tgou1i4mi2for07mhci.'\
    'apps.googleusercontent.com'
GOOGLE_CLIENT_SECRET = 'J2cnuhv-CS33SLnfUS-8lZfo'


class GmailFilterManager():

    def __init__(self, **kw):
        for k, v in kw.items():
            self.opt[k] = v

        # Set defaults if it is called w/o args (check dummy in argparser)
        if "dummy" not in self.opt:
            self.opt = vars(self.get_parser().parse_args())

        if self.opt["client_id"] is None:
            self.opt["client_id"] = GOOGLE_CLIENT_ID
        if self.opt["client_secret"] is None:
            self.opt["client_secret"] = GOOGLE_CLIENT_SECRET

        self.service = None
        self.address = None
        self.filters = None
        self.filters_api = None
        self.labels = None

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

        if ((type(self.opt["command"]) == str and self.opt["command"] == "") or
                (type(self.opt["command"]) == str and
                 len(self.opt["command"]) == 0) or
                (self.opt["command"] is None)):
            return

        if type(self.opt["command"]) == str:
            self.opt["command"] = [self.opt["command"]]

        for c in self.opt["command"]:
            if c == "xml2yaml":
                self.read_xml()
                self.write_xml()
            elif c == "yaml2xml":
                self.read_yaml()
                self.write_xml()
            elif c == "get":
                self.get()
            elif c == "put":
                self.put()
            elif c == "show_filters_api":
                self.show_filters()
            elif c == "show_labels_api":
                self.show_labels()
            else:
                raise ValueError("Invalid command: %s" % c)

    def clean(self):
        self.filters = None
        self.filters_api = None
        self.labels = None

    def authentication(self, storage):
        return run_flow(
            OAuth2WebServerFlow(
                client_id=self.opt["client_id"],
                client_secret=self.opt["client_secret"],
                scope=['https://www.googleapis.com/auth/gmail.modify']),
            storage, argparser.parse_args([]))

    def build_service(self, rebuild=False):
        conf_dir = os.path.dirname(self.opt["auth_file"])
        if not os.path.isdir(conf_dir):
            os.makedirs(conf_dir)
        storage = Storage(self.opt["auth_file"])
        credentials = storage.get()

        if rebuild or credentials is None or credentials.invalid:
            credentials = self.authentication(storage)

        http = httplib2.Http()
        http = credentials.authorize(http)

        service = build('gmail', 'v1', http=http)

        prof = service.users().getProfile(userId='me').execute()
        self.opt["address "] = prof['emailAddress']
        if self.opt["debug"]:
            print("My address: %s" % self.opt["address"])

        return service

    def get_service(self):
        if self.service is None:
            self.service = self.build_service()
        return self.service

    def read_xml(self):
        namespaces = {str(x[0]) if x[0] != "" else "atom": x[1]
                      for _, x in ET.iterparse(self.opt["input_xml"],
                                               events=['start-ns'])}

        tree = ET.parse(self.opt["input_xml"])
        root = tree.getroot()

        filter_list = []
        for e in root.findall("./atom:entry", namespaces):
            properties = {}
            for p in e.findall("./apps:property", namespaces):
                name = p.get("name")
                value = p.get("value")
                properties[name] = DoubleQuotedScalarString(value)
            if "size" not in properties:
                for noneed in ["sizeOperator", "sizeUnit"]:
                    if noneed in properties:
                        del properties[noneed]
            filter_list.append(properties)

        self.filters = {"namespaces": namespaces, "filter": filter_list}

    def write_yaml(self):
        yaml = ruamel.yaml.YAML()
        yaml.indent(mapping=2, sequence=4, offset=2)
        with open(self.opt["output_yaml"], "w") as stream:
            yaml.dump(self.filters, stream=stream)

    def read_yaml(self):
        yaml = ruamel.yaml.YAML()
        with open(self.opt["input_yaml"], "r") as f:
            self.filters = yaml.load(f)

        if "namespaces" in self.filters:
            if "atom" in self.filters["namespaces"]:
                self.filters["namespaces"][""] -\
                    self.filters["namespaces"]["atom"]
                del self.filters["namespaces"]["atom"]
        else:
            self.filters["namespaces"] = {
                "": "http://www.w3.org/2005/Atom",
                "apps": "http://schemas.google.com/apps/2006"
            }

    def write_xml(self):
        for k, v in self.filters["namespaces"].items():
            ET.register_namespace(k, v)

        root = ET.Element('feed')
        for f in self.filters["filters"]:
            if "label" in f:
                labels = f["label"] if isinstance(
                    f["label"], list) else [f["label"]]
                del f["label"]
            else:
                labels = [None]
            for label in labels:
                entry = ET.SubElement(
                    root, "{" + self.filters["namespaces"][""] + "}" + 'entry')
                properties = f
                if label is not None:
                    properties["label"] = label
                for k, v in properties.items():
                    ET.SubElement(
                        entry,
                        "{" + self.filters["namespaces"]["apps"] + "}property",
                        attrib={"name": k, "value": v}
                    )

        my_filter = xml.dom.minidom.parseString(ET.tostring(root)).toprettyxml(
            indent="  ", encoding="utf-8")
        if sys.version_info.major > 2:
            my_filter = my_filter.decode()

        with open(self.opt["output_xml"], "w") as f:
            f.write(my_filter)

    def get_filters(self):
        if self.filters_api is not None:
            return
        self.filters_api = self.get_service().users().settings(
        ).filters().list(userId='me').execute()

    def show_filters(self):
        self.get_filters()
        if self.opt["raw"]:
            print(self.filters_api)
            return
        for f in self.filters_api["filter"]:
            print("criteria:")
            for a in f["criteria"]:
                print("  %s: %s" % (a, f["criteria"][a]))
            print("action:")
            for a in f["action"]:
                print("  %s: %s" % (a, f["action"][a]))
            print("")

    def get(self):
        self.get_filters()
        data = {
            "filter": [],
            "namespaces": {
                "apps": "http://schemas.google.com/apps/2006",
                "atom": "http://www.w3.org/2005/Atom",
            }
        }

        for f in self.filters["filter"]:
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
                        if "label" not in xml_filter:
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

            data["filter"].append(xml_filter)

        with open(self.opt["output_yaml"], "w") as stream:
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
            key_out = "hasTheWord"
        elif key == "query":
            key_out = "hasTheWord"

        return key_out, value_out

    def get_labels(self):
        if self.labels is not None:
            return
        self.labels = self.get_service().users().labels().list(
            userId='me').execute()["labels"]

    def show_labels(self):
        self.get_labels()
        if self.opt["raw"]:
            for l in self.labels:
                print(l)
            return
        print("===User labels===")
        for l in sorted(filter(lambda x: x["type"] == "user", self.labels),
                        key=lambda x: x["name"]):
            print("%s: %s" % (l["name"], l["id"]))
        print("\n===System labels===")
        for l in sorted(filter(lambda x: x["type"] != "user", self.labels),
                        key=lambda x: x["name"]):
            print("%s: %s" % (l["name"], l["id"]))

    def label_id2name(self, label_id):
        self.get_labels()
        candidates = filter(lambda x: x["id"] == label_id, self.labels)
        if len(candidates) != 1:
            print("Wrong label id? id: %s, candidates: %s" %
                  (label_id, str(candidates)))
            sys.exit(1)
        return candidates[0]["name"]

    def label_name2id(self, name):
        self.get_labels()
        candidates = filter(lambda x: x["name"] == name, self.labels)
        if len(candidates) != 1:
            print("Wrong label name? candidates: %s" % str(candidates))
            sys.exit(1)
        return candidates[0]["id"]

    def put(self):
        pass

    @staticmethod
    def get_parser():
        input_xml_parser = argparse.ArgumentParser(add_help=False)
        input_xml_parser.add_argument(
            "-x", "--input_xml", action="store", dest="input_xml",
            default="mailFilters.xml", help="Input XML file name")
        input_yaml_parser = argparse.ArgumentParser(add_help=False)
        input_yaml_parser.add_argument(
            "-y", "--input_yaml", action="store", dest="input_yaml",
            default="mailFilters.yaml", help="Input YAML file name")
        output_xml_parser = argparse.ArgumentParser(add_help=False)
        output_xml_parser.add_argument(
            "-X", "--output_xml", action="store", dest="output_xml",
            default="filters.xml", help="Output XML file name")
        output_yaml_parser = argparse.ArgumentParser(add_help=False)
        output_yaml_parser.add_argument(
            "-Y", "--output_yaml", action="store", dest="output_yaml",
            default="mailFilters.yaml", help="Output YAML file name")
        auth_file_parser = argparse.ArgumentParser(add_help=False)
        auth_file_parser.add_argument(
            "--auth_file", action="store", dest="auth_file",
            default=AUTH_FILE, help="Gmail API authentication file")
        client_id_parser = argparse.ArgumentParser(add_help=False)
        client_id_parser.add_argument(
            "--client_id", action="store", dest="client_id",
            default=None, help="Google Client ID")
        client_secret_parser = argparse.ArgumentParser(add_help=False)
        client_secret_parser.add_argument(
            "--client_secret", action="store", dest="client_secret",
            default=None, help="Google Client ID")
        raw_parser = argparse.ArgumentParser(add_help=False)
        raw_parser.add_argument(
            "-r", "--raw", action="store_true", dest="raw", default=False,
            help="Show raw output")
        debug_parser = argparse.ArgumentParser(add_help=False)
        debug_parser.add_argument(
            "-d", "--debug", action="store_true", dest="debug", default=False,
            help="Enable debug mode")
        dummy_parser = argparse.ArgumentParser(add_help=False)
        dummy_parser.add_argument(
            "--dummy", action="store_true", dest="dummy", default=True,
            help=argparse.SUPPRESS)

        parser = argparse.ArgumentParser(
            prog=__prog__,
            add_help=True,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            description=__description__,
            parents=[input_xml_parser, input_yaml_parser, output_xml_parser,
                     output_yaml_parser, auth_file_parser,
                     client_id_parser, client_secret_parser,
                     raw_parser, debug_parser,
                     dummy_parser],
        )

        subparsers = parser.add_subparsers(
            title="subcommands", metavar="[command]", help="", dest="command")

        desc = "Convert filters from XML to YAML"
        subparsers.add_parser(
            "xml2yaml", description=desc, help=desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            parents=[input_xml_parser, output_yaml_parser, debug_parser])

        desc = "Convert filters from YAML to XML"
        subparsers.add_parser(
            "yaml2xml", description=desc, help=desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            parents=[input_yaml_parser, output_xml_parser, debug_parser])

        desc = "Get filters by using API and make YAML"
        subparsers.add_parser(
            "get", description=desc, help=desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            parents=[output_yaml_parser, auth_file_parser,
                     client_id_parser, client_secret_parser, debug_parser])

        desc = "Put filters in YAML file to Gmail server by using API"
        subparsers.add_parser(
            "put", description=desc, help=desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            parents=[input_yaml_parser, auth_file_parser,
                     client_id_parser, client_secret_parser, debug_parser])

        desc = "Show filters taken by API"
        subparsers.add_parser(
            "show_filters_api", description=desc, help=desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            parents=[auth_file_parser, client_id_parser, client_secret_parser,
                     raw_parser, debug_parser])

        desc = "Show labels taken by API"
        subparsers.add_parser(
            "show_labels_api", description=desc, help=desc,
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            parents=[auth_file_parser, client_id_parser, client_secret_parser,
                     raw_parser, debug_parser])

        return parser


def main():
    parser = GmailFilterManager.get_parser()

    if len(sys.argv) == 1:
        parser.print_help()
        return

    args = parser.parse_args()
    GmailFilterManager(**vars(args))


if __name__ == '__main__':
    main()
