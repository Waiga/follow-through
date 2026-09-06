import unittest

from follow_through import report
from follow_through.models import UNKNOWN, Entry


def entry(identity="a1", owner="Alex", due="by Friday", state="open", note=""):
    return Entry(
        id=identity,
        text="I'll send the lease.",
        owner=owner,
        due_phrase=due,
        cues=("first-person-undertaking",),
        source="sample.txt",
        line=1,
        state=state,
        note=note,
    )


class Counting(unittest.TestCase):
    def test_counts_each_state(self):
        figures = report.counts([entry("a"), entry("b", state="closed", note="done")])
        self.assertEqual(figures["open"], 1)
        self.assertEqual(figures["closed"], 1)
        self.assertEqual(figures["total"], 2)

    def test_counts_open_entries_without_an_owner(self):
        figures = report.counts([entry("a", owner=UNKNOWN), entry("b")])
        self.assertEqual(figures["open_without_owner"], 1)

    def test_counts_open_entries_with_a_deadline(self):
        figures = report.counts([entry("a", due=UNKNOWN), entry("b")])
        self.assertEqual(figures["open_with_due_phrase"], 1)

    def test_a_closed_entry_is_not_counted_as_open(self):
        figures = report.counts([entry("a", state="closed", note="done")])
        self.assertEqual(figures["open_without_owner"], 0)
        self.assertEqual(figures["open_with_due_phrase"], 0)


class Grouping(unittest.TestCase):
    def test_named_owners_come_first_and_unknown_last(self):
        groups = report.group_by_owner(
            [entry("a", owner=UNKNOWN), entry("b", owner="Sam"), entry("c", owner="Alex")]
        )
        self.assertEqual([name for name, _ in groups], ["Alex", "Sam", UNKNOWN])

    def test_unknown_owners_keep_their_own_visible_group(self):
        groups = report.group_by_owner([entry("a", owner=UNKNOWN)])
        self.assertEqual(groups, [(UNKNOWN, [entry("a", owner=UNKNOWN)])])


class Markdown(unittest.TestCase):
    def test_shows_evidence_for_every_entry(self):
        text = report.render_markdown([entry()])
        self.assertIn("sample.txt` line 1", text)
        self.assertIn("first-person-undertaking", text)

    def test_names_a_missing_deadline_rather_than_inventing_one(self):
        text = report.render_markdown([entry(due=UNKNOWN)])
        self.assertIn("no stated deadline", text)

    def test_missing_owner_gets_a_readable_heading(self):
        text = report.render_markdown([entry(owner=UNKNOWN)])
        self.assertIn("No owner stated", text)

    def test_closed_entries_show_why(self):
        text = report.render_markdown([entry(state="closed", note="signed and filed")])
        self.assertIn("signed and filed", text)

    def test_an_empty_ledger_still_renders(self):
        text = report.render_markdown([])
        self.assertIn("Nothing open.", text)

    def test_every_report_states_its_limits(self):
        self.assertIn(report.LIMITATIONS, report.render_markdown([]))


class MarkdownIsNotInjectable(unittest.TestCase):
    """A closing note is written by a person and can contain newlines.

    In Markdown a newline ends the list item, so an unescaped note could close
    the list, open a heading, and add entries the tool never found to a report a
    reader trusts.
    """

    def test_a_multiline_note_cannot_add_structure(self):
        hostile = entry(state="closed", note="done\n## Injected\n- **ffff** fabricated")
        rendered = report.render_markdown([hostile])
        self.assertNotIn("\n## Injected", rendered)
        self.assertNotIn("\n- **ffff**", rendered)

    def test_a_multiline_quote_cannot_add_structure(self):
        hostile = entry()
        hostile.text = "I'll send it.\n## Injected heading"
        rendered = report.render_markdown([hostile])
        self.assertNotIn("\n## Injected heading", rendered)

    def test_the_content_is_kept_not_dropped(self):
        hostile = entry(state="closed", note="done\n## Injected")
        rendered = report.render_markdown([hostile])
        self.assertIn("done ## Injected", rendered)

    def test_a_note_cannot_render_a_clickable_link(self):
        hostile = entry(state="closed", note="paid [proof](http://evil.example/x)")
        rendered = report.render_markdown([hostile])
        self.assertNotIn("[proof](http://evil.example/x)", rendered)
        self.assertIn("proof", rendered)

    def test_a_note_cannot_render_emphasis_or_code(self):
        hostile = entry(state="closed", note="**PAID IN FULL** `rm -rf /`")
        rendered = report.render_markdown([hostile])
        self.assertNotIn("**PAID IN FULL**", rendered)
        self.assertNotIn("`rm -rf /`", rendered)

    def test_html_is_protected_by_the_same_rule(self):
        hostile = entry(state="closed", note="done\n## Injected")
        self.assertIn("done ## Injected", report.render_html([hostile]))


class Html(unittest.TestCase):
    def test_escapes_text_from_the_transcript(self):
        hostile = entry()
        hostile.text = "<script>alert(1)</script>"
        rendered = report.render_html([hostile])
        self.assertNotIn("<script>alert(1)</script>", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_escapes_an_owner_name(self):
        hostile = entry(owner="<b>Alex</b>")
        rendered = report.render_html([hostile])
        self.assertNotIn("<b>Alex</b>", rendered)

    def test_escapes_a_closing_note(self):
        hostile = entry(state="closed", note="<img src=x onerror=1>")
        rendered = report.render_html([hostile])
        self.assertNotIn("<img src=x", rendered)

    def test_is_a_complete_document(self):
        rendered = report.render_html([entry()])
        self.assertTrue(rendered.startswith("<!doctype html>"))
        self.assertIn("</html>", rendered)

    def test_every_report_states_its_limits(self):
        self.assertIn("does not find every commitment", report.render_html([]))


if __name__ == "__main__":
    unittest.main()
