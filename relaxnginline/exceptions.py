from lxml import etree


class RelaxngInlineError(BaseException):
    pass


class NoAvailableHandlerError(RelaxngInlineError):
    pass


class BadXmlError(RelaxngInlineError):
    pass


class ParseError(BadXmlError):
    pass


class DereferenceError(RelaxngInlineError):
    pass


class InvalidGrammarError(BadXmlError):
    @classmethod
    def from_bad_element(cls, el, msg):
        return cls("{} on line {} {}"
                   .format(el.tag, el.sourceline or "??", msg))


class SchemaIncludesSelfError(InvalidGrammarError, DereferenceError):
    @classmethod
    def from_context_stack(cls, url, trigger_el, stack):
        # Drop tokens from the stack and append the loop-creating el & url
        url_triggers = [(u, t) for (u, _, t) in stack] + [(url, trigger_el)]

        loop = "".join(cls._format_url_trigger(u, t)
                       for (u, t) in url_triggers)

        return cls("A schema referenced itself, creating a loop:\n{}"
                   .format(loop))

    @classmethod
    def _format_url_trigger(cls, url, trigger_el):
        if trigger_el is None:
            return url
        return ":{} <{}> -> \n{}".format(
            trigger_el.sourceline, etree.QName(trigger_el).localname, url)
