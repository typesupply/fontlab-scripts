# FLM: UFO Central
"""Export and import UFOs. Version 2.0"""

help = """
UFO Central
Version 2.1b

This script gives you fine-grained control over
importing and exporting UFO data.

Import
------

Select UFOs
Select the UFOs you wish to import data from.
You can select a directory and all UFOs from
the directory will be imported.

Save After Importing
Check to save the VFB files after importing.

Close After Importing
Check to close the VFBs after importing.


Export
------

Current Font
Check to export data from the current font.

All Open Fonts
Check to export data from all open fonts.

Format
Choose to export format 1 or format 2.


File Options
------------

Make New Files
Check to write new UFO or VFB files. The file name
will be same as the file being exported or imported
except that it will have a different file suffix.
If that file name already exists, a date stamp will
be added to the file name.

Write Into Existing Files
Check to write data into existing UFO or VFB files.
The file name will be exported or imported except
that it will have a different file suffix.


Data Options
------------

Font Info
Check to read/write font info data.

Kerning
Check to read/write kerning data.

Groups
Check to read/write group data.

Lib
Check to read/write font lib data.

Hints
Check to read/write hint data.

Glyphs
This button brings up a dialog that will allow
you to select which glyphs should be exported
or imported.

Glyph Marks
Check to read/write glyph marks.

Glyph Masks
Check to read/write glyph masks.
""".strip()


import os
from copy import deepcopy
from robofab.ufoLib import UFOReader, UFOWriter
from robofab.pens.pointPen import AbstractPointPen
from robofab.world import AllFonts, CurrentFont, CurrentGlyph, OpenFont, NewFont
from robofab.interface.all.dialogs import Message
from robofab.plistlib import readPlist, writePlist
from robofab.objects.objectsFL import _dictHintsToGlyph, postScriptHintDataLibKey, PostScriptFontHintValues, _glyphHintsToDict
import dialogKit
from FL import *
import fl_cmd

try:
    set
except NameError:
    from sets import Set as set


# ---------
# Interface
# ---------

class HelpDialog(object):

    def __init__(self):
        self.w = dialogKit.ModalDialog((390, 550), "UFO Central Help")
        self.w.help = dialogKit.List((12, 12, -12, -60), help.splitlines())
        self.w.open()

# quick modes
quickMode_import_selectedFiles_everything = "Import: Selected Files: Everything"
quickMode_export_allFonts_everything = "Export: All Fonts: Everything"
quickMode_export_currentFont_selectedGlyphs = "Export: Current Font: Selected Glyphs"

class MainDialog(object):

    def __init__(self):
        self.mode = "import"
        self.files = {}
        self.glyphs = None
        self.quickModes = [
            quickMode_import_selectedFiles_everything,
            quickMode_export_allFonts_everything,
            quickMode_export_currentFont_selectedGlyphs
        ]

        self.w = dialogKit.ModalDialog((570, 422), "UFO Central", okCallback=self.okCallback)

        self.w.fileList = dialogKit.List((12, 12, 200, -60), [])

        self.w.quickModeTitle = dialogKit.TextBox((220, 16, 80, 20), "Quick Mode:")
        self.w.quickModePopUp = dialogKit.PopUpButton((305, 12, -12, 27), self.quickModes, callback=self.quickModeSelectionCallback)

        self.w.line1 = dialogKit.HorizontalLine((220, 49, -12, 1))

        self.w.doImportCheckBox = dialogKit.CheckBox((220, 59, 190, 20), "Import", value=True, callback=self.doImportCallback)
        self.w.importSelectFilesButton = dialogKit.Button((240, 87, 100, 20), "Select UFOs", callback=self.importFileSelectionCallback)
        self.w.saveVFBCheckBox = dialogKit.CheckBox((240, 117, 170, 20), "Save After Importing", value=True, callback=self.saveVFBCallback)
        self.w.closeVFBCheckBox = dialogKit.CheckBox((240, 140, 170, 20), "Close After Importing", value=True)

        self.w.doExportCheckBox = dialogKit.CheckBox((220, 170, 190, 20), "Export", callback=self.doExportCallback)
        self.w.exportCurrentFontCheckBox = dialogKit.CheckBox((240, 195, 170, 20), "Current Font", value=True, callback=self.exportFileSelectionCallback)
        self.w.exportAllOpenFontsCheckBox = dialogKit.CheckBox((240, 218, 170, 20), "All Open Fonts", callback=self.exportFileSelectionCallback)
        self.w.exportFormatVersion1CheckBox = dialogKit.CheckBox((240, 246, 170, 20), "Format 1", callback=self.exportFormatSelectionCallback)
        self.w.exportFormatVersion2CheckBox = dialogKit.CheckBox((240, 269, 170, 20), "Format 2", value=True, callback=self.exportFormatSelectionCallback)
        self.w.exportCurrentFontCheckBox.enable(False)
        self.w.exportAllOpenFontsCheckBox.enable(False)
        self.w.exportFormatVersion1CheckBox.enable(False)
        self.w.exportFormatVersion2CheckBox.enable(False)

        self.w.line2 = dialogKit.HorizontalLine((220, 299, 190, 1))

        self.w.destinationNewFilesCheckBox = dialogKit.CheckBox((240, 309, 170, 20), "Make New Files", value=True, callback=self.destinationFilesCallback)
        self.w.destinationExistingFilesCheckBox = dialogKit.CheckBox((240, 332, 170, 20), "Write Into Existing Files", callback=self.destinationFilesCallback)

        self.w.line3 = dialogKit.VerticalLine((420, 59, 1, -60))

        self.w.doFontInfoCheckBox = dialogKit.CheckBox((435, 59, -12, 20), "Font Info", value=True)
        self.w.doKerningCheckBox = dialogKit.CheckBox((435, 82, -12, 20), "Kerning", value=True)
        self.w.doGroupsCheckBox = dialogKit.CheckBox((435, 105, -12, 20), "Groups", value=True)
        self.w.doLibCheckBox = dialogKit.CheckBox((435, 128, -12, 20), "Lib", value=True)
        self.w.doFeaturesCheckBox = dialogKit.CheckBox((435, 151, -12, 20), "Features", value=True)
        self.w.doGlyphsButton = dialogKit.Button((435, 182, 70, 20), "Glyphs", callback=self.editGlyphsCallback)
        self.w.doGlyphsText = dialogKit.TextBox((512, 185, -12, 20), "")
        self.w.doGlyphMarksCheckBox = dialogKit.CheckBox((435, 212, -12, 20), "Glyph Marks")
        self.w.doGlyphMasksCheckBox = dialogKit.CheckBox((435, 235, -12, 20), "Glyph Masks")
        self.w.doGlyphHintsCheckBox = dialogKit.CheckBox((435, 258, -12, 20), "Glyph Hints", value=False)

        self.w.helpButton = dialogKit.Button((12, -32, 70, 20), "Help", callback=self.showHelpCallback)

        self.w.open()

    def _modeChange(self):
        self.w.doImportCheckBox.set(self.mode == "import")
        self.w.doExportCheckBox.set(self.mode == "export")
        importControls = [
            self.w.importSelectFilesButton,
            self.w.saveVFBCheckBox,
            self.w.closeVFBCheckBox
        ]
        exportControls = [
            self.w.exportCurrentFontCheckBox,
            self.w.exportAllOpenFontsCheckBox,
            self.w.exportFormatVersion1CheckBox,
            self.w.exportFormatVersion2CheckBox,
        ]
        for control in importControls:
            control.enable(self.mode == "import")
        for control in exportControls:
            control.enable(self.mode == "export")
        if self.mode == "export":
            self._updateExportFileList()
        else:
            self.files = {}
            self.w.fileList.set([])
        self.glyphs = None
        self._updateGlyphsText()

    def _updateFileList(self):
        fileNames = [os.path.basename(p) for p in self.files.keys()]
        fileNames.sort()
        self.w.fileList.set(fileNames)

    def _updateGlyphsText(self):
        if self.glyphs is None:
            self.w.doGlyphsText.set("All")
        else:
            self.w.doGlyphsText.set("Subset")

    def destinationFilesCallback(self, sender):
        if sender == self.w.destinationNewFilesCheckBox:
            self.w.destinationExistingFilesCheckBox.set(not sender.get())
        else:
            self.w.destinationNewFilesCheckBox.set(not sender.get())

    def showHelpCallback(self, sender):
        HelpDialog()

    # ----------
    # Quick Mode
    # ----------

    def quickModeSelectionCallback(self, sender):
        mode = self.quickModes[sender.getSelection()]
        if mode == quickMode_import_selectedFiles_everything:
            # import
            self.w.doImportCheckBox.set(True)
            self.w.saveVFBCheckBox.set(True)
            self.w.closeVFBCheckBox.set(True)
            # export
            self.w.doExportCheckBox.set(False)
            self.w.exportCurrentFontCheckBox.set(False)
            self.w.exportAllOpenFontsCheckBox.set(False)
            self.w.exportFormatVersion1CheckBox.set(False)
            self.w.exportFormatVersion2CheckBox.set(False)
            # destination
            self.w.destinationNewFilesCheckBox.set(True)
            self.w.destinationExistingFilesCheckBox.set(False)
            # parts
            self.w.doFontInfoCheckBox.set(True)
            self.w.doKerningCheckBox.set(True)
            self.w.doGroupsCheckBox.set(True)
            self.w.doLibCheckBox.set(True)
            self.w.doFeaturesCheckBox.set(True)
            self.w.doGlyphsText.set("")
            self.w.doGlyphMarksCheckBox.set(False)
            self.w.doGlyphMasksCheckBox.set(False)
            self.w.doGlyphHintsCheckBox.set(False)
            glyphs = None
        elif mode == quickMode_export_allFonts_everything:
            # import
            self.w.doImportCheckBox.set(False)
            self.w.saveVFBCheckBox.set(False)
            self.w.closeVFBCheckBox.set(False)
            # export
            self.w.doExportCheckBox.set(True)
            self.w.exportCurrentFontCheckBox.set(False)
            self.w.exportAllOpenFontsCheckBox.set(True)
            self.w.exportFormatVersion1CheckBox.set(False)
            self.w.exportFormatVersion2CheckBox.set(True)
            # destination
            self.w.destinationNewFilesCheckBox.set(True)
            self.w.destinationExistingFilesCheckBox.set(False)
            # parts
            self.w.doFontInfoCheckBox.set(True)
            self.w.doKerningCheckBox.set(True)
            self.w.doGroupsCheckBox.set(True)
            self.w.doLibCheckBox.set(True)
            self.w.doFeaturesCheckBox.set(True)
            self.w.doGlyphsText.set("")
            self.w.doGlyphMarksCheckBox.set(False)
            self.w.doGlyphMasksCheckBox.set(False)
            self.w.doGlyphHintsCheckBox.set(False)
            glyphs = None
        elif mode == quickMode_export_currentFont_selectedGlyphs:
            # import
            self.w.doImportCheckBox.set(False)
            self.w.saveVFBCheckBox.set(False)
            self.w.closeVFBCheckBox.set(False)
            # export
            self.w.doExportCheckBox.set(True)
            self.w.exportCurrentFontCheckBox.set(True)
            self.w.exportAllOpenFontsCheckBox.set(False)
            self.w.exportFormatVersion1CheckBox.set(False)
            self.w.exportFormatVersion2CheckBox.set(True)
            # destination
            self.w.destinationNewFilesCheckBox.set(False)
            self.w.destinationExistingFilesCheckBox.set(True)
            # parts
            self.w.doFontInfoCheckBox.set(False)
            self.w.doKerningCheckBox.set(False)
            self.w.doGroupsCheckBox.set(False)
            self.w.doLibCheckBox.set(False)
            self.w.doFeaturesCheckBox.set(False)
            self.w.doGlyphsText.set("")
            self.w.doGlyphMarksCheckBox.set(False)
            self.w.doGlyphMasksCheckBox.set(False)
            self.w.doGlyphHintsCheckBox.set(False)
            font = CurrentFont()
            if font is None:
                glyphs = None
            elif not len(font.selection):
                glyph = CurrentGlyph()
                if glyph is None:
                    glyphs = None
                else:
                    glyphs = [glyph.name]
            else:
                glyphs = font.selection
                glyphs.sort()
        else:
            return
        # update enabled states
        if self.w.doImportCheckBox.get():
            self.mode = "import"
        else:
            self.mode = "export"
        self._modeChange()
        # update glyph list
        self.glyphs = glyphs
        self._updateGlyphsText()

    # ------
    # Import
    # ------

    def doImportCallback(self, sender):
        if sender.get():
            self.mode = "import"
        else:
            self.mode = "export"
        self._modeChange()

    def importFileSelectionCallback(self, sender):
        import glob
        from robofab.interface.all.dialogs import GetFileOrFolder

        path = GetFileOrFolder()
        if path is not None:
            if os.path.isdir(path):
                if os.path.splitext(path)[-1] == ".ufo" and self.mode == "import":
                    self.files[path] = None
                else:
                    for fileName in glob.glob(os.path.join(path, "*.ufo")):
                        self.files[fileName] = None
            else:
                ext = os.path.splitext(path)[-1]
                if ext == ".ufo":
                    self.files[path] = None
            self._updateFileList()

    def saveVFBCallback(self, sender):
        self.w.closeVFBCheckBox.enable(sender.get())

    # ------
    # Export
    # ------

    def doExportCallback(self, sender):
        if sender.get():
            self.mode = "export"
        else:
            self.mode = "import"
        self._modeChange()

    def exportFileSelectionCallback(self, sender):
        if sender == self.w.exportCurrentFontCheckBox:
            self.w.exportAllOpenFontsCheckBox.set(not sender.get())
        else:
            self.w.exportCurrentFontCheckBox.set(not sender.get())
        self._updateExportFileList()

    def _updateExportFileList(self):
        if self.w.exportCurrentFontCheckBox.get():
            font = CurrentFont()
            if font is None:
                self.files = {}
            else:
                self.files = {
                    font.path : font
                }
        else:
            self.files = {}
            for font in AllFonts():
                self.files[font.path] = font
        self._updateFileList()

    def exportFormatSelectionCallback(self, sender):
        if sender == self.w.exportFormatVersion1CheckBox:
            self.w.exportFormatVersion2CheckBox.set(not sender.get())
        else:
            self.w.exportFormatVersion1CheckBox.set(not sender.get())

    def exportDestinationFilesCallback(self, sender):
        if sender == self.w.exportNewFilesCheckBox:
            self.w.exportExistingFilesCheckBox.set(not sender.get())
        else:
            self.w.exportNewFilesCheckBox.set(not sender.get())

    # --------------
    # Data Selection
    # --------------

    def editGlyphsCallback(self, sender):
        GlyphsDialog(self.files, self.glyphs, self.mode, self._editGlyphsFinishedCallback)

    def _editGlyphsFinishedCallback(self, selectedGlyphs, unselectedGlyphs):
        if not len(unselectedGlyphs):
            self.glyphs = None
        else:
            self.glyphs = selectedGlyphs
        self._updateGlyphsText()

    # ----------
    # Processing
    # ----------

    def okCallback(self, sender):
        doInfo = self.w.doFontInfoCheckBox.get()
        doKerning = self.w.doKerningCheckBox.get()
        doGroups = self.w.doGroupsCheckBox.get()
        doLib = self.w.doLibCheckBox.get()
        doFeatures = self.w.doFeaturesCheckBox.get()
        doGlyphHints = self.w.doGlyphHintsCheckBox.get()
        doGlyphMarks = self.w.doGlyphMarksCheckBox.get()
        doGlyphMasks = self.w.doGlyphMasksCheckBox.get()
        formatVersion = 2
        if self.w.exportFormatVersion1CheckBox.get():
            formatVersion = 1

        newFile = self.w.destinationNewFilesCheckBox.get()

        if self.mode == "export":
            for path, font in self.files.items():
                exportUFO(font, newFile, doInfo=doInfo, doKerning=doKerning, doGroups=doGroups, doLib=doLib, doFeatures=doFeatures,
                    doHints=doGlyphHints, doMarks=doGlyphMarks, doMasks=doGlyphMasks, glyphs=self.glyphs, formatVersion=formatVersion)
        else:
            saveFile = self.w.saveVFBCheckBox.get()
            closeFile = self.w.closeVFBCheckBox.get()
            for path in self.files.keys():
                importUFO(path, newFile, saveFile, closeFile, doInfo=doInfo, doKerning=doKerning, doGroups=doGroups, doLib=doLib, doFeatures=doFeatures,
                    doHints=doGlyphHints, doMarks=doGlyphMarks, doMasks=doGlyphMasks, glyphs=self.glyphs)


class GlyphsDialog(object):

    def __init__(self, fonts, glyphs, mode, callback):
        self.allGlyphs = set()
        for path, font in fonts.items():
            if font is None:
                contentsPath = os.path.join(path, "glyphs", "contents.plist")
                if not os.path.exists(contentsPath):
                    continue
                else:
                    contents = readPlist(contentsPath)
                    self.allGlyphs = self.allGlyphs | set(contents.keys())
            else:
                self.allGlyphs = self.allGlyphs | set(font.keys())
        if glyphs is None:
            self.selectedGlyphs = list(self.allGlyphs)
            self.selectedGlyphs.sort()
            self.unselectedGlyphs = []
        else:
            self.selectedGlyphs = glyphs
            self.unselectedGlyphs = list(self.allGlyphs - set(glyphs))
            self.unselectedGlyphs.sort()

        self.callback = callback
        mode = mode.title()

        self.w = dialogKit.ModalDialog((472, 400), "Glyphs", okCallback=self.okCallback)

        self.w.unselectedTitle = dialogKit.TextBox((12, 12, 150, 20), "Ignore:")
        self.w.unselectedGlyphsList = dialogKit.List((12, 37, 150, -60), self.unselectedGlyphs)

        self.w.addSelectionButton = dialogKit.Button((172, 37, 130, 20), ">>>", callback=self.addSelectionCallback)
        self.w.removeSelectionButton = dialogKit.Button((172, 67, 130, 20), "<<<", callback=self.removeSelectionCallback)
        self.w.addAllButton = dialogKit.Button((172, 97, 130, 20), "%s All" % mode, callback=self.addAllCallback)
        self.w.removeAllButton = dialogKit.Button((172, 127, 130, 20), "Ignore All", callback=self.removeAllCallback)
        self.w.fromFontSelection = dialogKit.Button((172, 157, 130, 20), "Font Selection", callback=self.fontSelectionCallback)

        self.w.selectedTitle = dialogKit.TextBox((310, 12, 150, 20), "%s:" % mode)
        self.w.selectedGlyphsList = dialogKit.List((310, 37, 150, -60), self.selectedGlyphs)

        self.w.open()

    def _updateLists(self):
        self.w.unselectedGlyphsList.set(self.unselectedGlyphs)
        self.w.selectedGlyphsList.set(self.selectedGlyphs)

    def addSelectionCallback(self, sender):
        s = self.w.unselectedGlyphsList.getSelection()
        if not s:
            return
        s = self.unselectedGlyphs[s[0]]
        self.selectedGlyphs.append(s)
        self.selectedGlyphs.sort()
        self.unselectedGlyphs.remove(s)
        self._updateLists()

    def removeSelectionCallback(self, sender):
        s = self.w.selectedGlyphsList.getSelection()
        if not s:
            return
        s = self.selectedGlyphs[s[0]]
        self.unselectedGlyphs.append(s)
        self.unselectedGlyphs.sort()
        self.selectedGlyphs.remove(s)
        self._updateLists()

    def addAllCallback(self, sender):
        self.selectedGlyphs = list(self.allGlyphs)
        self.selectedGlyphs.sort()
        self.unselectedGlyphs = []
        self._updateLists()

    def removeAllCallback(self, sender):
        self.unselectedGlyphs = list(self.allGlyphs)
        self.unselectedGlyphs.sort()
        self.selectedGlyphs = []
        self._updateLists()

    def fontSelectionCallback(self, sender):
        font = CurrentFont()
        if font is None:
            return
        self.selectedGlyphs = list(font.selection)
        self.unselectedGlyphs = list(set(self.allGlyphs) - set(self.selectedGlyphs))
        self.unselectedGlyphs.sort()
        self._updateLists()

    def okCallback(self, sender):
        self.callback(list(self.selectedGlyphs), list(self.unselectedGlyphs))


# -------
# Support
# -------

class InstructionPointPen(AbstractPointPen):

    def __init__(self):
        self._instructions = []

    def beginPath(self):
        d = {
            "method":"beginPath"
            }
        self._instructions.append(d)

    def endPath(self):
        d = {
            "method":"endPath"
            }
        self._instructions.append(d)

    def addPoint(self, pt, segmentType=None, smooth=False, name=None, **kwargs):
        d = {
            "method":"addPoint",
            "pt":pt,
            }
        if segmentType is not None:
            d["segmentType"] = segmentType
        if smooth is not None:
            d["smooth"] = smooth
        if name is not None:
            d["name"] = name
        self._instructions.append(d)

    def addComponent(self, baseGlyphName, transformation):
        d = {
            "method":"addComponent",
            "baseGlyphName":baseGlyphName,
            "transformation":transformation
            }

    def getInstructions(self):
        # filter out any single point contours (anchors)
        instructions = []
        pointStack = []
        for instruction in self._instructions:
            pointStack.append(instruction)
            if instruction["method"] == "endPath":
                if pointStack:
                    if len(pointStack) > 3:
                        instructions.extend(pointStack)
                    pointStack = []
        return instructions


def _drawPointStack(stack, pointPen):
    for instruction in stack:
        meth = instruction["method"]
        if meth == "beginPath":
            pointPen.beginPath()
        elif meth == "endPath":
            pointPen.endPath()
        elif meth == "addPoint":
            pt = instruction["pt"]
            smooth = instruction.get("smooth")
            segmentType = instruction.get("segmentType")
            name = instruction.get("name")
            pointPen.addPoint(pt, segmentType, smooth, name)
        elif meth == "addComponent":
            baseGlyphName = instruction["baseGlyphName"]
            transformation = instruction["transformation"]
            pointPen.addComponent(baseGlyphName, transformation)
        else:
            raise NotImplementedError, meth

def instructionsDrawPoints(instructions, pointPen):
    """draw instructions created by InstructionPointPen"""
    # filter out single point contours (anchors)
    pointStack = []
    for instruction in instructions:
        pointStack.append(instruction)
        meth = instruction["method"]
        if meth == "endPath":
            if len(pointStack) > 3:
                _drawPointStack(pointStack, pointPen)
            pointStack = []

MASK_LIB_KEY = "org.robofab.fontlab.maskData"
MARK_LIB_KEY = "org.robofab.fontlab.mark"
FEATURES_LIB_KEY = "org.robofab.opentype.features"
FEATURES_ORDER_LIB_KEY = "org.robofab.opentype.featureorder"
FEATURES_CLASSES_KEY = "org.robofab.opentype.classes"
GLYPH_ORDER_LIB_KEY = "org.robofab.glyphOrder"
WWS_FAMILY_KEY = "com.typesupply.ufocentral.openTypeNameWWSFamilyName"
WWS_SUBFAMILY_KEY = "com.typesupply.ufocentral.openTypeNameWWSSubfamilyName"

def _normalizeLineEndings(s):
    return s.replace("\r\n", "\n").replace("\r", "\n")

def _findAvailablePathName(path):
    import time
    folder = os.path.dirname(path)
    fileName = os.path.basename(path)
    fileName, extension = os.path.splitext(fileName)
    stamp = time.strftime("%Y-%m-%d %H-%M-%S %Z")
    newFileName = "%s (%s)%s" % (fileName, stamp, extension)
    newPath = os.path.join(folder, newFileName)
    # intentionally break to prevent a file overwrite
    # this could happen if the user has a director full
    # of files with future time stamped file names.
    # not likely, but avoid it all the same.
    assert not os.path.exists(newPath)
    return newPath

# ---------------
# Import & Export
# ---------------

def exportUFO(font, newFile=True, doInfo=True, doKerning=True, doGroups=True, doLib=True, doFeatures=True,
    doHints=False, doMarks=True, doMasks=True, glyphs=None, formatVersion=2):
    # get the UFO path
    ufoPath = os.path.splitext(font.path)[0] + ".ufo"
    if not newFile:
        if not os.path.exists(ufoPath):
            Message("Could not find the UFO file \"%s\"." % os.path.basename(ufoPath))
            return
    else:
        if os.path.exists(ufoPath):
            ufoPath = _findAvailablePathName(ufoPath)
    # make sure no bogus glyph names are coming in
    if glyphs is not None:
        glyphs = [glyphName for glyphName in glyphs if font.has_key(glyphName)]
    # make the font the top font in FL
    fl.ifont = font.fontIndex
    # add the masks and marks to the glyph.lib
    if doMasks or doMarks:
        if glyphs is None:
            glyphNames = font.keys()
        else:
            glyphNames = glyphs
        for glyphName in glyphNames:
            glyph = font[glyphName]
            if doMarks:
                mark = glyph.mark
                glyph.lib[MARK_LIB_KEY] = mark
            if doMasks:
                # open a glyph window
                fl.EditGlyph(glyph.index)
                # switch to the mask layer
                fl.CallCommand(fl_cmd.ViewEditMask)
                # if the mask is empty, skip this step
                if not len(glyph):
                    # switch back to the edit layer
                    fl.CallCommand(fl_cmd.ViewEditMask)
                    continue
                # get the mask data
                pen = InstructionPointPen()
                glyph.drawPoints(pen)
                # switch back to the edit layer
                fl.CallCommand(fl_cmd.ViewEditMask)
                # write the mask data to the glyph lib
                instructions = pen.getInstructions()
                if instructions:
                    glyph.lib[MASK_LIB_KEY] = instructions
        # close all glyph windows. sometimes this actually works.
        fl.CallCommand(fl_cmd.WindowCloseAllGlyphWindows)
    # remove WWS names from the lib
    wwsStorage = {}
    if "openTypeNameWWSFamilyName" in font.lib:
        wwsStorage["openTypeNameWWSFamilyName"] = font.lib.pop(WWS_FAMILY_KEY)
    if "openTypeNameWWSSubfamilyName" in font.lib:
        wwsStorage["openTypeNameWWSSubfamilyName"] = font.lib.pop(WWS_SUBFAMILY_KEY)
    # write the UFO
    font.writeUFO(path=ufoPath, doHints=doHints, doInfo=doInfo,
        doKerning=doKerning, doGroups=doGroups, doLib=doLib, doFeatures=doFeatures, glyphs=glyphs,
        formatVersion=formatVersion)
    # add the WWS names to the info
    if doInfo:
        infoPath = os.path.join(ufoPath, "fontinfo.plist")
        info = readPlist(infoPath)
        newInfo = deepcopy(info)
        newInfo.update(wwsStorage)
        if info != newInfo:
            writePlist(newInfo, infoPath)
    # put the WWS names back in the lib
    font.lib.update(wwsStorage)
    # remove the masks and marks from the glyph.lib
    if doMasks or doMarks:
        if glyphs is None:
            glyphNames = font.keys()
        else:
            glyphNames = glyphs
        for glyphName in glyphNames:
            glyph = font[glyphName]
            lib = glyph.lib
            if lib.has_key(MASK_LIB_KEY):
                del lib[MASK_LIB_KEY]
            if lib.has_key(MARK_LIB_KEY):
                del lib[MARK_LIB_KEY]

def importUFO(ufoPath, newFile=True, saveFile=True, closeFile=True, doInfo=True, doKerning=True, doGroups=True,
    doLib=True, doFeatures=True, doHints=False, doMarks=True, doMasks=True, glyphs=None):
    # get the VFB path
    vfbPath = os.path.splitext(ufoPath)[0] + ".vfb"
    if not newFile:
        font = None
        for font in AllFonts():
            if font.path == vfbPath:
                break
        if font is None:
            if not os.path.exists(vfbPath):
                Message("Could not find the FontLab file \"%s\"." % os.path.basename(vfbPath))
                return
            font = OpenFont(vfbPath)
    else:
        if saveFile:
            if os.path.exists(vfbPath):
                vfbPath = _findAvailablePathName(vfbPath)
        font = NewFont()
    # make the font the top font in FL
    fl.ifont = font.fontIndex
    # read the UFO
    font.readUFO(ufoPath, doHints=doHints, doInfo=doInfo, doKerning=doKerning,
        doGroups=doGroups, doLib=doLib, doFeatures=doFeatures, glyphs=glyphs)
    # load the masks and marks
    if doMasks or doMarks:
        for glyph in font:
            lib = glyph.lib
            if doMarks:
                if lib.has_key(MARK_LIB_KEY):
                    glyph.mark = lib[MARK_LIB_KEY]
                    del lib[MARK_LIB_KEY]
            if doMasks:
                if lib.has_key(MASK_LIB_KEY):
                    # open a glyph window
                    fl.EditGlyph(glyph.index)
                    # switch to the mask layer
                    fl.CallCommand(fl_cmd.ViewEditMask)
                    # add the mask data
                    instructions = lib[MASK_LIB_KEY]
                    pen = glyph.getPointPen()
                    instructionsDrawPoints(instructions, pen)
                    # switch back to the edit layer
                    fl.CallCommand(fl_cmd.ViewEditMask)
                    # clear the mask data from the glyph lib
                    del lib[MASK_LIB_KEY]
        # close all glyph windows. sometimes this actually works.
        fl.CallCommand(fl_cmd.WindowCloseAllGlyphWindows)
    # load the WWS names
    if doInfo:
        info = readPlist(os.path.join(ufoPath, "fontInfo.plist"))
        if "openTypeNameWWSFamilyName" in info:
            font.lib[WWS_FAMILY_KEY] = info["openTypeNameWWSFamilyName"]
        elif "openTypeNameWWSFamilyName" in font.lib:
            del font.lib[WWS_FAMILY_KEY]
        if "openTypeNameWWSSubfamilyName" in info:
            font.lib[WWS_SUBFAMILY_KEY] = info["openTypeNameWWSSubfamilyName"]
        elif "openTypeNameWWSSubfamilyName" in font.lib:
            del font.lib[WWS_SUBFAMILY_KEY]
    # update the font
    font.update()
    # save and close
    if saveFile:
        font.save(vfbPath)
        if closeFile:
            font.close()


if __name__ == "__main__":
    MainDialog()
