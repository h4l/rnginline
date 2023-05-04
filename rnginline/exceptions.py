from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

from lxml import etree

if TYPE_CHECKING:
    from rnginline import InlineContextToken


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
    def from_bad_element(cls, el: etree._Element, msg: str) -> InvalidGrammarError:
        return cls(
            "{0} in {1} on line {2} {3}".format(
                el.tag, el.getroottree().docinfo.URL or "??", el.sourceline or "??", msg
            )
        )


class SchemaIncludesSelfError(InvalidGrammarError, DereferenceError):
    @classmethod
    def from_context_stack(
        cls,
        url: str | None,
        trigger_el: etree._Element | None,
        stack: Sequence[tuple[str | None, InlineContextToken, etree._Element | None]],
    ) -> SchemaIncludesSelfError:
        # Drop tokens from the stack and append the loop-creating el & url
        url_triggers = [(u, t) for (u, _, t) in stack] + [(url, trigger_el)]

        loop = "".join(cls._format_url_trigger(u, t) for (u, t) in url_triggers)

        return cls("A schema referenced itself, creating a loop:\n{0}".format(loop))

    @classmethod
    def _format_url_trigger(
        cls, url: str | None, trigger_el: etree._Element | None
    ) -> str:
        if trigger_el is None:
            return str(url)
        return ":{0} <{1}> -> \n{2}".format(
            trigger_el.sourceline, etree.QName(trigger_el).localname, url
        )
