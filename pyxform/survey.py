import codecs
import os
import re
import tempfile
import xml.etree.ElementTree as ETree
from collections import defaultdict
from datetime import datetime

from pyxform import constants
from pyxform.errors import PyXFormError
from pyxform.errors import ValidationError
from pyxform.external_instance import ExternalInstance
from pyxform.instance import SurveyInstance
from pyxform.instance_info import InstanceInfo
from pyxform.question import Question
from pyxform.section import Section
from pyxform.survey_element import SurveyElement
from pyxform.utils import PatchedText, basestring, node, unicode, NSMAP, get_languages_with_bad_tags
from pyxform.validators import odk_validate
from pyxform.validators import enketo_validate


def register_nsmap():
    for prefix, uri in NSMAP.items():
        prefix_no_xmlns = prefix.replace("xmlns", "").replace(":", "")
        ETree.register_namespace(prefix_no_xmlns, uri)


register_nsmap()


class Survey(Section):

    FIELDS = Section.FIELDS.copy()
    FIELDS.update(
        {
            u"_xpath": dict,
            u"_created": datetime.now,  # This can't be dumped to json
            u"title": unicode,
            u"id_string": unicode,
            u"sms_keyword": unicode,
            u"sms_separator": unicode,
            u"sms_allow_media": bool,
            u"sms_date_format": unicode,
            u"sms_datetime_format": unicode,
            u"sms_response": unicode,

            constants.COMPACT_PREFIX: unicode,
            constants.COMPACT_DELIMITER: unicode,

            u"file_name": unicode,
            u"default_language": unicode,
            u"_translations": dict,
            u"submission_url": unicode,
            u"auto_send": unicode,
            u"auto_delete": unicode,
            u"public_key": unicode,
            u"instance_xmlns": unicode,
            u"version": unicode,
            u"choices": dict,
            u"style": unicode,
            u"attribute": dict,
            u"namespaces": unicode,
        }
    )

    def validate(self):
        if self.id_string in [None, 'None']:
            raise PyXFormError('Survey cannot have an empty id_string')
        super(Survey, self).validate()
        self._validate_uniqueness_of_section_names()

    def _validate_uniqueness_of_section_names(self):
        section_names = []
        for e in self.iter_descendants():
            if isinstance(e, Section):
                if e.name in section_names:
                    raise PyXFormError(
                        "There are two sections with the name %s." % e.name)
                section_names.append(e.name)

    def get_nsmap(self):
        """Add additional namespaces"""
        namespaces = getattr(self, constants.NAMESPACES, None)

        if namespaces and isinstance(namespaces, basestring):
            nslist = [
                ns.split('=') for ns in namespaces.split()
                if len(ns.split('=')) == 2 and ns.split('=')[0] != ''
            ]
            xmlns = u'xmlns:'
            nsmap = NSMAP.copy()
            nsmap.update(dict([
                (xmlns + k, v.replace('"', '').replace("'", ""))
                for k, v in nslist if xmlns + k not in nsmap
            ]))
            return nsmap
        else:
            return NSMAP

    def xml(self):
        """
        calls necessary preparation methods, then returns the xml.
        """
        self.validate()
        self._setup_xpath_dictionary()
        body_kwargs = {}
        if hasattr(self, constants.STYLE) and getattr(
                self, constants.STYLE):
            body_kwargs['class'] = getattr(
                self, constants.STYLE)
        nsmap = self.get_nsmap()

        return node(u"h:html",
                    node(u"h:head",
                         node(u"h:title", self.title),
                         self.xml_model()
                         ),
                    node(u"h:body", *self.xml_control(), **body_kwargs),
                    **nsmap
                    )

    @staticmethod
    def _generate_static_instances(list_name, choice_list):
        """
        Generates <instance> elements for static data
        (e.g. choices for select type questions)

        Note that per commit message 0578242 and in xls2json.py R539, an
        instance is only output for select items defined in the choices sheet
        when the item has a choice_filter, and it is that way for backwards
        compatibility.
        """
        instance_element_list = []
        for idx, choice in enumerate(choice_list):
            choice_element_list = []
            # Add a unique id to the choice element in case there is itext
            # it references
            itext_id = '-'.join(['static_instance', list_name, str(idx)])
            choice_element_list.append(node("itextId", itext_id))

            for choicePropertyName, choicePropertyValue in choice.items():
                if isinstance(choicePropertyValue, basestring) \
                        and choicePropertyName != 'label':
                    choice_element_list.append(
                        node(choicePropertyName,
                             unicode(choicePropertyValue))
                    )
            instance_element_list.append(node("item", *choice_element_list))
        return InstanceInfo(
            type=u"choice",
            context=u"survey",
            name=list_name,
            src=None,
            instance=node(
                "instance",
                node("root", *instance_element_list),
                id=list_name
            )
        )

    @staticmethod
    def _get_dummy_instance():
        """Instance content required by ODK Validate for select inputs."""
        return node("root", node("item", node("name", "_"), node("label", "_")))

    @staticmethod
    def _generate_external_instances(element):
        if isinstance(element, ExternalInstance):
            name = element[u"name"]
            src = "jr://file/{}.xml".format(name)
            return InstanceInfo(
                type=u"external",
                context="[type: {t}, name: {n}]".format(
                    t=element[u"parent"][u"type"],
                    n=element[u"parent"][u"name"]
                ),
                name=name,
                src=src,
                instance=node(
                    "instance",
                    Survey._get_dummy_instance(),
                    id=name,
                    src=src
                )
            )

    @staticmethod
    def _validate_external_instances(instances):
        """
        Must have unique names.

        - Duplications could come from across groups; this checks the form.
        - Errors are pooled together into a (hopefully) helpful message.
        """
        seen = {}
        for i in instances:
            element = i.name
            if seen.get(element) is None:
                seen[element] = [i]
            else:
                seen[element].append(i)
        errors = []
        for element, copies in seen.items():
            if 1 < len(copies):
                contexts = ", ".join(x.context for x in copies)
                errors.append(
                    "Instance names must be unique within a form. "
                    "The name '{i}' was found {c} time(s), "
                    "under these contexts: {contexts}".format(
                        i=element, c=len(copies), contexts=contexts))
        if 0 < len(errors):
            raise ValidationError("\n".join(errors))

    @staticmethod
    def _generate_pulldata_instances(element):
        if 'calculate' in element['bind']:
            calculate = element['bind']['calculate']
            if calculate.startswith('pulldata('):
                pieces = calculate.split('"') \
                    if '"' in calculate else calculate.split("'")
                if len(pieces) > 1 and pieces[1]:
                    file_id = pieces[1]
                    uri = "jr://file-csv/{}.csv".format(file_id)
                    return InstanceInfo(
                        type=u"pulldata",
                        context="[type: {t}, name: {n}]".format(
                            t=element[u"parent"][u"type"],
                            n=element[u"parent"][u"name"]
                        ),
                        name=file_id,
                        src=uri,
                        instance=node(
                            "instance",
                            Survey._get_dummy_instance(),
                            id=file_id,
                            src=uri
                        )
                    )

    @staticmethod
    def _generate_from_file_instances(element):
        itemset = element.get('itemset')
        if itemset and (itemset.endswith('.csv') or itemset.endswith('.xml')):
            file_id, ext = os.path.splitext(itemset)
            uri = 'jr://%s/%s' % (
                'file' if ext == '.xml' else "file-%s" % ext[1:], itemset)
            return InstanceInfo(
                type=u"file",
                context="[type: {t}, name: {n}]".format(
                    t=element[u"parent"][u"type"],
                    n=element[u"parent"][u"name"]
                ),
                name=file_id,
                src=uri,
                instance=node(
                    "instance",
                    Survey._get_dummy_instance(),
                    id=file_id,
                    src=uri
                )
            )

    def _generate_instances(self):
        """
        Get instances from all the different ways that they may be generated.

        An opportunity to validate instances before output to the XML model.

        Instance names used for the id attribute are generated as follows:

        - xml-external: item name value (for type==xml-external)
        - pulldata: first arg to calculation->pulldata()
        - select from file: file name arg to type->itemset
        - choices: list_name (for type==select_*)

        Validation and business rules for output of instances:

        - xml-external item name must be unique across the XForm and the form is
          considered invalid if there is a duplicate name. This differs from
          other item types which allow duplicates if not in the same group.
        - for all instance sources, if the same instance name is encountered,
          the following rules are used to allow re-using instances but prevent
          overwriting conflicting instances:
          - same id, same src URI: skip adding the second (duplicate) instance
          - same id, different src URI: raise an error
          - otherwise: output the instance

        There are two other things currently supported by pyxform that involve
        external files and are not explicitly handled here, but may be relevant
        to future efforts to harmonise / simplify external data workflows:

        - `search` appearance/function: works a lot like pulldata but the csv
          isn't made explicit in the form.
        - `select_one_external`: implicitly relies on a `itemsets.csv` file and
          uses XPath-like expressions for querying.
        """
        instances = []
        for i in self.iter_descendants():
            i_ext = self._generate_external_instances(element=i)
            i_pull = self._generate_pulldata_instances(element=i)
            i_file = self._generate_from_file_instances(element=i)
            instances += [x for x in [i_ext, i_pull, i_file] if x is not None]

        # Append last so the choice instance is excluded on a name clash.
        for k, v in self.choices.items():
            instances += [
                self._generate_static_instances(list_name=k, choice_list=v)]

        # Check that external instances have unique names.
        if 0 < len(instances):
            ext_only = [x for x in instances if x.type == "external"]
            self._validate_external_instances(instances=ext_only)

        seen = {}
        for i in instances:
            if i.name in seen.keys() and seen[i.name].src != i.src:
                # Instance id exists with different src URI -> error.
                msg = "The same instance id will be generated for different " \
                      "external instance source URIs. Please check the form. " \
                      "Instance name: '{i}', Existing type: '{e}', " \
                      "Existing URI: '{iu}', Duplicate type: '{d}', " \
                      "Duplicate URI: '{du}', Duplicate context: '{c}'.".format(
                          i=i.name, iu=seen[i.name].src, e=seen[i.name].type,
                          d=i.type, du=i.src, c=i.context
                      )
                raise PyXFormError(msg)
            elif i.name in seen.keys() and seen[i.name].src == i.src:
                # Instance id exists with same src URI -> ok, don't duplicate.
                continue
            else:
                # Instance doesn't exist yet -> add it.
                yield i.instance
            seen[i.name] = i

    def xml_model(self):
        """
        Generate the xform <model> element
        """
        self._setup_translations()
        self._setup_media()
        self._add_empty_translations()

        model_children = []
        if self._translations:
            model_children.append(self.itext())
        model_children += [node("instance", self.xml_instance())]
        model_children += list(self._generate_instances())
        model_children += self.xml_bindings()

        if self.submission_url or self.public_key or self.auto_send or self.auto_delete:
            submission_attrs = dict()
            if self.submission_url:
                submission_attrs["action"] = self.submission_url
            if self.public_key:
                submission_attrs["base64RsaPublicKey"] = self.public_key
            if self.auto_send:
                submission_attrs["orx:auto-send"] = self.auto_send
            if self.auto_delete:
                submission_attrs["orx:auto-delete"] = self.auto_delete
            submission_node = node("submission", method="form-data-post",
                                   **submission_attrs)
            model_children.insert(0, submission_node)

        return node("model",  *model_children)

    def xml_instance(self):
        result = Section.xml_instance(self)

        # set these first to prevent overwriting id and version
        for key, value in self.attribute.items():
            result.setAttribute(unicode(key), value)

        result.setAttribute(u"id", self.id_string)

        # add instance xmlns attribute to the instance node
        if self.instance_xmlns:
            result.setAttribute(u"xmlns", self.instance_xmlns)

        if self.version:
            result.setAttribute(u"version", self.version)

        if self.prefix:
            result.setAttribute(u"odk:prefix", self.prefix)

        if self.delimiter:
            result.setAttribute(u"odk:delimiter", self.delimiter)

        return result

    def _add_to_nested_dict(self, dicty, path, value):
        if len(path) == 1:
            dicty[path[0]] = value
            return
        if path[0] not in dicty:
            dicty[path[0]] = {}
        self._add_to_nested_dict(dicty[path[0]], path[1:], value)

    def _setup_translations(self):
        """
        set up the self._translations dict which will be referenced in the
        setup media and itext functions
        """
        self._translations = defaultdict(dict)
        for element in self.iter_descendants():
            for d in element.get_translations(self.default_language):
                if 'guidance_hint' in d['path']:
                    hint_path = d['path'].replace('guidance_hint', 'hint')
                    self._translations[d['lang']][hint_path] = self._translations[d['lang']].get(hint_path, {})
                    self._translations[d['lang']][hint_path].update({"guidance": d['text']})
                else:
                    self._translations[d['lang']][d['path']] = self._translations[d['lang']].get(d['path'], {})
                    self._translations[d['lang']][d['path']].update({"long": d['text']})

        # This code sets up translations for choices in filtered selects.
        for list_name, choice_list in self.choices.items():
            for idx, choice in zip(range(len(choice_list)), choice_list):
                for choicePropertyName, choicePropertyValue in choice.items():
                    itext_id = '-'.join(
                        ['static_instance', list_name, str(idx)])
                    if isinstance(choicePropertyValue, dict):
                        for mediatypeorlanguage, value in choicePropertyValue.items():  # noqa
                            if isinstance(value, dict):
                                for language, val in value.items():
                                    self._add_to_nested_dict(
                                        self._translations,
                                        [language, itext_id,
                                         mediatypeorlanguage],
                                        val)
                            else:
                                if choicePropertyName == 'media':
                                    self._add_to_nested_dict(
                                        self._translations,
                                        [self.default_language, itext_id,
                                         mediatypeorlanguage],
                                        value)
                                else:
                                    self._add_to_nested_dict(
                                        self._translations,
                                        [mediatypeorlanguage, itext_id,
                                         'long'], value)
                    elif choicePropertyName == 'label':
                        self._add_to_nested_dict(
                            self._translations,
                            [self.default_language, itext_id, 'long'],
                            choicePropertyValue)

    def _add_empty_translations(self):
        """
        Adds translations so that every itext element has the same elements \
        accross every language.
        When translations are not provided "-" will be used.
        This disables any of the default_language fallback functionality.
        """
        paths = {}
        for lang, translation in self._translations.items():
            for path, content in translation.items():
                paths[path] = paths.get(path, set()).union(content.keys())

        for lang, translation in self._translations.items():
            for path, content_types in paths.items():
                if path not in self._translations[lang]:
                    self._translations[lang][path] = {}
                for content_type in content_types:
                    if content_type not in self._translations[lang][path]:
                        self._translations[lang][path][content_type] = u"-"

    def _setup_media(self):
        """
        Traverse the survey, find all the media, and put in into the \
        _translations data structure which looks like this:
        {language : {element_xpath : {media_type : media}}}
        It matches the xform nesting order.
        """
        if not self._translations:
            self._translations = defaultdict(dict)

        for survey_element in self.iter_descendants():

            translation_key = survey_element.get_xpath() + ":label"
            media_dict = survey_element.get(u"media")

            # This is probably papering over a real problem, but anyway,
            # in py3, sometimes if an item is on an xform with multiple
            # languages and the item only has media defined in # "default"
            # (e.g. no "image" vs. "image::lang"), the media dict will be
            # nested inside of a dict with key "default", e.g.
            # {"default": {"image": "my_image.jpg"}}
            media_dict_default = media_dict.get("default", None)
            if isinstance(media_dict_default, dict):
                media_dict = media_dict_default

            for media_type, possibly_localized_media in media_dict.items():

                if media_type not in SurveyElement.SUPPORTED_MEDIA:
                    raise PyXFormError(
                        "Media type: " + media_type + " not supported")

                if type(possibly_localized_media) is dict:
                    # media is localized
                    localized_media = possibly_localized_media
                else:
                    # media is not localized so create a localized version
                    # using the default language
                    localized_media = {
                        self.default_language: possibly_localized_media
                    }

                for language, media in localized_media.items():

                    # Create the required dictionaries in _translations,
                    # then add media as a leaf value:

                    if language not in self._translations:
                        self._translations[language] = {}

                    translations_language = self._translations[language]

                    if translation_key not in translations_language:
                        translations_language[translation_key] = {}

                    translations_trans_key = \
                        translations_language[translation_key]

                    if media_type not in translations_trans_key:
                            translations_trans_key[media_type] = {}

                    translations_trans_key[media_type] = media

    def itext(self):
        """
        This function creates the survey's itext nodes from _translations
        @see _setup_media _setup_translations
        itext nodes are localized images/audio/video/text
        @see http://code.google.com/p/opendatakit/wiki/XFormDesignGuidelines
        """
        result = []
        for lang, translation in self._translations.items():
            if lang == self.default_language:
                result.append(
                    node("translation", lang=lang, default=u"true()"))
            else:
                result.append(node("translation", lang=lang))

            for label_name, content in translation.items():
                itext_nodes = []
                label_type = label_name.partition(":")[-1]

                if type(content) is not dict:
                    raise Exception()

                for media_type, media_value in content.items():
                    # There is a odk/jr bug where hints can't have a value
                    # for the "form" attribute.
                    # This is my workaround.
                    if label_type == u"hint":
                        value, output_inserted = \
                            self.insert_output_values(media_value)

                        if media_type == "guidance":
                            itext_nodes.append(
                                node("value", value,
                                    form='guidance',
                                    toParseString=output_inserted)
                            )
                        else:
                             itext_nodes.append(
                                node("value", value, toParseString=output_inserted)
                            )
                        continue

                    if media_type == "long":
                        value, output_inserted = \
                            self.insert_output_values(media_value)
                        # I'm ignoring long types for now because I don't know
                        # how they are supposed to work.
                        itext_nodes.append(
                            node("value", value, toParseString=output_inserted)
                        )
                    elif media_type == "image":
                        value, output_inserted = \
                            self.insert_output_values(media_value)
                        itext_nodes.append(
                            node("value", "jr://images/" + value,
                                 form=media_type,
                                 toParseString=output_inserted)
                        )
                    else:
                        value, output_inserted = \
                            self.insert_output_values(media_value)
                        itext_nodes.append(
                            node("value", "jr://" + media_type + "/" + value,
                                 form=media_type,
                                 toParseString=output_inserted))

                result[-1].appendChild(
                    node("text", *itext_nodes, id=label_name))

        return node("itext", *result)

    def date_stamp(self):
        return self._created.strftime("%Y_%m_%d")

    def _to_ugly_xml(self):
        return '<?xml version="1.0"?>' + self.xml().toxml()

    def _to_pretty_xml(self):
        """
        I want the to_xml method to by default validate the xml we are
        producing.
        """
        # Hacky way of pretty printing xml without adding extra white
        # space to text
        # TODO: check out pyxml
        # http://ronrothman.com/public/leftbraned/xml-dom-minidom-toprettyxml-and-silly-whitespace/
        xml_with_linebreaks = self.xml().toprettyxml(indent='  ')
        text_re = re.compile('(>)\n\s*(\s[^<>\s].*?)\n\s*(\s</)', re.DOTALL)
        output_re = re.compile('\n.*(<output.*>)\n(\s\s)*')
        pretty_xml = text_re.sub(lambda m: ''.join(m.group(1, 2, 3)), xml_with_linebreaks)
        inline_output = output_re.sub('\g<1>', pretty_xml)
        return '<?xml version="1.0"?>\n' + inline_output

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "<pyxform.survey.Survey instance at %s>" % hex(id(self))

    def _setup_xpath_dictionary(self):
        self._xpath = {}
        for element in self.iter_descendants():
            if isinstance(element, Question) or isinstance(element, Section):
                if element.name in self._xpath:
                    self._xpath[element.name] = None
                else:
                    self._xpath[element.name] = element.get_xpath()

    def _var_repl_function(self, matchobj):
        """
        Given a dictionary of xpaths, return a function we can use to
        replace ${varname} with the xpath to varname.
        """
        name = matchobj.group(1)
        intro = "There has been a problem trying to replace ${%s} with the "\
            "XPath to the survey element named '%s'." % (name, name)
        if name not in self._xpath:
            raise PyXFormError(
                intro + " There is no survey element with this name.")
        if self._xpath[name] is None:
            raise PyXFormError(intro + " There are multiple survey elements"
                               " with this name.")

        return " " + self._xpath[name] + " "

    def insert_xpaths(self, text):
        """
        Replace all instances of ${var} with the xpath to var.
        """
        bracketed_tag = r"\$\{(.*?)\}"

        return re.sub(bracketed_tag, self._var_repl_function, unicode(text))

    def _var_repl_output_function(self, matchobj):
        """
        A regex substitution function that will replace
        ${varname} with an output element that has the xpath to varname.
        """
#        if matchobj.group(1) not in self._xpath:
#            raise PyXFormError("There is no survey element with this name.",
#                            matchobj.group(1))
        return '<output value="' + self._var_repl_function(matchobj) + '" />'

    def insert_output_values(self, text):
        """
        Replace all the ${variables} in text with xpaths.
        Returns that and a boolean indicating if there were any ${variables}
        present.
        """
        # There was a bug where escaping is completely turned off in labels
        # where variable replacement is used.
        # For exampke, `${name} < 3` causes an error but `< 3` does not.
        # This is my hacky fix for it, which does string escaping prior to
        # variable replacement:
        text_node = PatchedText()
        text_node.data = text
        xml_text = text_node.toxml()

        bracketed_tag = r"\$\{(.*?)\}"
        # need to make sure we have reason to replace
        # since at this point < is &lt,
        # the net effect &lt gets translated again to &amp;lt;
        if unicode(xml_text).find('{') != -1:
            result = re.sub(
                bracketed_tag, self._var_repl_output_function,
                unicode(xml_text))
            return result, not result == xml_text
        return text, False

    def print_xform_to_file(self, path=None, validate=True, pretty_print=True,
                            warnings=None, enketo=False):
        """
        Print the xForm to a file and optionally validate it as well by
        throwing exceptions and adding warnings to the warnings array.
        """
        if warnings is None:
            warnings = []
        if not path:
            path = self._print_name + ".xml"
        try:
            with codecs.open(path, mode="w", encoding="utf-8") as fp:
                if pretty_print:
                    fp.write(self._to_pretty_xml())
                else:
                    fp.write(self._to_ugly_xml())
        except Exception as e:
            if os.path.exists(path):
                os.unlink(path)
            raise e
        if validate:
            warnings.extend(odk_validate.check_xform(path))
        if enketo:
            warnings.extend(enketo_validate.check_xform(path))

        # Warn if one or more translation is missing a valid IANA subtag
        if len(self._translations.keys()) > 0:
            bad_languages = get_languages_with_bad_tags(self._translations.keys())
            if len(bad_languages) > 0:
                warnings.append("\tThe following language declarations do not contain valid machine-readable codes: " +
                    ", ".join(bad_languages) + ". Learn more: http://xlsform.org/#language")

    def to_xml(self, validate=True, pretty_print=True, warnings=None,
               enketo=False):
        # On Windows, NamedTemporaryFile must be opened exclusively.
        # So it must be explicitly created, opened, closed, and removed.
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        try:
            # this will throw an exception if the xml is not valid
            self.print_xform_to_file(
                path=tmp.name, validate=validate, pretty_print=pretty_print,
                warnings=warnings, enketo=enketo)
        finally:
            if os.path.exists(tmp.name):
                os.remove(tmp.name)
        if pretty_print:
            return self._to_pretty_xml()
        else:
            return self._to_ugly_xml()

    def instantiate(self):
        """
        Instantiate as in return a instance of SurveyInstance for collected
        data.
        """
        return SurveyInstance(self)
