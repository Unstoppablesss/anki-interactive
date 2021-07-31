"""
Assembling addon
"""
from os import mkdir
import shutil
import zipfile
import re

import anki

import config
import models_def
import notes_def


class Sources(dict):
    """
    Caching dictionary of all sources in SRCPATH
    """
    def __getitem__(self, name):
        if name not in self:
            with open(config.SRCDIR / name) as f:
                self[name] = f.read()
        return super().__getitem__(name)

    def compile_html(self, html):
        html = re.sub('{{> (.*)}}', lambda m: self[m.group(1)+".html"], html)
        html = re.sub('<script src="(.*)"></script>', lambda m: "<script>" + self[m.group(1)] + "</script>\n", html)
        return html

    def compile_css(self, csslist):
        return "\n".join(map(lambda f: self[f], csslist))


sources = Sources()


def create_models(coll):
    for name, conf in models_def.MODELS.items():
        create_model(coll, name, conf)


def create_model(coll, name, conf):
    model = coll.models.new(name)
    model['type'] = conf['type']

    for fld in conf['fields']:
        f = coll.models.newField(fld)
        if fld in models_def.COMMON_FIELDS:
            f['sticky'] = True
        coll.models.addField(model, f)
    model['sortf'] = 0
    model['latexPre'] = ""
    model['latexPost'] = ""
    model['css'] = sources.compile_css(conf['css'])
    tmpl = coll.models.newTemplate(name)
    tmpl['qfmt'] = sources.compile_html(sources[conf['html'][0]])
    tmpl['afmt'] = sources.compile_html(sources[conf['html'][1]])
    coll.models.addTemplate(model, tmpl)
    coll.models.add(model)


def create_notes(coll):
    for conf in notes_def.NOTES:
        create_note(coll, conf)


def create_note(coll, conf):
    model = coll.models.byName(conf['model'])
    note = anki.notes.Note(coll, model)
    note.guid = conf['guid']
    for fld, val in conf['fields'].items():
        note[fld] = val
    coll.addNote(note)


# def make_zip():
#     addon = zipfile.ZipFile(config.ADDONFILE, "w")
#     for entry in config.ADDONDIR:
#         if entry.name in ('__pycache__', 'meta.json'):
#             continue
#         addon.write(entry.path, entry.name)
#     addon.close()


if __name__ == "__main__":
    print("Rebuilding...")
    if not config.BUILDDIR.exists():
        config.BUILDDIR.mkdir()

    if not config.DISTDIR.exists():
        config.DECKFILE.mkdir()


    # creating new collection file
    print(f"Saving to {config.DECKFILE}...")

    config.DECKFILE.unlink(missing_ok=True)
    coll = anki.Collection(config.DECKFILE, server=False, log=False)
    coll.decks.add_config("Interactive Demo")

    create_models(coll)
    print(f"Added {len(coll.models.all())} models")

    create_notes(coll)
    print(f"Added {coll.noteCount()} notes")

    # remove all default models
    for m in coll.models.all():
        if m['name'] not in models_def.MODELS:
            coll.models.remove(m['id'])

    coll.close()

    apkg = zipfile.ZipFile(config.APKGFILE, "w")
    apkg.write(config.DECKFILE, "collection.anki2")
    apkg.writestr('media', "{}")
    apkg.close()

    print(f"Created apkg in {config.APKGFILE}")