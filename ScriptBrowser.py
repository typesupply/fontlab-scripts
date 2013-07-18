"""
ScriptBrowser:  A nicer way to browse and execute scripts in FontLab.
Version 1.0

This script scans a directory or list of directories for sub directories which are then scanned for scripts.

Main Directory
    Sub-Directory A
        a_script.py
        another_script.py
    Sub-Directory B
        a_script.py
        another_script.py
    etc.

This is useful for categorizing scripts. For example my scripts are organized like this:

FontLab_Scripts
    Font
        DecomposeComponents.py
        BuildAccents.py
    Glyph
        CorrectPathDirection.py
        RemoveOverlap.py
    UFO
        ExportCurrent.py
        ImportOne.py
        ExportDirectory.py
        ImportDirectory.py
    etc.

This will also scan the scripts for a title and some documentation.
The title must be on the first line of the script and it must be preceeded by a #.
Documentation will be read as the first triple quoted string in the script.
This info will be displayed in the UI when a script is selected.

THIS SCRIPT IS SUPPLIED AS IS. NO WARRANTEES. NO GUARANTEES. NO QUESTIONS.
(C) 2005 Tal Leming
"""

###########################################
# you must hardwire the location of your scripts directory here
#
SCRIPT_DIRECTORY = None
#
###########################################

import os
import sys
import re
from FL import *

assert SCRIPT_DIRECTORY is not None, "Path to script directory is undefined!"
if isinstance(SCRIPT_DIRECTORY, list):
    for p in SCRIPT_DIRECTORY:
        assert os.path.isdir(p)
else:
    assert os.path.isdir(SCRIPT_DIRECTORY)

##
## functions for loading data from scripts
##

def runScriptDirectory(path):
    """run through a directory and get script from each sub directory"""
    sections = {}
    if isinstance(path, list):
        for p in path:
            for section, scripts in runScriptDirectory(p).items():
                if section not in sections:
                    sections[section] = {}
                sections[section].update(scripts)
    else:
        for fileName in os.listdir(path):
            if fileName.startswith("."):
                continue
            fullPath = os.path.join(path, fileName)
            if os.path.isdir(fullPath):
                found = runSubDirectory(fullPath)
                if fileName in sections:
                    sections[fileName].extend(found)
                else:
                    sections[fileName] = found
    return sections

def runSubDirectory(path):
    """run through a directory of scripts and gather information about each script"""
    scripts = {}
    for fileName in os.listdir(path):
        if fileName.startswith("."):
            continue
        base, ext = os.path.splitext(fileName)
        if ext.lower() == ".py":
            fullPath = os.path.join(path, fileName)
            title, doc = scanScript(fullPath)
            if title is None or len(title) == 0:
                title = base
            if doc is None:
                doc = ""
            scripts[title] = (doc, fullPath)
    return scripts

doc_RE = re.compile(
        "[\"\']{3}" # triple quote
        "([\S\s]*)" # text
        "[\"\']{3}" # triple quote
        )
title_RE = re.compile(
        "#\s*"
        "(.*)"
        )

def scanScript(path):
    """get the title and documentation from the script"""
    title = None
    doc = None
    f = open(path, "rb")
    text = f.read().replace("\r\n", "\n").replace("\r", "\n")
    f.close()
    # extract doc
    docSearch = doc_RE.findall(text)
    if docSearch:
        doc = docSearch[0].strip()
    # extract name
    titleSearch = title_RE.match(text)
    if titleSearch is not None:
        title = titleSearch.group(1)
        if title[:4] == "FLM:":
            title = title[4:]
        title = title.strip()
    return title, doc

##
## the UI
##

width = 365
height = 400

class ScriptBrowser:

    """A user freindly interface for executing scripts"""

    def __init__(self, scriptDirectory):

        self.d = Dialog(self)
        self.d.size = Point(width, height)
        self.d.Center()
        self.d.title = "ScriptBrowser"

        self.scriptDict = runScriptDirectory(scriptDirectory)
        self.category_select = self.scriptDict.keys()
        self.category_select.sort()
        self.category_select_index = None
        self.script_select = []
        self.script_select_index = None
        self.doc_label = "Documentation..."
        self.selected = ""

        self.d.AddControl(LISTCONTROL, Rect(15, 15, 120, height-130),  "category_select", STYLE_LIST, "")
        self.d.AddControl(LISTCONTROL, Rect(130, 15, 350, height-130),  "script_select", STYLE_LIST, "")
        self.d.AddControl(STATICCONTROL, Rect(15, height-120, width-15, height-100), "selected_label", STYLE_LABEL, "Selected:")
        self.d.AddControl(STATICCONTROL, Rect(15, height-100, width-15, height-60), "doc_label", STYLE_LABEL, "Documentation...")

        self.d.Run()

    def on_category_select(self, code):
        self.d.GetValue("category_select")
        if self.category_select_index != '-1':
            self.category = self.category_select[int(self.category_select_index)]
            self.script_select = self.scriptDict[self.category].keys()
            self.script_select.sort()
            self.d.PutValue("script_select")

    def on_script_select(self, code):
        self.d.GetValue("script_select")
        if self.script_select_index != "-1":
            name = self.script_select[int(self.script_select_index)]
            self.selected = self.scriptDict[self.category][name]
            doc, path = self.selected
            self.doc_label = doc
            self.selected_label = name
            self.d.PutValue("doc_label")
            self.d.PutValue("selected_label")

    def on_ok(self, code):
        self.d.End()
        # run the selected script
        if self.selected != "":
            doc, path = self.selected
            saveArgv = sys.argv
            saveChdir = os.getcwd()
            sys.argv = [path]
            os.chdir(os.path.dirname(path))
            try:
                namespace = {
                        "__file__" : path,
                        "__name__" : "__main__",
                        }
                
                f = open(path, 'rb')
                data = '\n'.join(f.read().splitlines()) + '\n'
                f.close()
                exec data in namespace
            finally:
                sys.argv = saveArgv
                os.chdir(saveChdir)

    def on_cancel(self, code):
        pass


ScriptBrowser(SCRIPT_DIRECTORY)
