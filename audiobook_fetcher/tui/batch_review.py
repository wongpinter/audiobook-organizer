"""The batch rename review screen: shows old->new path for every file,
lets the user toggle rows in/out, and only returns the approved subset.
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Footer, Header, Static

from audiobook_fetcher.domain.models import RenamePlan

ROW_OK = "green"
ROW_SKIPPED = "yellow"
ROW_CONFLICT = "red"


class BatchReviewApp(App):
    """Run this with BatchReviewApp(plans).run() to get the user-approved subset."""

    BINDINGS = [
        Binding("space", "toggle_row", "Toggle include"),
        Binding("y", "confirm", "Commit batch"),
        Binding("q", "quit_without_saving", "Cancel"),
    ]

    def __init__(self, plans: list[RenamePlan]):
        super().__init__()
        self.plans = plans
        self.approved: list[RenamePlan] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Static(id="summary"),
            DataTable(id="review-table", cursor_type="row"),
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#review-table", DataTable)
        table.add_columns("Include", "Old Path", "New Path")
        self._refresh_table()

    def _refresh_table(self) -> None:
        table = self.query_one("#review-table", DataTable)
        table.clear()
        for i, plan in enumerate(self.plans):
            mark = "[x]" if plan.include else "[ ]"
            new_display = str(plan.new_path) if plan.new_path else f"(skipped: {plan.reason_skipped})"
            table.add_row(mark, plan.old_path.name, new_display, key=str(i))

        included = sum(1 for p in self.plans if p.include)
        skipped = len(self.plans) - included
        self.query_one("#summary", Static).update(
            f"{included} to rename, {skipped} skipped — "
            f"[space] toggle  [y] commit  [q] cancel"
        )

    def action_toggle_row(self) -> None:
        table = self.query_one("#review-table", DataTable)
        if table.cursor_row is None:
            return
        plan = self.plans[table.cursor_row]
        if plan.new_path is None:
            return  # can't include a row with no match
        plan.include = not plan.include
        self._refresh_table()

    def action_confirm(self) -> None:
        self.approved = [p for p in self.plans if p.include]
        self.exit()

    def action_quit_without_saving(self) -> None:
        self.approved = None
        self.exit()


def review_batch(plans: list[RenamePlan]) -> list[RenamePlan] | None:
    """Blocking helper: run the TUI, return the approved plans or None if cancelled."""
    app = BatchReviewApp(plans)
    app.run()
    return app.approved
